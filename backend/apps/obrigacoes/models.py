from datetime import date, timedelta

from django.db import models

from apps.orcamento.models import AuditoriaMixin, OrigemRegistroMixin


class EscopoObrigacao(models.TextChoices):
    MUNICIPIO = "MUNICIPIO", "Município (todo o município)"
    UNIDADE_GESTORA = "UNIDADE_GESTORA", "Unidade Gestora"


class PeriodicidadeObrigacao(models.TextChoices):
    MENSAL = "MENSAL", "Mensal"
    BIMESTRAL = "BIMESTRAL", "Bimestral"
    TRIMESTRAL = "TRIMESTRAL", "Trimestral"
    QUADRIMESTRAL = "QUADRIMESTRAL", "Quadrimestral"
    SEMESTRAL = "SEMESTRAL", "Semestral"
    ANUAL = "ANUAL", "Anual"


MESES_POR_PERIODICIDADE = {
    PeriodicidadeObrigacao.MENSAL: 1,
    PeriodicidadeObrigacao.BIMESTRAL: 2,
    PeriodicidadeObrigacao.TRIMESTRAL: 3,
    PeriodicidadeObrigacao.QUADRIMESTRAL: 4,
    PeriodicidadeObrigacao.SEMESTRAL: 6,
    PeriodicidadeObrigacao.ANUAL: 12,
}


class TipoObrigacao(models.Model):
    """
    Catálogo configurável de obrigações de controle externo — hoje, as 8
    consultas públicas do Portal NEC do TCM-PA (UNICAD, Prestação de Contas,
    Dados Contábeis, Folha de Pagamento, Mural de Licitações, Processos
    Eletrônicos, Pauta de Julgamentos, Decisões Plenárias — ver migration
    0002), mas sem nenhuma regra fixada em código: a Instrução Normativa do
    TCM-PA que rege periodicidade/prazo de cada uma ainda não foi confirmada
    pelo usuário, então `periodicidade`/`prazo_meses_apos_periodo`/
    `prazo_dia_limite` nascem NULL e `services.gerar_obrigacoes_pendentes()`
    ignora silenciosamente qualquer Tipo que ainda não tenha os 3
    configurados — basta cadastrar um novo Tipo aqui (de qualquer outro
    órgão) pra ele entrar no mesmo fluxo, sem alterar código.
    """

    nome = models.CharField("Nome", max_length=200, unique=True)
    descricao = models.TextField("Descrição", blank=True, default="")
    orgao_externo = models.CharField("Órgão externo exigente", max_length=200, blank=True, default="TCM-PA")
    escopo = models.CharField(
        "Escopo", max_length=20, choices=EscopoObrigacao.choices, default=EscopoObrigacao.MUNICIPIO
    )
    periodicidade = models.CharField(
        "Periodicidade", max_length=20, choices=PeriodicidadeObrigacao.choices, null=True, blank=True
    )
    # Prazo = (fim do período) + N meses, ajustado pro dia-limite daquele mês
    # (ex.: "até o dia 20 do mês subsequente ao bimestre" => meses=1,
    # dia_limite=20). Os dois ficam NULL até o usuário confirmar a regra
    # oficial de cada Tipo — enquanto isso, `gerar_obrigacoes_pendentes`
    # pula esse Tipo inteiro (ver services.py).
    prazo_meses_apos_periodo = models.PositiveSmallIntegerField(
        "Prazo — meses após o fim do período", null=True, blank=True
    )
    prazo_dia_limite = models.PositiveSmallIntegerField(
        "Prazo — dia-limite do mês (1-31)", null=True, blank=True
    )
    # Confirmado contra o calendário real de 2026 (12/12 meses, zero exceção)
    # para Arquivo Contábil/Arquivo de Folha de Pagamento/Matriz de Saldos
    # Contábeis: vencimento = último dia do mês subsequente (prazo_dia_limite=31,
    # já clampado pelo próprio `calcular_prazo_limite`), e quando esse dia cai
    # em sábado/domingo desloca pro próximo dia útil (segunda-feira). Não há
    # calendário de feriados no sistema — só ajusta fim de semana.
    ajustar_prazo_para_dia_util = models.BooleanField(
        "Ajustar prazo para o próximo dia útil se cair em fim de semana", default=False
    )
    dias_antecedencia_alerta = models.PositiveSmallIntegerField("Dias de antecedência para alerta", default=10)
    unidades_gestoras_restritas = models.ManyToManyField(
        "municipios.UnidadeGestora",
        blank=True,
        related_name="+",
        verbose_name="Restrito a estas Unidades Gestoras",
        help_text=(
            "Vazio = gera para todas as UGs ativas do município (padrão). Preenchido = gera só para as UGs "
            "listadas aqui, mesmo com escopo Unidade Gestora — ex. RREO/Balanço Geral/Matriz de Saldos "
            "Contábeis só são responsabilidade da Prefeitura, RGF é Prefeitura+Câmara, não os Fundos."
        ),
    )
    url_consulta = models.URLField(
        "URL de consulta pública",
        blank=True,
        default="",
        help_text='Aberta em nova aba pelo botão "Verificar agora" — o Portal NEC é uma SPA, sem deep-link por querystring.',
    )
    ativo = models.BooleanField("Ativo", default=True, db_index=True)
    ordem = models.PositiveSmallIntegerField("Ordem de exibição", default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de Obrigação"
        verbose_name_plural = "Tipos de Obrigação"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class StatusObrigacao(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    CUMPRIDA = "CUMPRIDA", "Cumprida"


class Obrigacao(OrigemRegistroMixin, AuditoriaMixin, models.Model):
    """
    Instância concreta de uma competência de `TipoObrigacao`, gerada por
    `services.gerar_obrigacoes_pendentes()` (idempotente via get_or_create) e
    fechada por um humano que resolveu o CAPTCHA do TCM-PA fora do sistema
    (ver `ObrigacaoViewSet.confirmar`). `status` só guarda PENDENTE/CUMPRIDA
    — "atrasada"/"próxima do prazo" são @property derivadas comparando
    `prazo_limite` com a data de hoje, mesmo espírito de `cumpre_limite` em
    apps.execucao_fiscal.

    NOTA: a UniqueConstraint abaixo não impede duplicatas quando
    `unidade_gestora` é NULL (NULL é distinto de NULL em unique constraints,
    tanto Postgres quanto SQLite) — a idempotência real vem do
    get_or_create em services.py, a única via de criação (nunca
    concorrente: é um clique único no dashboard).
    """

    tipo_obrigacao = models.ForeignKey(TipoObrigacao, on_delete=models.PROTECT, related_name="obrigacoes")
    municipio = models.ForeignKey("municipios.Municipio", on_delete=models.PROTECT, related_name="+")
    unidade_gestora = models.ForeignKey(
        "municipios.UnidadeGestora", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    exercicio = models.PositiveIntegerField("Exercício", db_index=True)
    numero_competencia = models.PositiveSmallIntegerField("Número da competência")
    rotulo_competencia = models.CharField("Rótulo da competência", max_length=60)
    data_fim_periodo = models.DateField("Data-fim do período de referência")
    prazo_limite = models.DateField("Prazo-limite", db_index=True)

    status = models.CharField(
        "Status", max_length=10, choices=StatusObrigacao.choices, default=StatusObrigacao.PENDENTE, db_index=True
    )
    data_cumprimento = models.DateField("Data do cumprimento constatado", null=True, blank=True)
    protocolo = models.CharField("Protocolo/identificador da consulta", max_length=100, blank=True, default="")
    observacao = models.TextField("Observação", blank=True, default="")
    comprovante = models.FileField(
        "Comprovante/Recibo",
        upload_to="obrigacoes/comprovantes/%Y/%m/",
        null=True,
        blank=True,
        help_text="PDF ou imagem do recibo visto na consulta pública/área logada — anexado manualmente ao confirmar.",
    )

    verificado_por = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    verificado_em = models.DateTimeField("Verificado em", null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Obrigação"
        verbose_name_plural = "Obrigações"
        ordering = ["prazo_limite", "municipio_id", "tipo_obrigacao_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_obrigacao", "municipio", "unidade_gestora", "exercicio", "numero_competencia"],
                name="obrigacao_unica_por_tipo_municipio_ug_exercicio_competencia",
            )
        ]

    @property
    def atrasada(self) -> bool:
        return self.status == StatusObrigacao.PENDENTE and self.prazo_limite < date.today()

    @property
    def proxima_do_prazo(self) -> bool:
        if self.status != StatusObrigacao.PENDENTE:
            return False
        hoje = date.today()
        limite = hoje + timedelta(days=self.tipo_obrigacao.dias_antecedencia_alerta)
        return hoje <= self.prazo_limite <= limite

    @property
    def situacao(self) -> str:
        if self.status == StatusObrigacao.CUMPRIDA:
            return "CUMPRIDA"
        if self.atrasada:
            return "ATRASADA"
        if self.proxima_do_prazo:
            return "PROXIMA_DO_PRAZO"
        return "PENDENTE"

    def __str__(self):
        return f"{self.tipo_obrigacao.nome} — {self.municipio} — {self.rotulo_competencia}"
