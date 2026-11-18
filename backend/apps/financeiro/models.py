from django.db import models

from apps.orcamento.models import AuditoriaMixin, OrigemRegistroMixin


class NaturezaSaldo(models.TextChoices):
    DEVEDOR = "D", "Devedor"
    CREDOR = "C", "Credor"


class SaldoBalancoConta(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Uma linha de "MOVIMENTOS DE SALDOS DE BALANÇO" do ASPEC — um PDF por
    Unidade Gestora, foto do saldo de cada conta bancária numa DATA
    específica (não é uma série mensal: o primeiro conjunto de arquivos
    traz só 02/01/2026, o saldo de abertura do exercício — reimportações
    futuras com datas diferentes convivem como fotos separadas).

    Cada conta pertence a uma categoria (`categoria`: "Banco", "Depósitos
    de diversas origens", "Consignações" — nem toda UG tem todas), e o
    relatório também inclui, ao final, um resumo "TOTAL das contas por
    Fontes de Recursos" que é só a mesma informação re-agregada — o parser
    ignora esse resumo (e os resumos por categoria "DETALHAMENTO da conta
    <X> por Fontes de Recursos" no meio do arquivo), nunca os trata como
    linhas de conta novas. Validado batendo a soma de `SaldoBalancoContaFonte`
    por (código, natureza) contra esses resumos, a cada campo, para a UG
    com mais contas (Prefeitura) — bateu exatamente.

    `codigo_conta` é o código interno de 3 dígitos do relatório — único
    por (unidade_gestora, categoria, data), não globalmente (o mesmo
    código "019" aparece em categorias diferentes de uma mesma UG).
    """

    unidade_gestora = models.ForeignKey(
        "municipios.UnidadeGestora", on_delete=models.PROTECT, related_name="saldos_balanco"
    )
    data_referencia = models.DateField("Data de referência", db_index=True)
    categoria = models.CharField("Categoria", max_length=100)
    codigo_conta = models.CharField("Código da conta", max_length=10)
    banco = models.CharField("Banco", max_length=100, blank=True)
    numero_conta = models.CharField("Número da conta", max_length=30, blank=True)
    apelido = models.CharField("Apelido da conta", max_length=255)
    valor = models.DecimalField("Valor", max_digits=18, decimal_places=2)
    natureza = models.CharField("Natureza", max_length=1, choices=NaturezaSaldo.choices)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Saldo de Balanço (Conta)"
        verbose_name_plural = "Saldos de Balanço (Contas)"
        ordering = ["unidade_gestora", "categoria", "codigo_conta"]
        constraints = [
            models.UniqueConstraint(
                fields=["unidade_gestora", "categoria", "codigo_conta", "data_referencia"],
                name="saldo_balanco_conta_unica_por_ug_categoria_codigo_data",
            )
        ]

    def __str__(self):
        return f"{self.apelido} ({self.data_referencia}): {self.valor} {self.natureza}"


class SaldoBalancoContaFonte(models.Model):
    """Quebra por fonte de recursos de uma SaldoBalancoConta — mesma linha do relatório, nunca um resumo."""

    conta = models.ForeignKey(SaldoBalancoConta, on_delete=models.CASCADE, related_name="fontes")
    fonte_recursos = models.ForeignKey(
        "orcamento.FonteRecursos", on_delete=models.PROTECT, related_name="saldos_balanco"
    )
    valor = models.DecimalField("Valor", max_digits=18, decimal_places=2)
    natureza = models.CharField("Natureza", max_length=1, choices=NaturezaSaldo.choices)

    class Meta:
        verbose_name = "Saldo de Balanço (Fonte)"
        verbose_name_plural = "Saldos de Balanço (Fontes)"
        constraints = [
            models.UniqueConstraint(fields=["conta", "fonte_recursos"], name="saldo_balanco_fonte_unica_por_conta")
        ]

    def __str__(self):
        return f"{self.fonte_recursos.codigo} - {self.valor} {self.natureza}"


class SaldoContaBancaria(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Uma linha de "Relação de saldos - Por UG titular da conta" do ASPEC —
    um PDF por Unidade Gestora, **mensal** (pasta `DADOS/SALDO/CONTAS/<mês>/`,
    data do cabeçalho é o último dia do mês — "31/01/2026" para o mês 01).

    Diferente de `SaldoBalancoConta`: aqui cada conta traz DOIS valores
    (`saldo_pre_pagamentos_previstos` e `saldo_nao_comprometido`), sem
    natureza D/C na linha da conta (só nas linhas de fonte). O relatório
    tem três camadas de resumo a ignorar, nessa ordem — "TOTAL DA CONTA
    BANCO...", "Detalhamento da conta BANCO por fontes de recursos" (+ seu
    "TOTAL detalhamento..."), e no fim "Detalhamento geral de todas as
    contas" + "TOTAL GERAL DETALHAMENTO TODAS CONTAS" — todas elas repetem
    dados já capturados nas linhas de conta reais; o parser para de ler o
    arquivo assim que encontra qualquer uma delas (nunca aparecem seguidas
    de mais contas reais nos arquivos vistos). Confirmado perdendo o
    resumo por engano uma vez durante o desenvolvimento (dobrava os
    valores por fonte) — corrigido e revalidado batendo exatamente contra
    o "TOTAL GERAL DETALHAMENTO TODAS CONTAS" da Prefeitura.
    """

    unidade_gestora = models.ForeignKey(
        "municipios.UnidadeGestora", on_delete=models.PROTECT, related_name="saldos_conta_bancaria"
    )
    mes_referencia = models.PositiveSmallIntegerField("Mês de referência", db_index=True)
    data_referencia = models.DateField("Data de referência", db_index=True)
    banco = models.CharField("Banco", max_length=100)
    numero_conta = models.CharField("Número da conta", max_length=30)
    apelido = models.CharField("Apelido da conta", max_length=255)
    saldo_pre_pagamentos_previstos = models.DecimalField(
        "Saldo pré-pagamentos já previstos", max_digits=18, decimal_places=2
    )
    saldo_nao_comprometido = models.DecimalField("Saldo não comprometido", max_digits=18, decimal_places=2)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Saldo por Conta Bancária"
        verbose_name_plural = "Saldos por Conta Bancária"
        ordering = ["unidade_gestora", "mes_referencia", "numero_conta"]
        constraints = [
            models.UniqueConstraint(
                fields=["unidade_gestora", "numero_conta", "mes_referencia"],
                name="saldo_conta_bancaria_unica_por_ug_conta_mes",
            )
        ]

    def __str__(self):
        return f"{self.apelido} - mês {self.mes_referencia} ({self.saldo_nao_comprometido})"


class SaldoContaBancariaFonte(models.Model):
    """Quebra por fonte de recursos de uma SaldoContaBancaria."""

    conta = models.ForeignKey(SaldoContaBancaria, on_delete=models.CASCADE, related_name="fontes")
    fonte_recursos = models.ForeignKey(
        "orcamento.FonteRecursos", on_delete=models.PROTECT, related_name="saldos_conta_bancaria"
    )
    valor = models.DecimalField("Valor", max_digits=18, decimal_places=2)
    natureza = models.CharField("Natureza", max_length=1, choices=NaturezaSaldo.choices, blank=True)

    class Meta:
        verbose_name = "Saldo por Conta Bancária (Fonte)"
        verbose_name_plural = "Saldos por Conta Bancária (Fontes)"
        constraints = [
            models.UniqueConstraint(
                fields=["conta", "fonte_recursos"], name="saldo_conta_bancaria_fonte_unica_por_conta"
            )
        ]

    def __str__(self):
        return f"{self.fonte_recursos.codigo} - {self.valor} {self.natureza}"


class RestoAPagar(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Uma linha de "DEMONSTRATIVO DOS RESTOS A PAGAR POR FONTE DE RECURSOS"
    do ASPEC — **um PDF por mês cobrindo TODAS as UGs** (diferente dos
    relatórios de saldo, que são um PDF por UG) — `RP01.PDF`..`RP09.PDF`.

    Cada linha é um empenho de um EXERCÍCIO ANTERIOR (2020-2025 nos dados
    vistos) que ainda tinha resto a pagar pendente naquele mês — não tem
    relação direta com o `Empenho` do exercício corrente (apps.orcamento),
    cujos registros começam em 2026; por isso `numero_empenho` e
    `exercicio_origem` ficam como campos próprios, não uma FK.

    **Não é uma série de movimentos mensais a somar** (ao contrário de
    `EmpenhoMovimento`/`LancamentoExecucaoReceita`): é um relatório
    CUMULATIVO reimpresso por inteiro todo mês — confirmado comparando
    RP01 e RP09: as 411 linhas e os valores de `inscricao_processada`/
    `inscricao_nao_processada` são IDÊNTICOS nos dois (são fatos fixados
    uma vez, no exercício de origem do empenho), enquanto `liquidacao`/
    `rpp_pago`/`rpnp_pago` crescem mês a mês (ex.: RPNP pago salta de
    R$1,44M em janeiro para R$17,67M em setembro) — cada arquivo mostra o
    ACUMULADO até aquele mês, não o incremento. Por isso a importação
    SUBSTITUI (delete + recreate) os dados daquele mês inteiro — nunca some
    com meses anteriores.

    Cada arquivo também tem uma seção final "Consolidado" (páginas extras,
    mesma UG-like label) que é só a re-agregação de todas as UGs já lidas —
    descartada pelo parser, nunca tratada como uma UG adicional (validado
    somando as 7 UGs reais e batendo com o "Total geral" do Consolidado,
    em todas as 7 colunas, tanto em janeiro quanto em setembro).
    """

    unidade_gestora = models.ForeignKey(
        "municipios.UnidadeGestora", on_delete=models.PROTECT, related_name="restos_a_pagar"
    )
    fonte_recursos = models.ForeignKey(
        "orcamento.FonteRecursos", on_delete=models.PROTECT, related_name="restos_a_pagar"
    )
    mes_referencia = models.PositiveSmallIntegerField("Mês de referência", db_index=True)
    exercicio_origem = models.PositiveIntegerField("Exercício de origem do empenho")
    numero_empenho = models.CharField("Número do empenho", max_length=20)

    inscricao_processada = models.DecimalField("Inscrição processada", max_digits=18, decimal_places=2, default=0)
    inscricao_nao_processada = models.DecimalField(
        "Inscrição não processada", max_digits=18, decimal_places=2, default=0
    )
    reinscricao = models.DecimalField("Reinscrição", max_digits=18, decimal_places=2, default=0)
    cancelamento = models.DecimalField("Cancelamento", max_digits=18, decimal_places=2, default=0)
    liquidacao = models.DecimalField("Liquidação", max_digits=18, decimal_places=2, default=0)
    rpp_pago = models.DecimalField("RPP Pago", max_digits=18, decimal_places=2, default=0)
    rpnp_pago = models.DecimalField("RPNP Pago", max_digits=18, decimal_places=2, default=0)

    # Enriquecimento opcional a partir de "SALDO DAS FICHAS DE RESTOS A PAGAR"
    # (FICHAS_RESTOS.PDF, foto de 02/01/2026) — ver
    # services.enriquecer_restos_a_pagar_fichas(). RP0x.PDF (acima) não dá
    # classificação nem credor; nulo/"" para todo registro que esse
    # relatório não cobriu ou que ainda não foi enriquecido.
    credor_nome = models.CharField("Credor", max_length=255, blank=True)
    orgao = models.ForeignKey(
        "municipios.Orgao", on_delete=models.SET_NULL, null=True, blank=True, related_name="restos_a_pagar"
    )
    unidade_orcamentaria = models.ForeignKey(
        "municipios.UnidadeOrcamentaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restos_a_pagar",
    )
    elemento_despesa = models.ForeignKey(
        "orcamento.ElementoDespesa", on_delete=models.SET_NULL, null=True, blank=True, related_name="restos_a_pagar"
    )
    classificacao_funcional_programatica = models.CharField(
        "Classificação funcional-programática (função.subfunção.programa.ação)", max_length=20, blank=True
    )
    acao_nome = models.CharField("Nome da ação", max_length=255, blank=True)
    # Código completo "categoria.grupo.modalidade.elemento.subelemento" (ex.:
    # "3.3.90.30.00") tal como impresso em FICHAS_RESTOS.PDF — `elemento_despesa`
    # (acima) só resolve o segmento de elemento (2 dígitos) contra o catálogo
    # nacional atual; este campo preserva a classificação econômica completa do
    # empenho histórico, que não tem FK estável (categoria/grupo/modalidade não
    # são chaves próprias neste app, só compõem o código do elemento).
    classificacao_economica_codigo = models.CharField(
        "Classificação econômica (categoria.grupo.modalidade.elemento.subelemento)", max_length=20, blank=True
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resto a Pagar"
        verbose_name_plural = "Restos a Pagar"
        ordering = ["unidade_gestora", "fonte_recursos", "exercicio_origem", "numero_empenho"]
        constraints = [
            models.UniqueConstraint(
                fields=["unidade_gestora", "fonte_recursos", "exercicio_origem", "numero_empenho", "mes_referencia"],
                name="resto_a_pagar_unico_por_ug_fonte_exercicio_numero_mes",
            )
        ]

    @property
    def pago_total(self):
        return self.rpp_pago + self.rpnp_pago

    def __str__(self):
        return f"{self.exercicio_origem}/{self.numero_empenho} - mês {self.mes_referencia} ({self.pago_total})"
