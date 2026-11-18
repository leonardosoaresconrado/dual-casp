from django.db import models

from apps.orcamento.models import AuditoriaMixin, OrigemRegistroMixin


class ApuracaoFiscalBase(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Base comum aos 8 índices constitucionais/LRF acompanhados neste módulo
    (DTP, MDE, Magistério/FUNDEB, ASPS, VAAT Educação Infantil, VAAT
    Despesa de Capital, FUNDEB Valor Não Aplicado, FUNDEB Reprogramação) —
    todos são apurados por bimestre, para o MUNICÍPIO INTEIRO (sem
    dimensão UG/órgão, ao contrário da maioria dos outros fatos deste
    projeto), a partir de um relatório STN padronizado (RGF/RREO) que o
    próprio ASPEC exporta um PDF por bimestre. Reimportar o mesmo
    (município, exercício, bimestre) SUBSTITUI o registro — cada PDF é
    uma foto completa da apuração até aquele bimestre, nunca um
    incremento.
    """

    municipio = models.ForeignKey("municipios.Municipio", on_delete=models.PROTECT, related_name="+")
    exercicio = models.PositiveIntegerField("Exercício", db_index=True)
    bimestre = models.PositiveSmallIntegerField("Bimestre", db_index=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["municipio", "exercicio", "bimestre"]


class ApuracaoDTP(ApuracaoFiscalBase):
    """
    Despesa Total com Pessoal (LRF art.19/20) — RGF Anexo 1, seção final
    "APURAÇÃO DO CUMPRIMENTO DO LIMITE LEGAL". Limite é um TETO (máximo
    54% da RCL ajustada), ao contrário dos outros índices deste módulo
    (que são mínimos) — por isso `cumpre_limite` compara na direção
    oposta.
    """

    rcl = models.DecimalField("Receita Corrente Líquida", max_digits=18, decimal_places=2)
    # As 4 deduções vêm como 4 linhas próprias no RGF (cada uma pode ter
    # peso diferente de um bimestre pro outro — ex.: emendas de bancada só
    # aparecem a partir de certo bimestre) — mantidas separadas em vez de
    # pré-somadas, mesmo nível de composição que a planilha de controle do
    # cliente usa. Conjunto fixo e pequeno (4 deduções nomeadas por lei,
    # nunca varia) — ao contrário dos sub-itens de receita do MDE/
    # Reprogramação abaixo, não é um "grupo repetido" que justifique
    # virar tabela filha.
    deducao_emendas_individuais = models.DecimalField(
        "Dedução — emendas individuais (art.166-A, §1º CF)", max_digits=18, decimal_places=2, default=0
    )
    deducao_emendas_bancada = models.DecimalField(
        "Dedução — emendas de bancada (art.166, §16 CF)", max_digits=18, decimal_places=2, default=0
    )
    deducao_agentes_saude = models.DecimalField(
        "Dedução — remun. agentes comunitários de saúde/combate a endemias (art.198, §11 CF)",
        max_digits=18, decimal_places=2, default=0,
    )
    deducao_outras = models.DecimalField(
        "Outras deduções constitucionais ou legais", max_digits=18, decimal_places=2, default=0
    )
    rcl_ajustada = models.DecimalField("RCL ajustada para cálculo do limite", max_digits=18, decimal_places=2)
    despesa_total_pessoal = models.DecimalField("Despesa Total com Pessoal (DTP)", max_digits=18, decimal_places=2)
    percentual_dtp = models.DecimalField("% DTP sobre RCL ajustada", max_digits=7, decimal_places=4)
    limite_maximo_valor = models.DecimalField("Limite máximo (valor)", max_digits=18, decimal_places=2)
    limite_maximo_percentual = models.DecimalField("Limite máximo (%)", max_digits=7, decimal_places=4)
    limite_prudencial_valor = models.DecimalField("Limite prudencial (valor)", max_digits=18, decimal_places=2)
    limite_prudencial_percentual = models.DecimalField("Limite prudencial (%)", max_digits=7, decimal_places=4)
    limite_alerta_valor = models.DecimalField("Limite de alerta (valor)", max_digits=18, decimal_places=2)
    limite_alerta_percentual = models.DecimalField("Limite de alerta (%)", max_digits=7, decimal_places=4)

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração DTP (Despesa com Pessoal)"
        verbose_name_plural = "Apurações DTP (Despesa com Pessoal)"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"], name="apuracao_dtp_unica_por_municipio_exercicio_bimestre"
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6), name="apuracao_dtp_bimestre_1_a_6"
            ),
        ]

    @property
    def deducoes_rcl(self):
        return (
            self.deducao_emendas_individuais
            + self.deducao_emendas_bancada
            + self.deducao_agentes_saude
            + self.deducao_outras
        )

    @property
    def cumpre_limite(self) -> bool:
        return self.percentual_dtp <= self.limite_maximo_percentual

    def __str__(self):
        return f"DTP {self.municipio}/{self.exercicio} bim.{self.bimestre}: {self.percentual_dtp}%"


class GrupoReceitaMDE(models.TextChoices):
    IMPOSTOS = "IMPOSTOS", "1 - Receita de Impostos"
    TRANSFERENCIAS = "TRANSFERENCIAS", "2 - Receita de Transferências"


class ApuracaoMDE(ApuracaoFiscalBase):
    """
    Manutenção e Desenvolvimento do Ensino (CF art.212, LDB art.72) — RREO
    Anexo 8, seção de apuração do limite de 25% sobre receita de impostos.

    Os sub-itens de receita (1.1-1.4 "Receita de Impostos", 2.1-2.7
    "Receita de Transferências") NÃO são mais colunas fixas aqui — ver
    `ApuracaoMDEReceitaItem` (tabela filha, uma linha por sub-item). Essas
    duas colunas (`receita_impostos`/`receita_transferencias`) guardam só
    o TOTAL de cada grupo, como o próprio relatório já traz.
    """

    receita_impostos = models.DecimalField("1 - Receita de impostos", max_digits=18, decimal_places=2)
    receita_transferencias = models.DecimalField(
        "2 - Receita de transferências constitucionais", max_digits=18, decimal_places=2
    )

    base_calculo = models.DecimalField("Base de cálculo (1+2)", max_digits=18, decimal_places=2)
    minimo_constitucional = models.DecimalField("Mínimo constitucional (25%)", max_digits=18, decimal_places=2)

    # Despesa com MDE custeada por impostos (exceto FUNDEB) — o relatório
    # dá as 3 fases (empenhada/liquidada/paga) na mesma linha; mantidas
    # separadas porque alimentam os 3 "TOTAL GERENCIAL" da planilha do
    # cliente (ver properties abaixo), cada um usando uma fase diferente.
    despesa_mde_empenhada = models.DecimalField("Despesa MDE — empenhada", max_digits=18, decimal_places=2, default=0)
    despesa_mde_liquidada = models.DecimalField("Despesa MDE — liquidada", max_digits=18, decimal_places=2, default=0)
    despesa_mde_paga = models.DecimalField("Despesa MDE — paga", max_digits=18, decimal_places=2, default=0)

    fundeb_transferido = models.DecimalField(
        "(+) Total das receitas transferidas ao FUNDEB", max_digits=18, decimal_places=2, default=0
    )
    excedente_fundeb_nao_aplicado = models.DecimalField(
        "(-) Receitas do FUNDEB não utilizadas no exercício (excedente aos 10%)",
        max_digits=18, decimal_places=2, default=0,
    )
    cancelamento_rp = models.DecimalField(
        "(-) Cancelamento de RP inscritos com disponibilidade de recursos de impostos",
        max_digits=18, decimal_places=2, default=0,
    )
    # Nem `cancelamento_rp`/`excedente_fundeb_nao_aplicado` acima, nem os 2
    # campos a seguir, vêm do RREO — confirmado via shell que a linha 20
    # do relatório ("TOTAL DAS DESPESAS COM AÇÕES TÍPICAS DE MDE", =
    # despesa_mde_empenhada/liquidada/paga) bate exatamente com toda a
    # despesa da função 12 nas fontes 15001001/25001001, sem excluir nada
    # — nem PNAE/PEAE, nem ensino médio/superior. São descontos GERENCIAIS
    # pedidos pelo usuário (esses gastos não deveriam contar como MDE),
    # só aplicados quando a visão gerencial é escolhida no frontend (ver
    # `total_gerencial_N_desconsiderando_pnae` abaixo) — o padrão
    # (`total_gerencial_N`) continua batendo com o RREO oficial.
    aplicacao_pnae_recursos_proprios = models.DecimalField(
        "(-) Aplicação no PNAE/PEAE com recursos próprios (visão gerencial)",
        max_digits=18, decimal_places=2, default=0,
    )
    # Despesa em recursos próprios nas subfunções 362 (Ensino Médio) / 364
    # (Ensino Superior) — município deve atuar prioritariamente em
    # fundamental/infantil (CF art.211 §2º). Calculado direto por
    # função+subfunção+fonte (sem precisar de flag em `Acao`, ao contrário
    # do PNAE/PEAE — subfunção já é campo direto em `RubricaOrcamentaria`).
    despesa_ensino_medio_superior_recursos_proprios = models.DecimalField(
        "(-) Despesa com Ensino Médio/Superior (362/364) em recursos próprios (visão gerencial)",
        max_digits=18, decimal_places=2, default=0,
    )

    valor_exigido = models.DecimalField("Valor exigido", max_digits=18, decimal_places=2)
    valor_aplicado = models.DecimalField("Valor aplicado (TOTAL STN)", max_digits=18, decimal_places=2)
    percentual_aplicado = models.DecimalField("% aplicado (ÍNDICE STN)", max_digits=7, decimal_places=4)

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração MDE (Ensino)"
        verbose_name_plural = "Apurações MDE (Ensino)"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"], name="apuracao_mde_unica_por_municipio_exercicio_bimestre"
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6), name="apuracao_mde_bimestre_1_a_6"
            ),
        ]

    # Confirmado numericamente contra a planilha de controle do cliente:
    # "TOTAL GERENCIAL n" = despesa (na fase n) + FUNDEB transferido, SEM
    # descontar excedente/cancelamento — apesar do rótulo da própria
    # planilha dizer "- EXCEDENTE", a aritmética bate exatamente sem esse
    # desconto (ex. bimestre 1: 568269,25 + 2977919,13 = 3546188,38 =
    # TOTAL GERENCIAL 1 da planilha, com o dígito batendo à centavo). O
    # desconto de excedente/cancelamento só entra no TOTAL STN (=
    # `valor_aplicado`, que já vem pronto do próprio relatório) — a
    # diferença entre STN e GERENCIAL é exatamente esse desconto.
    def _total_gerencial(self, despesa):
        return despesa + self.fundeb_transferido

    # Variante "visão gerencial mais restritiva" — descontando PNAE/PEAE
    # (recursos próprios) e despesa de ensino médio/superior (362/364,
    # recursos próprios), que o RREO não desconta (ver nota nos campos
    # acima). Só usada quando o frontend liga o switch "Desconsiderar
    # PNAE/PEAE e Ensino Médio/Superior" — por padrão (`total_gerencial_N`
    # acima) os totais continuam batendo com o RREO oficial.
    def _total_gerencial_desconsiderando_pnae(self, despesa):
        return (
            despesa + self.fundeb_transferido
            - self.aplicacao_pnae_recursos_proprios
            - self.despesa_ensino_medio_superior_recursos_proprios
        )

    @property
    def total_gerencial_1(self):
        """TOTAL GERENCIAL 1 (base: despesa LIQUIDADA)."""
        return self._total_gerencial(self.despesa_mde_liquidada)

    @property
    def total_gerencial_2(self):
        """TOTAL GERENCIAL 2 (base: despesa EMPENHADA)."""
        return self._total_gerencial(self.despesa_mde_empenhada)

    @property
    def total_gerencial_3(self):
        """TOTAL GERENCIAL 3 (base: despesa PAGA)."""
        return self._total_gerencial(self.despesa_mde_paga)

    @property
    def total_gerencial_1_desconsiderando_pnae(self):
        return self._total_gerencial_desconsiderando_pnae(self.despesa_mde_liquidada)

    @property
    def total_gerencial_2_desconsiderando_pnae(self):
        return self._total_gerencial_desconsiderando_pnae(self.despesa_mde_empenhada)

    @property
    def total_gerencial_3_desconsiderando_pnae(self):
        return self._total_gerencial_desconsiderando_pnae(self.despesa_mde_paga)

    @property
    def indice_gerencial_1(self):
        return (self.total_gerencial_1 / self.base_calculo * 100) if self.base_calculo else None

    @property
    def indice_gerencial_2(self):
        return (self.total_gerencial_2 / self.base_calculo * 100) if self.base_calculo else None

    @property
    def indice_gerencial_3(self):
        return (self.total_gerencial_3 / self.base_calculo * 100) if self.base_calculo else None

    @property
    def indice_gerencial_1_desconsiderando_pnae(self):
        return (self.total_gerencial_1_desconsiderando_pnae / self.base_calculo * 100) if self.base_calculo else None

    @property
    def indice_gerencial_2_desconsiderando_pnae(self):
        return (self.total_gerencial_2_desconsiderando_pnae / self.base_calculo * 100) if self.base_calculo else None

    @property
    def indice_gerencial_3_desconsiderando_pnae(self):
        return (self.total_gerencial_3_desconsiderando_pnae / self.base_calculo * 100) if self.base_calculo else None

    @property
    def cumpre_limite(self) -> bool:
        return self.percentual_aplicado >= 25

    def __str__(self):
        return f"MDE {self.municipio}/{self.exercicio} bim.{self.bimestre}: {self.percentual_aplicado}%"


class ApuracaoMDEReceitaItem(models.Model):
    """
    Quebra por sub-item de receita de uma `ApuracaoMDE` — uma linha por
    sub-item (1.1 IPTU, 1.2 ITBI, 1.3 ISS, 1.4 IRRF, 2.1 FPM, 2.2 ICMS,
    2.3 IPI, 2.4 ITR, 2.5 IPVA, 2.6 IOF, 2.7 Compensações), substituindo
    as 11 colunas flat que existiam antes (`receita_iptu`, `receita_itbi`
    etc.) — mesmo padrão já usado por `SaldoBalancoContaFonte`/
    `SaldoContaBancariaFonte` (quebra em tabela filha em vez de colunas
    paralelas por sub-item), adotado aqui para deixar tanto o import de
    PDF (cada linha numerada do relatório vira uma linha filha, sem
    precisar de um mapa fixo nome-de-campo→sub-item) quanto o cadastro
    manual (um formulário de "adicionar item" em vez de ~11 campos fixos
    simultâneos) mais diretos.
    """

    apuracao = models.ForeignKey(ApuracaoMDE, on_delete=models.CASCADE, related_name="itens_receita")
    grupo = models.CharField("Grupo", max_length=20, choices=GrupoReceitaMDE.choices, db_index=True)
    codigo = models.CharField("Código (ex.: 1.1, 2.3)", max_length=10)
    rotulo = models.CharField("Rótulo (ex.: IPTU, FPM)", max_length=100)
    valor = models.DecimalField("Valor", max_digits=18, decimal_places=2)

    class Meta:
        verbose_name = "Apuração MDE — Item de Receita"
        verbose_name_plural = "Apuração MDE — Itens de Receita"
        ordering = ["apuracao", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["apuracao", "codigo"], name="apuracao_mde_item_unico_por_codigo")
        ]

    def __str__(self):
        return f"{self.codigo} - {self.rotulo}: {self.valor}"


class ApuracaoMagisterioFundeb(ApuracaoFiscalBase):
    """
    Mínimo de 70% do FUNDEB em remuneração do magistério em efetivo
    exercício (CF art.212-A, inciso XI) — RREO Anexo 8, seção
    "INDICADORES - Art.212-A" (mesmo arquivo da apuração de MDE, seção
    diferente — por isso um model próprio em vez de campos extras em
    ApuracaoMDE, já que os dois vêm de seções distintas do mesmo PDF mas
    representam índices legalmente separados).
    """

    fundeb_receita_total = models.DecimalField("Receita total do FUNDEB", max_digits=18, decimal_places=2)
    valor_exigido = models.DecimalField("Valor exigido (70%)", max_digits=18, decimal_places=2)
    valor_aplicado = models.DecimalField("Valor aplicado", max_digits=18, decimal_places=2)
    percentual_aplicado = models.DecimalField("% aplicado", max_digits=7, decimal_places=4)

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração Magistério/FUNDEB"
        verbose_name_plural = "Apurações Magistério/FUNDEB"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"],
                name="apuracao_magisterio_unica_por_municipio_exercicio_bimestre",
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6), name="apuracao_magisterio_bimestre_1_a_6"
            ),
        ]

    @property
    def cumpre_limite(self) -> bool:
        return self.percentual_aplicado >= 70

    def __str__(self):
        return f"Magistério/FUNDEB {self.municipio}/{self.exercicio} bim.{self.bimestre}: {self.percentual_aplicado}%"


class ApuracaoETIFundeb(ApuracaoFiscalBase):
    """
    Mínimo de 4% do FUNDEB na criação de matrículas em Educação em Tempo
    Integral — ETI (CF art.212-A, inciso XI c/c Lei 14.113/2020) — RREO
    Anexo 8, mesma seção "INDICADORES - Art.212-A", linha 15.2 (15.1 é o
    Magistério, `ApuracaoMagisterioFundeb`, mínimo de 70% — mesma seção do
    mesmo PDF, mesmo `fundeb_receita_total` como base de referência).
    """

    fundeb_receita_total = models.DecimalField("Receita total do FUNDEB", max_digits=18, decimal_places=2)
    valor_exigido = models.DecimalField("Valor exigido (4%)", max_digits=18, decimal_places=2)
    valor_aplicado = models.DecimalField("Valor aplicado", max_digits=18, decimal_places=2)
    percentual_aplicado = models.DecimalField("% aplicado", max_digits=7, decimal_places=4)

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração FUNDEB — Mínimo de 4% em Matrículas ETI"
        verbose_name_plural = "Apurações FUNDEB — Mínimo de 4% em Matrículas ETI"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"],
                name="apuracao_eti_fundeb_unica_por_municipio_exercicio_bimestre",
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6), name="apuracao_eti_fundeb_bimestre_1_a_6"
            ),
        ]

    @property
    def cumpre_limite(self) -> bool:
        return self.percentual_aplicado >= 4

    def __str__(self):
        return f"FUNDEB ETI (4%) {self.municipio}/{self.exercicio} bim.{self.bimestre}: {self.percentual_aplicado}%"


class ApuracaoASPS(ApuracaoFiscalBase):
    """
    Ações e Serviços Públicos de Saúde (LC 141/2012 art.35) — RREO Anexo
    XII, mínimo de 15% da receita de impostos/transferências.
    """

    receita_impostos_transferencias = models.DecimalField(
        "Receita de impostos e transferências constitucionais", max_digits=18, decimal_places=2
    )
    base_calculo = models.DecimalField("Base de cálculo", max_digits=18, decimal_places=2)
    minimo_constitucional = models.DecimalField("Mínimo constitucional (15%)", max_digits=18, decimal_places=2)
    despesa_asps_empenhada = models.DecimalField("Despesa com ASPS empenhada", max_digits=18, decimal_places=2)
    despesa_asps_liquidada = models.DecimalField("Despesa com ASPS liquidada", max_digits=18, decimal_places=2)
    despesa_asps_paga = models.DecimalField("Despesa com ASPS paga", max_digits=18, decimal_places=2, default=0)
    # % aplicado oficial (ÍNDICE STN) é sobre a despesa LIQUIDADA, já vem
    # pronto do relatório; ÍNDICE GERENCIAL (sobre a EMPENHADA) a planilha
    # do cliente também acompanha lado a lado — property, não precisa
    # armazenar (é só despesa_asps_empenhada/base_calculo).
    percentual_aplicado = models.DecimalField("% aplicado (ÍNDICE STN)", max_digits=7, decimal_places=4)

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração ASPS (Saúde)"
        verbose_name_plural = "Apurações ASPS (Saúde)"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"], name="apuracao_asps_unica_por_municipio_exercicio_bimestre"
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6), name="apuracao_asps_bimestre_1_a_6"
            ),
        ]

    @property
    def percentual_gerencial(self):
        return (self.despesa_asps_empenhada / self.base_calculo * 100) if self.base_calculo else None

    @property
    def cumpre_limite(self) -> bool:
        return self.percentual_aplicado >= 15

    def __str__(self):
        return f"ASPS {self.municipio}/{self.exercicio} bim.{self.bimestre}: {self.percentual_aplicado}%"


class ApuracaoVAATEducacaoInfantil(ApuracaoFiscalBase):
    """
    Aplicação da Complementação da União ao FUNDEB (VAAT) em educação
    infantil (CF art.212-A, §3º / Lei 14.113/2020) — RREO Anexo 8, mesma
    seção "INDICADORES - Art.212-A" de `ApuracaoMagisterioFundeb` (linha
    16, logo após a linha 15 do magistério), mesmo arquivo/parser.
    O relatório não imprime um percentual mínimo fixo para este
    indicador (ao contrário de MDE/ASPS/Magistério/VAAT-Capital) — só dá
    o valor exigido e o valor aplicado diretamente, por isso
    `cumpre_limite` compara os dois valores em vez de um percentual.

    `percentual_vaat_publicado`/`portaria_vaat_referencia`: o percentual
    oficial do VAAT (base de cálculo da complementação da União) é
    republicado pelo MEC/MF algumas vezes por exercício (3 publicações
    confirmadas em 2026, cada uma valendo até a próxima) — não vem de
    nenhum PDF já importado neste sistema, então são campos manuais,
    preenchidos pelo usuário via o mesmo CRUD das demais apurações, não
    por import. Pedido explícito do usuário: "precisamos criar um
    parâmetro para o gráfico e linha da Educação Infantil VAAT porque ele
    varia no ano" — usados como linha de referência (variável por
    bimestre, não uma linha reta) no gráfico da visão sintética.
    """

    valor_exigido = models.DecimalField("Valor exigido", max_digits=18, decimal_places=2)
    valor_aplicado = models.DecimalField("Valor aplicado", max_digits=18, decimal_places=2)
    percentual_aplicado = models.DecimalField("% aplicado", max_digits=7, decimal_places=4)
    percentual_vaat_publicado = models.DecimalField(
        "% VAAT publicado (MEC/MF)", max_digits=7, decimal_places=4, null=True, blank=True
    )
    portaria_vaat_referencia = models.CharField(
        "Portaria de referência do % VAAT", max_length=200, blank=True, default=""
    )

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração VAAT — Educação Infantil"
        verbose_name_plural = "Apurações VAAT — Educação Infantil"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"],
                name="apuracao_vaat_ed_infantil_unica_por_municipio_exercicio_bimestre",
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6), name="apuracao_vaat_ed_infantil_bimestre_1_a_6"
            ),
        ]

    @property
    def cumpre_limite(self) -> bool:
        return self.valor_aplicado >= self.valor_exigido

    def __str__(self):
        return f"VAAT Educação Infantil {self.municipio}/{self.exercicio} bim.{self.bimestre}: {self.percentual_aplicado}%"


class ApuracaoVAATDespesaCapital(ApuracaoFiscalBase):
    """
    Mínimo de 15% da Complementação da União ao FUNDEB (VAAT) aplicado em
    despesas de capital (Lei 14.113/2020, art.25) — RREO Anexo 8, mesma
    seção "INDICADORES - Art.212-A" (linha 17, logo após o indicador de
    educação infantil acima — mesmo arquivo/parser dos demais índices
    FUNDEB deste módulo).
    """

    valor_exigido = models.DecimalField("Valor exigido (15%)", max_digits=18, decimal_places=2)
    valor_aplicado = models.DecimalField("Valor aplicado", max_digits=18, decimal_places=2)
    percentual_aplicado = models.DecimalField("% aplicado", max_digits=7, decimal_places=4)

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração VAAT — Despesa de Capital"
        verbose_name_plural = "Apurações VAAT — Despesa de Capital"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"],
                name="apuracao_vaat_capital_unica_por_municipio_exercicio_bimestre",
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6), name="apuracao_vaat_capital_bimestre_1_a_6"
            ),
        ]

    @property
    def cumpre_limite(self) -> bool:
        return self.percentual_aplicado >= 15

    def __str__(self):
        return f"VAAT Despesa de Capital {self.municipio}/{self.exercicio} bim.{self.bimestre}: {self.percentual_aplicado}%"


class ApuracaoValorNaoAplicadoFundeb(ApuracaoFiscalBase):
    """
    Limite de 10% de superávit não aplicado do FUNDEB (Lei 14.113/2020,
    art.25, §3º) — RREO Anexo 8, mesma seção "INDICADORES - Art.212-A"
    (linha 18, logo após o VAAT Despesa de Capital). `valor_excedente...`
    já vem pronto do relatório como `valor_nao_aplicado - valor_maximo_
    permitido`; `cumpre_limite` usa esse excedente diretamente em vez de
    comparar o percentual (que é sobre uma base diferente do limite de
    10%, não diretamente comparável a ele).
    """

    valor_maximo_permitido = models.DecimalField(
        "Valor máximo permitido (10% de superávit)", max_digits=18, decimal_places=2
    )
    valor_nao_aplicado = models.DecimalField("Valor não aplicado", max_digits=18, decimal_places=2)
    valor_nao_aplicado_apos_ajuste = models.DecimalField(
        "Valor não aplicado após ajuste", max_digits=18, decimal_places=2
    )
    valor_excedente_ao_maximo_permitido = models.DecimalField(
        "Valor não aplicado excedente ao máximo permitido", max_digits=18, decimal_places=2
    )
    percentual_nao_aplicado = models.DecimalField("% não aplicado", max_digits=7, decimal_places=4)

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração FUNDEB — Valor Não Aplicado"
        verbose_name_plural = "Apurações FUNDEB — Valor Não Aplicado"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"],
                name="apuracao_fundeb_nao_aplicado_unica_por_municipio_exercicio_bimestre",
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6), name="apuracao_fundeb_nao_aplicado_bimestre_1_a_6"
            ),
        ]

    @property
    def cumpre_limite(self) -> bool:
        return self.valor_excedente_ao_maximo_permitido <= 0

    def __str__(self):
        return f"FUNDEB Valor Não Aplicado {self.municipio}/{self.exercicio} bim.{self.bimestre}: {self.percentual_nao_aplicado}%"


class OrigemReprogramacaoFundeb(models.TextChoices):
    IMPOSTOS = "IMPOSTOS", "19.1 - Impostos e Transferências de Impostos"
    UNIAO = "UNIAO", "19.2 - Complementação da União (VAAF+VAAT+VAAR)"


class ApuracaoReprogramacaoFundeb(ApuracaoFiscalBase):
    """
    Aplicação do Superávit de Exercício Anterior / Reprogramação do FUNDEB
    (Lei 14.113/2020, art.25, §3º) — RREO Anexo 8, mesma seção, linha 19
    (apuração COMBINADA, guardada aqui). A quebra por origem de recurso
    (19.1 impostos/transferências, 19.2 complementação da União) NÃO é
    mais um conjunto de colunas `impostos_*`/`uniao_*` — ver
    `ApuracaoReprogramacaoFundebOrigem` (tabela filha, uma linha por
    origem), mesmo racional de `ApuracaoMDEReceitaItem` acima.

    `cumpre_limite` verifica se o superávit do exercício anterior foi
    integralmente aplicado até o 1º quadrimestre do exercício atual (como
    a lei exige) — se sobrar algo não aplicado até esse prazo, é
    descumprimento.

    `valor_aplicado_*_empenhado` são a visão GERENCIAL (empenhado) ao lado
    da visão já existente (liquidado, a mesma base que `importar_mde_e_
    magisterio()`/`_calcular_aplicado_apos_quadrimestre()` usa pros campos
    sem sufixo) — mesmo racional STN-vs-GERENCIAL já usado em `ApuracaoMDE`
    (`total_gerencial_1/2/3`), pedido explícito do usuário ("fazer igual
    ao MDE e ter o cálculo gerencial informado também o valor empenhado").
    Calculados em `services.py` a partir de `LancamentoExecucaoOrcamentaria`
    nas mesmas 7 fontes de superávit do FUNDEB, nunca a partir do PDF (o
    RREO-Anexo 8 só imprime uma coluna de "aplicado", baseada em liquidado).
    """

    valor_superavit_permitido_exercicio_anterior = models.DecimalField(
        "Valor superávit permitido no exercício anterior", max_digits=18, decimal_places=2
    )
    valor_nao_aplicado_exercicio_anterior = models.DecimalField(
        "Valor não aplicado no exercício anterior", max_digits=18, decimal_places=2
    )
    valor_aplicado_ate_primeiro_quadrimestre = models.DecimalField(
        "Valor superávit aplicado até o 1º quadrimestre", max_digits=18, decimal_places=2
    )
    valor_aplicado_apos_primeiro_quadrimestre = models.DecimalField(
        "Valor aplicado após o 1º quadrimestre", max_digits=18, decimal_places=2
    )
    valor_aplicado_ate_primeiro_quadrimestre_empenhado = models.DecimalField(
        "Valor superávit aplicado até o 1º quadrimestre (gerencial — empenhado)",
        max_digits=18, decimal_places=2, default=0,
    )
    valor_aplicado_apos_primeiro_quadrimestre_empenhado = models.DecimalField(
        "Valor aplicado após o 1º quadrimestre (gerencial — empenhado)",
        max_digits=18, decimal_places=2, default=0,
    )
    valor_nao_aplicado_ate_primeiro_quadrimestre_atual = models.DecimalField(
        "Valor superávit permit. exerc. ant. não aplicado até 1º quadrimestre do exercício atual",
        max_digits=18, decimal_places=2,
    )

    class Meta(ApuracaoFiscalBase.Meta):
        verbose_name = "Apuração FUNDEB — Reprogramação (Superávit Exercício Anterior)"
        verbose_name_plural = "Apurações FUNDEB — Reprogramação (Superávit Exercício Anterior)"
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "exercicio", "bimestre"],
                name="apuracao_fundeb_reprogramacao_unica_por_municipio_exercicio_bimestre",
            ),
            models.CheckConstraint(
                condition=models.Q(bimestre__gte=1) & models.Q(bimestre__lte=6),
                name="apuracao_fundeb_reprogramacao_bimestre_1_a_6",
            ),
        ]

    @property
    def cumpre_limite(self) -> bool:
        return self.valor_nao_aplicado_ate_primeiro_quadrimestre_atual <= 0

    def __str__(self):
        return f"FUNDEB Reprogramação {self.municipio}/{self.exercicio} bim.{self.bimestre}"


class ApuracaoReprogramacaoFundebOrigem(models.Model):
    """
    Quebra por origem de recurso (19.1 impostos/transferências de
    impostos x 19.2 complementação da União VAAF+VAAT+VAAR) de uma
    `ApuracaoReprogramacaoFundeb` — duas linhas por apuração, substituindo
    as 10 colunas flat `impostos_*`/`uniao_*` que existiam antes. Mesmos
    5 campos do pai, restritos a essa origem.
    """

    apuracao = models.ForeignKey(
        ApuracaoReprogramacaoFundeb, on_delete=models.CASCADE, related_name="origens"
    )
    origem = models.CharField("Origem", max_length=20, choices=OrigemReprogramacaoFundeb.choices, db_index=True)
    valor_superavit_permitido_exercicio_anterior = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    valor_nao_aplicado_exercicio_anterior = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    valor_aplicado_ate_primeiro_quadrimestre = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    valor_aplicado_apos_primeiro_quadrimestre = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    valor_nao_aplicado_ate_primeiro_quadrimestre_atual = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Apuração FUNDEB Reprogramação — Origem"
        verbose_name_plural = "Apuração FUNDEB Reprogramação — Origens"
        ordering = ["apuracao", "origem"]
        constraints = [
            models.UniqueConstraint(fields=["apuracao", "origem"], name="apuracao_reprogramacao_origem_unica")
        ]

    def __str__(self):
        return f"{self.origem}: aplicado até 1º quad. {self.valor_aplicado_ate_primeiro_quadrimestre}"
