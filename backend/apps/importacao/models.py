from django.db import models


class SistemaOrigem(models.TextChoices):
    ASPEC = "ASPEC", "ASPEC"
    # futuros sistemas de origem entram aqui (ex.: BETHA, SAGRES, etc.)


class TipoRelatorio(models.TextChoices):
    """
    Um valor por parser/comando real do pipeline (ver CLAUDE.md "Import
    pipeline") — não mais um agrupamento grosso de 4 categorias. Cada
    valor aqui tem uma entrada correspondente em
    `apps.importacao.dispatcher.MAPEAMENTO`. Deliberadamente EXCLUÍDOS
    (não fazem sentido como "processar este arquivo enviado"):
    `gerar_execucao_orcamentaria_empenhos` (deriva do banco, não lê
    arquivo), `popular_classificacao_receita`/`importar_ementario_receita`
    (utilitários de catálogo, não parte do fluxo de relatório mensal),
    e o antigo `importar_aspec`/balancete (retirado — "não podemos mais
    depender de balancete.pdf").
    """

    ESTRUTURA_ORGANIZACIONAL = "ESTRUTURA_ORGANIZACIONAL", "Estrutura Organizacional"
    LOA_RELACIONAMENTO_ACOES = "LOA_RELACIONAMENTO_ACOES", "LOA — Relacionamento das Ações"
    LOA_DOTACOES = "LOA_DOTACOES", "LOA — Movimentos de Despesa Fixada (dotações)"
    FICHAS_DESPESA = "FICHAS_DESPESA", "Tabela de Fichas de Despesa"
    EMPENHOS = "EMPENHOS", "Relatório de Empenhos (mensal)"
    FONTES_RECURSOS = "FONTES_RECURSOS", "Fontes de Recursos"
    FICHAS_RECEITAS = "FICHAS_RECEITAS", "Classificação Econômica da Receita (fichas)"
    EXECUCAO_RECEITA = "EXECUCAO_RECEITA", "Demonstrativo da Receita por Classificação Econômica"
    SALDO_BALANCO = "SALDO_BALANCO", "Movimentos de Saldos de Balanço"
    SALDO_CONTA_BANCARIA = "SALDO_CONTA_BANCARIA", "Relação de Saldos por Conta Bancária"
    RESTOS_A_PAGAR = "RESTOS_A_PAGAR", "Demonstrativo dos Restos a Pagar"
    ENRIQUECIMENTO_RESTOS_A_PAGAR = "ENRIQUECIMENTO_RESTOS_A_PAGAR", "Saldo das Fichas de Restos a Pagar (enriquecimento)"
    DTP = "DTP", "RGF-Anexo 1 — Despesa Total com Pessoal"
    MDE_MAGISTERIO_VAAT_FUNDEB = "MDE_MAGISTERIO_VAAT_FUNDEB", "RREO-Anexo 8 — MDE/Magistério/VAAT/FUNDEB"
    ASPS = "ASPS", "RREO-Anexo XII — Ações e Serviços Públicos de Saúde"


class StatusImportacao(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    PROCESSANDO = "PROCESSANDO", "Processando"
    CONCLUIDA = "CONCLUIDA", "Concluída"
    ERRO = "ERRO", "Erro"


class Importacao(models.Model):
    """Registro de um arquivo importado (PDF, por ora) e seu processamento."""

    municipio = models.ForeignKey(
        "municipios.Municipio", on_delete=models.PROTECT, related_name="importacoes"
    )
    exercicio = models.ForeignKey(
        "orcamento.Exercicio", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="importacoes",
    )
    sistema_origem = models.CharField(
        "Sistema de origem", max_length=20, choices=SistemaOrigem.choices,
        default=SistemaOrigem.ASPEC,
    )
    tipo_relatorio = models.CharField(
        "Tipo de relatório", max_length=30, choices=TipoRelatorio.choices
    )
    arquivo = models.FileField("Arquivo", upload_to="importacoes/%Y/%m/")
    status = models.CharField(
        "Status", max_length=15, choices=StatusImportacao.choices,
        default=StatusImportacao.PENDENTE,
    )
    mensagem_erro = models.TextField("Mensagem de erro", blank=True)
    linhas_importadas = models.PositiveIntegerField("Linhas importadas", default=0)

    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="importacoes"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    processado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Importação"
        verbose_name_plural = "Importações"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_relatorio_display()} - {self.municipio} ({self.get_status_display()})"
