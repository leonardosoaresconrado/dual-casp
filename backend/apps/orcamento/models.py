from django.db import models


class StatusExercicio(models.TextChoices):
    PLANEJAMENTO = "PLANEJAMENTO", "Em planejamento"
    EM_EXECUCAO = "EM_EXECUCAO", "Em execução"
    ENCERRADO = "ENCERRADO", "Encerrado"


class OrigemClassificacao(models.TextChoices):
    OFICIAL = "OFICIAL", "Oficial (STN/SOF)"
    MUNICIPAL = "MUNICIPAL", "Municipal"


class ClassificacaoOficialMixin(models.Model):
    """
    Campos comuns aos catálogos de classificação oficial STN/SOF — tanto os
    de despesa (CategoriaEconomica, GrupoNaturezaDespesa, ModalidadeAplicacao,
    ElementoDespesa, Subelemento) quanto os de receita (apps.fiscal). São
    catálogos nacionais, compartilhados por todo município — nunca filtrados
    por município. `ano_vigencia_inicial` marca desde qual exercício aquele
    código existe na tabela oficial; não confundir com `Exercicio`, que é
    escopado por município (estes catálogos não são).
    """

    ativo = models.BooleanField("Ativo", default=True, db_index=True)
    origem_classificacao = models.CharField(
        "Origem da classificação", max_length=10,
        choices=OrigemClassificacao.choices, default=OrigemClassificacao.OFICIAL,
    )
    ano_vigencia_inicial = models.PositiveSmallIntegerField(
        "Vigente desde (ano)", null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditoriaMixin(models.Model):
    """
    Rastreia quem criou/alterou um registro pela API — nulo quando a linha
    vem de um management command de import (sem usuário autenticado na
    requisição) em vez de uma edição manual via CRUD. Usado pelos "fatos"
    importados que ganharam CRUD completo (ver OrigemRegistroMixin) e por
    qualquer outro model onde "quem mexeu nisso" importa.
    """

    criado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    atualizado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True


class OrigemRegistro(models.TextChoices):
    IMPORTADO = "IMPORTADO", "Importado"
    MANUAL = "MANUAL", "Manual"


class OrigemRegistroMixin(models.Model):
    """
    Distingue um "fato" (Empenho, LancamentoExecucaoOrcamentaria, etc.)
    criado pelo pipeline de import de um criado/editado manualmente via
    CRUD. Importante porque os services de import fazem delete+recreate ou
    upsert por chave natural (ver docstrings de Empenho/EmpenhoMovimento) —
    uma correção manual pode ser silenciosamente sobrescrita na próxima
    reimportação do mesmo arquivo. O frontend usa este campo para avisar
    disso antes de deixar editar.
    """

    origem_registro = models.CharField(
        "Origem do registro", max_length=10,
        choices=OrigemRegistro.choices, default=OrigemRegistro.IMPORTADO,
        db_index=True,
    )

    class Meta:
        abstract = True


class Exercicio(models.Model):
    """Exercício financeiro (ano) de um município."""

    municipio = models.ForeignKey(
        "municipios.Municipio", on_delete=models.PROTECT, related_name="exercicios"
    )
    ano = models.PositiveIntegerField("Ano", db_index=True)
    status = models.CharField(
        "Status", max_length=20, choices=StatusExercicio.choices,
        default=StatusExercicio.PLANEJAMENTO,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Exercício"
        verbose_name_plural = "Exercícios"
        ordering = ["-ano"]
        constraints = [
            models.UniqueConstraint(fields=["municipio", "ano"], name="exercicio_unico_por_municipio")
        ]

    def __str__(self):
        return f"{self.municipio.nome}/{self.municipio.uf} - {self.ano}"


class LOA(models.Model):
    """Lei Orçamentária Anual de um exercício."""

    exercicio = models.OneToOneField(Exercicio, on_delete=models.CASCADE, related_name="loa")
    numero_lei = models.CharField("Número da lei", max_length=50)
    data_sancao = models.DateField("Data de sanção", null=True, blank=True)
    valor_total_receita_prevista = models.DecimalField(
        "Receita total prevista", max_digits=18, decimal_places=2
    )
    valor_total_despesa_fixada = models.DecimalField(
        "Despesa total fixada", max_digits=18, decimal_places=2
    )
    observacoes = models.TextField("Observações", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "LOA"
        verbose_name_plural = "LOAs"

    def __str__(self):
        return f"LOA {self.exercicio}"


class NaturezaCategoriaEconomica(models.TextChoices):
    CORRENTE = "CORRENTE", "Corrente"
    CAPITAL = "CAPITAL", "Capital"


class CategoriaEconomica(ClassificacaoOficialMixin, models.Model):
    """
    Categoria econômica — compartilhada entre despesa e receita (Lei
    4.320/64), por pedido explícito do usuário ("Categoria econômica e
    fonte deve ser compartilhado entre receita e despesa, para podermos
    fazer cruzamentos como por exemplo Receita Corrente x Despesa
    Corrente"). Um único catálogo nacional com as 4 combinações possíveis:
    1=Receitas Correntes, 2=Receitas de Capital, 3=Despesas Correntes,
    4=Despesas de Capital — mais o código especial 9="Reserva de
    Contingência" (não é corrente nem capital, por isso `natureza` fica
    nulo nesse caso). `natureza` é o campo que de fato habilita o
    cruzamento Receita x Despesa: código varia (1 vs 3 são ambos
    "Corrente"), `natureza` não.

    Usado por `RubricaOrcamentaria.categoria_economica` (despesa) e por
    `apps.fiscal.ClassificacaoReceitaOrigem.categoria` (receita, nível 2 do
    Ementário aponta para o nível 1 aqui) — a mesma tabela, dois domínios.
    """

    codigo = models.CharField("Código", max_length=1, unique=True)
    nome = models.CharField("Nome", max_length=100)
    natureza = models.CharField(
        "Natureza", max_length=10, choices=NaturezaCategoriaEconomica.choices,
        null=True, blank=True,
    )

    class Meta:
        verbose_name = "Categoria Econômica"
        verbose_name_plural = "Categorias Econômicas"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class GrupoNaturezaDespesa(ClassificacaoOficialMixin, models.Model):
    """Grupo de natureza da despesa (1 a 6). Catálogo nacional, padrão STN."""

    codigo = models.CharField("Código", max_length=1, unique=True)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Grupo de Natureza de Despesa"
        verbose_name_plural = "Grupos de Natureza de Despesa"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class ModalidadeAplicacao(ClassificacaoOficialMixin, models.Model):
    """Modalidade de aplicação da despesa (ex.: 90-Aplicações Diretas). Catálogo nacional, padrão STN."""

    codigo = models.CharField("Código", max_length=2, unique=True)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Modalidade de Aplicação"
        verbose_name_plural = "Modalidades de Aplicação"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class ElementoDespesa(ClassificacaoOficialMixin, models.Model):
    """Elemento de despesa (ex.: 11-Vencimentos e Vantagens Fixas). Catálogo nacional, padrão STN."""

    codigo = models.CharField("Código", max_length=2, unique=True)
    nome = models.CharField("Nome", max_length=200)

    class Meta:
        verbose_name = "Elemento de Despesa"
        verbose_name_plural = "Elementos de Despesa"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Subelemento(ClassificacaoOficialMixin, models.Model):
    """Subelemento (desdobramento) de um Elemento de Despesa."""

    elemento = models.ForeignKey(ElementoDespesa, on_delete=models.PROTECT, related_name="subelementos")
    codigo = models.CharField("Código", max_length=2)
    nome = models.CharField("Nome", max_length=200)

    class Meta:
        verbose_name = "Subelemento de Despesa"
        verbose_name_plural = "Subelementos de Despesa"
        ordering = ["elemento", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["elemento", "codigo"], name="subelemento_codigo_unico_por_elemento")
        ]

    def __str__(self):
        return f"{self.elemento.codigo}.{self.codigo} - {self.nome}"


class TipoFonteRecursos(models.TextChoices):
    ORDINARIO = "ORDINARIO", "Ordinário"
    VINCULADO = "VINCULADO", "Vinculado"


class NaturezaFonteRecursos(models.TextChoices):
    DO_EXERCICIO = "DO_EXERCICIO", "Recursos do Exercício"
    SUPERAVIT_FINANCEIRO = "SUPERAVIT_FINANCEIRO", "Superávit Financeiro de Exercícios Anteriores"


class FonteRecursos(models.Model):
    """
    Fonte/destinação de recursos — catálogo nacional (STN), compartilhado
    por todas as Unidades Gestoras (mesmo padrão de `CategoriaEconomica`/
    `GrupoNaturezaDespesa`/`ModalidadeAplicacao`/`ElementoDespesa`/
    `Subelemento`, todos sem escopo de UG). **Corrigido em 2026-11-12**: o
    model original tinha `unidade_gestora` como parte da chave, criando uma
    linha duplicada por UG para o mesmo código/nome real — confirmado pelo
    usuário e pelos dados (89 códigos distintos espalhados em 138 linhas,
    zero divergência de nome entre as duplicatas de um mesmo código, e
    `importar_fontes_recursos()`/`_resolver_fonte_por_nome()` já tratavam
    fonte como catálogo único na prática, só o `unique_together` é que
    forçava a duplicação). Ver nota de migração de dados na migration que
    introduziu esse fix — mescla as duplicatas existentes antes de remover
    a coluna.
    """

    codigo = models.CharField("Código", max_length=10, unique=True)
    nome = models.CharField("Nome", max_length=200)
    tipo = models.CharField(
        "Tipo", max_length=20, choices=TipoFonteRecursos.choices, blank=True,
    )

    class Meta:
        verbose_name = "Fonte de Recursos"
        verbose_name_plural = "Fontes de Recursos"
        ordering = ["codigo"]

    @property
    def natureza(self) -> str | None:
        """
        Convenção confirmada pelo usuário: o 1º dígito do código indica se
        a fonte é "do exercício" (1) ou "superávit financeiro de
        exercícios anteriores" (2) — mesma classificação/nome costuma se
        repetir nos dois (ex.: "Transferências do FUNDEB - Impostos 70%"
        existe como `15401070` e como `25401070`, duas fontes DIFERENTES,
        não uma duplicata — daí o bug real encontrado em
        `RelatorioFinanceiroPage.tsx`, que agrupava por nome e misturava
        as duas). `None` para os poucos códigos sintéticos `RECxxxxx`
        (ver `_resolver_fonte_por_nome`), que não seguem essa convenção.
        """
        primeiro_digito = self.codigo[:1]
        if primeiro_digito == "1":
            return NaturezaFonteRecursos.DO_EXERCICIO
        if primeiro_digito == "2":
            return NaturezaFonteRecursos.SUPERAVIT_FINANCEIRO
        return None

    @property
    def natureza_label(self) -> str | None:
        return NaturezaFonteRecursos(self.natureza).label if self.natureza else None

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Funcao(models.Model):
    """
    Função de governo (classificação funcional, Portaria MOG nº 42/1999).
    Catálogo nacional — o código é o mesmo em todos os municípios.
    """

    codigo = models.CharField("Código", max_length=2, unique=True)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Função"
        verbose_name_plural = "Funções"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Subfuncao(models.Model):
    """Subfunção de governo (classificação funcional). Catálogo nacional."""

    codigo = models.CharField("Código", max_length=3, unique=True)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Subfunção"
        verbose_name_plural = "Subfunções"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Programa(models.Model):
    """Programa orçamentário de uma LOA (específico de cada exercício/município)."""

    loa = models.ForeignKey(LOA, on_delete=models.CASCADE, related_name="programas")
    codigo = models.CharField("Código", max_length=4)
    nome = models.CharField("Nome", max_length=200)
    objetivo = models.TextField("Objetivo", blank=True)

    class Meta:
        verbose_name = "Programa"
        verbose_name_plural = "Programas"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(fields=["loa", "codigo"], name="programa_codigo_unico_por_loa")
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class TipoAcao(models.TextChoices):
    PROJETO = "PROJETO", "Projeto"
    ATIVIDADE = "ATIVIDADE", "Atividade"
    OPERACAO_ESPECIAL = "OPERACAO_ESPECIAL", "Operação Especial"


class Acao(models.Model):
    """Ação orçamentária (projeto, atividade ou operação especial) de um Programa."""

    programa = models.ForeignKey(Programa, on_delete=models.PROTECT, related_name="acoes")
    codigo = models.CharField("Código", max_length=4)
    nome = models.CharField("Nome", max_length=250)
    tipo = models.CharField("Tipo", max_length=20, choices=TipoAcao.choices)
    # Usada pelo MDE (apps.execucao_fiscal.ApuracaoMDE) para descontar do
    # TOTAL/ÍNDICE GERENCIAL o gasto com PNAE/PEAE custeado com recursos
    # próprios (fontes 15001001/25001001) — esse gasto não deveria contar
    # como aplicação em MDE. Pensada pra ações sob a função 12 (Educação),
    # mas sem FK pra `Funcao` aqui (ver `funcao_codigo`/`funcao_nome`
    # abaixo) — é uma orientação de uso, não uma restrição de schema.
    desconsiderar_pnae_peae = models.BooleanField(
        "Desconsiderar PNAE e PEAE (recursos próprios) no cálculo do MDE", default=False,
    )

    class Meta:
        verbose_name = "Ação"
        verbose_name_plural = "Ações"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(fields=["programa", "codigo"], name="acao_codigo_unico_por_programa")
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    # `Acao` não tem FK pra `Funcao` (só RubricaOrcamentaria tem) — mas
    # confirmado que cada ação sempre aparece com a mesma função em toda
    # `RubricaOrcamentaria` do município (0 contraexemplos em Novo
    # Progresso/PA), então o `.first()` é representativo. Só pra exibição
    # (cadastro de Ações), ajuda a identificar as ações de função 12 antes
    # de marcar `desconsiderar_pnae_peae`.
    @property
    def funcao_codigo(self):
        r = self.rubricas_orcamentarias.select_related("funcao").first()
        return r.funcao.codigo if r else None

    @property
    def funcao_nome(self):
        r = self.rubricas_orcamentarias.select_related("funcao").first()
        return r.funcao.nome if r else None


class OrigemDotacao(models.TextChoices):
    ORCAMENTO = "ORCAMENTO", "Orçamento (LOA)"
    CREDITO_SUPLEMENTAR = "CREDITO_SUPLEMENTAR", "Crédito Suplementar"
    CREDITO_ESPECIAL = "CREDITO_ESPECIAL", "Crédito Especial"
    CREDITO_ADICIONAL = "CREDITO_ADICIONAL", "Crédito Adicional (não catalogado)"


class RubricaOrcamentaria(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Classificação orçamentária completa de uma dotação de despesa,
    conforme publicada na LOA (um registro por linha orçamentária).

    `origem_dotacao` é uma marcação de proveniência (não um ledger somado),
    atualizável — a fonte mais granular disponível sempre vence:
    ORCAMENTO/CREDITO_SUPLEMENTAR/CREDITO_ESPECIAL vêm de
    `services.importar_fichas_despesa` (relatório "Tabela de fichas de
    despesa" do ASPEC, que já classifica cada combinação nativamente —
    inclusive as que ainda não têm valor na LOA, criadas aqui com
    dotacao_inicial=0 à espera do crédito). `services.importar_dotacoes_loa`
    ("Movimentos de Despesa Fixada") só sabe ORCAMENTO vs. "tem valor", sem
    distinguir suplementar de especial — roda antes, pode ficar superado.
    CREDITO_ADICIONAL é o fallback de `services.importar_empenhos` só para
    uma classificação que nem a LOA nem a tabela de fichas previram.
    """

    loa = models.ForeignKey(LOA, on_delete=models.PROTECT, related_name="rubricas")
    unidade_gestora = models.ForeignKey(
        "municipios.UnidadeGestora", on_delete=models.PROTECT, related_name="rubricas_orcamentarias"
    )
    orgao = models.ForeignKey(
        "municipios.Orgao", on_delete=models.PROTECT, related_name="rubricas_orcamentarias",
    )
    unidade_orcamentaria = models.ForeignKey(
        "municipios.UnidadeOrcamentaria", on_delete=models.PROTECT, related_name="rubricas_orcamentarias",
    )
    funcao = models.ForeignKey(Funcao, on_delete=models.PROTECT, related_name="rubricas_orcamentarias")
    subfuncao = models.ForeignKey(Subfuncao, on_delete=models.PROTECT, related_name="rubricas_orcamentarias")
    programa = models.ForeignKey(Programa, on_delete=models.PROTECT, related_name="rubricas_orcamentarias")
    acao = models.ForeignKey(Acao, on_delete=models.PROTECT, related_name="rubricas_orcamentarias")
    categoria_economica = models.ForeignKey(
        CategoriaEconomica, on_delete=models.PROTECT, related_name="rubricas_orcamentarias"
    )
    grupo_natureza_despesa = models.ForeignKey(
        GrupoNaturezaDespesa, on_delete=models.PROTECT, related_name="rubricas_orcamentarias"
    )
    modalidade_aplicacao = models.ForeignKey(
        ModalidadeAplicacao, on_delete=models.PROTECT, related_name="rubricas_orcamentarias"
    )
    elemento_despesa = models.ForeignKey(
        ElementoDespesa, on_delete=models.PROTECT, related_name="rubricas_orcamentarias"
    )
    subelemento = models.ForeignKey(
        Subelemento, on_delete=models.PROTECT, related_name="rubricas_orcamentarias"
    )
    fonte_recursos = models.ForeignKey(
        FonteRecursos, on_delete=models.PROTECT, related_name="rubricas_orcamentarias"
    )
    dotacao_inicial = models.DecimalField("Dotação inicial", max_digits=18, decimal_places=2)
    origem_dotacao = models.CharField(
        "Origem da dotação", max_length=20,
        choices=OrigemDotacao.choices, default=OrigemDotacao.ORCAMENTO, db_index=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rubrica orçamentária"
        verbose_name_plural = "Rubricas orçamentárias"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "loa", "unidade_gestora", "orgao", "unidade_orcamentaria", "funcao", "subfuncao",
                    "programa", "acao", "categoria_economica", "grupo_natureza_despesa",
                    "modalidade_aplicacao", "elemento_despesa", "subelemento", "fonte_recursos",
                ],
                name="rubrica_unica_por_classificacao",
            )
        ]

    def __str__(self):
        return f"{self.unidade_gestora} - {self.funcao.codigo}.{self.subfuncao.codigo}.{self.programa.codigo}.{self.acao.codigo} - elem {self.elemento_despesa.codigo}"


class LancamentoExecucaoOrcamentaria(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Snapshot mensal da execução orçamentária de uma rubrica, geralmente
    obtido por importação de relatório (ex.: ASPEC).
    """

    rubrica = models.ForeignKey(
        RubricaOrcamentaria, on_delete=models.CASCADE, related_name="execucoes"
    )
    mes_referencia = models.PositiveSmallIntegerField("Mês de referência", db_index=True)

    dotacao_inicial = models.DecimalField(max_digits=18, decimal_places=2)
    creditos_suplementares = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    creditos_especiais = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    anulacoes = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    dotacao_atualizada = models.DecimalField(max_digits=18, decimal_places=2)

    empenhado_no_mes = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    empenhado_acumulado = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    liquidado_no_mes = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    liquidado_acumulado = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    pago_no_mes = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    pago_acumulado = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    importacao = models.ForeignKey(
        "importacao.Importacao", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lancamentos_execucao_orcamentaria",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lançamento de execução orçamentária"
        verbose_name_plural = "Lançamentos de execução orçamentária"
        ordering = ["rubrica", "mes_referencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["rubrica", "mes_referencia"], name="execucao_unica_por_mes"
            )
        ]

    @property
    def saldo_a_empenhar(self):
        return self.dotacao_atualizada - self.empenhado_acumulado

    @property
    def saldo_a_liquidar(self):
        return self.empenhado_acumulado - self.liquidado_acumulado

    @property
    def saldo_a_pagar(self):
        return self.liquidado_acumulado - self.pago_acumulado

    def __str__(self):
        return f"{self.rubrica} - {self.mes_referencia:02d}/{self.rubrica.loa.exercicio.ano}"


class Empenho(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Empenho individual — cabeçalho estável (identidade, classificação,
    credor). Fonte: relatório de empenhos do ASPEC ("Relatório para
    conferência dos empenhos"), que o ASPEC exporta uma planilha por mês.

    IMPORTANTE: o relatório do ASPEC não repete o valor acumulado do
    empenho quando ele reaparece num mês seguinte — cada linha reporta só a
    MOVIMENTAÇÃO daquele mês (quanto foi empenhado/liquidado/pago
    especificamente naquele mês para aquele número de empenho, podendo ser
    zero se não houve movimento novo). Por isso os valores totais aqui
    (valor_empenho/valor_liquidado/valor_pago) são agregados calculados a
    partir de `EmpenhoMovimento` — nunca são sobrescritos diretamente pelo
    valor de uma linha de planilha. Essa separação também torna a
    importação independente de ordem: meses podem chegar fora de sequência
    (ou ser reimportados) sem corromper o total, porque cada mês é um
    registro de movimento próprio, somado aos demais.

    "numero" é a chave natural do empenho (único por Unidade Gestora).
    """

    unidade_gestora = models.ForeignKey(
        "municipios.UnidadeGestora", on_delete=models.PROTECT, related_name="empenhos"
    )
    rubrica = models.ForeignKey(RubricaOrcamentaria, on_delete=models.PROTECT, related_name="empenhos")
    numero = models.CharField("Número do empenho", max_length=20)
    data_empenho = models.DateField("Data do empenho")

    credor = models.CharField("Credor", max_length=255)
    historico = models.TextField("Histórico", blank=True)

    valor_empenho = models.DecimalField("Valor empenhado (total)", max_digits=18, decimal_places=2, default=0)
    valor_liquidado = models.DecimalField("Valor liquidado (total)", max_digits=18, decimal_places=2, default=0)
    valor_pago = models.DecimalField("Valor pago (total)", max_digits=18, decimal_places=2, default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Empenho"
        verbose_name_plural = "Empenhos"
        ordering = ["unidade_gestora", "numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["unidade_gestora", "numero"], name="empenho_numero_unico_por_ug"
            )
        ]

    def recalcular_totais(self, salvar: bool = True) -> None:
        """Recalcula valor_empenho/valor_liquidado/valor_pago a partir dos EmpenhoMovimento."""
        agregados = self.movimentos.aggregate(
            emp=models.Sum("valor_empenho_no_mes"),
            liq=models.Sum("valor_liquidado_no_mes"),
            pago=models.Sum("valor_pago_no_mes"),
        )
        self.valor_empenho = agregados["emp"] or 0
        self.valor_liquidado = agregados["liq"] or 0
        self.valor_pago = agregados["pago"] or 0
        if salvar:
            self.save(update_fields=["valor_empenho", "valor_liquidado", "valor_pago", "atualizado_em"])

    @property
    def saldo_a_liquidar(self):
        return self.valor_empenho - self.valor_liquidado

    @property
    def saldo_a_pagar(self):
        return self.valor_liquidado - self.valor_pago

    def __str__(self):
        return f"Empenho {self.numero} - {self.credor} ({self.valor_empenho})"


class EmpenhoMovimento(models.Model):
    """
    Movimentação de um empenho num mês específico — exatamente o que uma
    linha do relatório mensal do ASPEC reporta para aquele número de
    empenho naquele mês (ver nota em `Empenho`). A chave (empenho,
    mes_referencia) é única: reimportar a planilha do mesmo mês atualiza
    esse registro em vez de duplicá-lo ou somar duas vezes.
    """

    empenho = models.ForeignKey(Empenho, on_delete=models.CASCADE, related_name="movimentos")
    mes_referencia = models.PositiveSmallIntegerField("Mês de referência", db_index=True)

    valor_empenho_no_mes = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    valor_liquidado_no_mes = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    valor_pago_no_mes = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    importacao = models.ForeignKey(
        "importacao.Importacao", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="empenho_movimentos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimento de empenho"
        verbose_name_plural = "Movimentos de empenho"
        ordering = ["empenho", "mes_referencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["empenho", "mes_referencia"], name="movimento_unico_por_mes"
            )
        ]

    def __str__(self):
        return f"{self.empenho.numero} - {self.mes_referencia:02d}"
