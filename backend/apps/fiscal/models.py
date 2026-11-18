from django.db import models

from apps.orcamento.models import (
    AuditoriaMixin,
    CategoriaEconomica,
    ClassificacaoOficialMixin,
    OrigemRegistroMixin,
)


class ClassificacaoReceitaOrigem(ClassificacaoOficialMixin, models.Model):
    """
    Nível 2 do Ementário da Receita (STN): Origem. Nível 1 (Categoria
    Econômica) não tem model próprio aqui — é compartilhado com a despesa
    via `apps.orcamento.CategoriaEconomica` (mesmo catálogo nacional, só
    códigos diferentes: 1/2 para receita, 3/4 para despesa), por pedido
    explícito do usuário para permitir cruzamentos Receita x Despesa por
    `natureza` (Corrente/Capital). Ver docstring de `CategoriaEconomica`.
    """

    categoria = models.ForeignKey(
        CategoriaEconomica, on_delete=models.PROTECT, related_name="origens_receita"
    )
    codigo = models.CharField("Código", max_length=1)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Classificação de Receita — Origem"
        verbose_name_plural = "Classificação de Receita — Origens"
        ordering = ["categoria", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["categoria", "codigo"], name="receita_origem_unica_por_categoria")
        ]

    def __str__(self):
        return f"{self.categoria.codigo}.{self.codigo} - {self.nome}"


class ClassificacaoReceitaEspecie(ClassificacaoOficialMixin, models.Model):
    """Nível 3 do Ementário da Receita (STN): Espécie."""

    origem = models.ForeignKey(ClassificacaoReceitaOrigem, on_delete=models.PROTECT, related_name="especies")
    codigo = models.CharField("Código", max_length=1)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Classificação de Receita — Espécie"
        verbose_name_plural = "Classificação de Receita — Espécies"
        ordering = ["origem", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["origem", "codigo"], name="receita_especie_unica_por_origem")
        ]

    def __str__(self):
        return f"{self.origem.categoria.codigo}.{self.origem.codigo}.{self.codigo} - {self.nome}"


class ClassificacaoReceitaRubrica(ClassificacaoOficialMixin, models.Model):
    """
    Nível 4 do Ementário da Receita (STN): Rubrica. ATENÇÃO — este é o
    nível oficial nacional "Rubrica" do Ementário da STN, distinto da
    `RubricaReceita` (cadastro municipal de rubricas orçamentárias, que
    referencia este nível via `classificacao_tipo`). Nomeado com o
    prefixo `ClassificacaoReceita` justamente para nunca ser confundido
    com `RubricaReceita` em nenhum import/consulta.
    """

    especie = models.ForeignKey(ClassificacaoReceitaEspecie, on_delete=models.PROTECT, related_name="rubricas")
    codigo = models.CharField("Código", max_length=1)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Classificação de Receita — Rubrica (STN)"
        verbose_name_plural = "Classificação de Receita — Rubricas (STN)"
        ordering = ["especie", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["especie", "codigo"], name="receita_rubrica_unica_por_especie")
        ]

    def __str__(self):
        return f"{self.especie.origem.categoria.codigo}.{self.especie.origem.codigo}.{self.especie.codigo}.{self.codigo} - {self.nome}"


class ClassificacaoReceitaAlinea(ClassificacaoOficialMixin, models.Model):
    """Nível 5 do Ementário da Receita (STN): Alínea."""

    rubrica = models.ForeignKey(ClassificacaoReceitaRubrica, on_delete=models.PROTECT, related_name="alineas")
    codigo = models.CharField("Código", max_length=2)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Classificação de Receita — Alínea"
        verbose_name_plural = "Classificação de Receita — Alíneas"
        ordering = ["rubrica", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["rubrica", "codigo"], name="receita_alinea_unica_por_rubrica")
        ]

    def __str__(self):
        return f"{self.rubrica} .{self.codigo} - {self.nome}"


class ClassificacaoReceitaSubalinea(ClassificacaoOficialMixin, models.Model):
    """Nível 6 do Ementário da Receita (STN): Subalínea."""

    alinea = models.ForeignKey(ClassificacaoReceitaAlinea, on_delete=models.PROTECT, related_name="subalineas")
    codigo = models.CharField("Código", max_length=1)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Classificação de Receita — Subalínea"
        verbose_name_plural = "Classificação de Receita — Subalíneas"
        ordering = ["alinea", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["alinea", "codigo"], name="receita_subalinea_unica_por_alinea")
        ]

    def __str__(self):
        return f"{self.alinea} .{self.codigo} - {self.nome}"


class ClassificacaoReceitaTipo(ClassificacaoOficialMixin, models.Model):
    """Nível 7 (folha) do Ementário da Receita (STN): Tipo (ex.: 1=Principal)."""

    subalinea = models.ForeignKey(ClassificacaoReceitaSubalinea, on_delete=models.PROTECT, related_name="tipos")
    codigo = models.CharField("Código", max_length=1)
    nome = models.CharField("Nome", max_length=150)

    class Meta:
        verbose_name = "Classificação de Receita — Tipo"
        verbose_name_plural = "Classificação de Receita — Tipos"
        ordering = ["subalinea", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["subalinea", "codigo"], name="receita_tipo_unico_por_subalinea")
        ]

    def __str__(self):
        return f"{self.subalinea} .{self.codigo} - {self.nome}"


class RubricaReceita(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Classificação orçamentária da receita (código + fonte de recursos),
    uma por LOA. Fonte: FICHAS_RECEITAS.PDF ("Classificação Econômica da
    Receita - Local") — o único catálogo de receita com valores
    disponível; cumpre para receita o mesmo papel que RubricaOrcamentaria
    cumpre para despesa, mas sem a dimensão organizacional (órgão/unidade
    orçamentária/função/subfunção/programa/ação): receita não se vincula a
    uma estrutura administrativa executora, só à Unidade Gestora
    arrecadadora (Prefeitura ou Câmara) e à fonte de recursos (vinculação
    constitucional). Reaproveita `orcamento.FonteRecursos` — é o mesmo
    catálogo de vinculações usado pela despesa (confirmado por nome: toda
    fonte citada no PDF já existe, com o mesmo nome, do lado despesa; só
    falta a linha para a UG específica em parte dos casos — criada aqui
    sob demanda, com o código emprestado de outra UG que já o tenha, ou um
    código sintético nos poucos casos nunca vistos em nenhuma UG — ver
    `services.resolver_fonte_por_nome`).
    """

    loa = models.ForeignKey("orcamento.LOA", on_delete=models.PROTECT, related_name="rubricas_receita")
    unidade_gestora = models.ForeignKey(
        "municipios.UnidadeGestora", on_delete=models.PROTECT, related_name="rubricas_receita"
    )
    codigo = models.CharField("Código", max_length=30)
    nome = models.CharField("Nome", max_length=255)
    fonte_recursos = models.ForeignKey(
        "orcamento.FonteRecursos", on_delete=models.PROTECT, related_name="rubricas_receita"
    )
    valor_orcado = models.DecimalField("Valor orçado", max_digits=18, decimal_places=2)

    classificacao_tipo = models.ForeignKey(
        ClassificacaoReceitaTipo, on_delete=models.PROTECT, null=True, blank=True,
        related_name="rubricas_receita",
        help_text="Folha (nível 7, Tipo) do Ementário STN que este código decompõe para.",
    )
    detalhamento_adicional = models.CharField(
        "Detalhamento adicional (não-STN)", max_length=20, blank=True,
        help_text=(
            "Segmentos do código além dos 7 níveis oficiais do Ementário STN "
            "(desdobramento interno do sistema de origem, ex.: '01.00.00') — "
            "nunca tratado como nível oficial, só preservado para referência."
        ),
    )

    eh_deducao = models.BooleanField(
        "É dedução", default=False,
        help_text=(
            "True quando o primeiro segmento do código tem um prefixo "
            "não-trivial antes do dígito de Categoria Econômica (ex.: "
            "'95'/'99' em '951.x'/'991.x') — convenção do usuário: códigos "
            "assim são deduções constitucionais da receita corrente "
            "(cota-parte/FUNDEB), não receita nova. Ver `rubrica_principal`."
        ),
    )
    rubrica_principal = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="deducoes",
        help_text=(
            "Quando eh_deducao=True, aponta para a RubricaReceita 'bruta' "
            "correspondente (mesma UG/fonte/classificação, prefixo trivial "
            "'00') que esta dedução reduz — ex.: '951.7.1.1.51.1.1...' "
            "(dedução FUNDEB do FPM) aponta para '001.7.1.1.51.1.1...' "
            "(FPM bruto)."
        ),
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rubrica de Receita"
        verbose_name_plural = "Rubricas de Receita"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["loa", "unidade_gestora", "codigo", "fonte_recursos"],
                name="rubrica_receita_unica_por_loa_ug_codigo_fonte",
            )
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nome} ({self.fonte_recursos.nome})"


class LancamentoExecucaoReceita(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Agregado mensal de receita arrecadada por rubrica (código × fonte) —
    equivalente, para receita, ao `LancamentoExecucaoOrcamentaria` de
    despesa. Fonte: "Demonstrativo da receita por classificação
    econômica" (R01.PDF..R09.PDF — um arquivo por mês, cada um cobrindo
    SÓ aquele mês, não cumulativo, ao contrário do antigo balancete de
    despesa em PDF).

    Esta é a ÚNICA fonte de receita com a dimensão fonte de recursos — a
    antiga planilha RECEITAS.ods (transação individual, sem fonte) foi
    usada como fonte de receita até 2026-11-10 e depois removida do
    schema inteiramente (model `Arrecadacao`, descontinuado) quando este
    relatório assumiu como única fonte ativa de execução de receita.

    `valor_liquido_no_mes = valor_bruto_no_mes - deducao_no_mes -
    anulacao_no_mes` (já vem calculado assim no relatório de origem).
    """

    rubrica = models.ForeignKey("RubricaReceita", on_delete=models.PROTECT, related_name="lancamentos")
    mes_referencia = models.PositiveSmallIntegerField("Mês de referência", db_index=True)

    valor_bruto_no_mes = models.DecimalField("Valor bruto no mês", max_digits=18, decimal_places=2, default=0)
    deducao_no_mes = models.DecimalField("Dedução no mês", max_digits=18, decimal_places=2, default=0)
    anulacao_no_mes = models.DecimalField("Anulação no mês", max_digits=18, decimal_places=2, default=0)
    valor_liquido_no_mes = models.DecimalField("Valor líquido no mês", max_digits=18, decimal_places=2, default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lançamento de Execução de Receita"
        verbose_name_plural = "Lançamentos de Execução de Receita"
        ordering = ["rubrica", "mes_referencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["rubrica", "mes_referencia"], name="lancamento_receita_unico_por_rubrica_mes"
            )
        ]

    def __str__(self):
        return f"{self.rubrica.codigo} - mês {self.mes_referencia} ({self.valor_liquido_no_mes})"
