from django.db import models


class Municipio(models.Model):
    UF_CHOICES = [
        ("AC", "AC"), ("AL", "AL"), ("AP", "AP"), ("AM", "AM"), ("BA", "BA"),
        ("CE", "CE"), ("DF", "DF"), ("ES", "ES"), ("GO", "GO"), ("MA", "MA"),
        ("MT", "MT"), ("MS", "MS"), ("MG", "MG"), ("PA", "PA"), ("PB", "PB"),
        ("PR", "PR"), ("PE", "PE"), ("PI", "PI"), ("RJ", "RJ"), ("RN", "RN"),
        ("RS", "RS"), ("RO", "RO"), ("RR", "RR"), ("SC", "SC"), ("SP", "SP"),
        ("SE", "SE"), ("TO", "TO"),
    ]

    nome = models.CharField("Nome", max_length=150)
    uf = models.CharField("UF", max_length=2, choices=UF_CHOICES)
    codigo_ibge = models.CharField("Código IBGE", max_length=7, unique=True)
    ativo = models.BooleanField("Ativo", default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["nome", "uf"], name="municipio_unico_por_uf")
        ]

    def __str__(self):
        return f"{self.nome}/{self.uf}"


class PoderEnum(models.TextChoices):
    EXECUTIVO = "EXECUTIVO", "Executivo"
    LEGISLATIVO = "LEGISLATIVO", "Legislativo"


class UnidadeGestora(models.Model):
    """
    Unidade Gestora (UG): Prefeitura, Câmara, Fundo Municipal de Saúde,
    RPPS, autarquias etc. Cada UG pertence a um único município.
    """

    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name="unidades_gestoras"
    )
    codigo = models.CharField("Código da UG", max_length=20)
    nome = models.CharField("Nome", max_length=200)
    poder = models.CharField("Poder", max_length=20, choices=PoderEnum.choices)
    cnpj = models.CharField("CNPJ", max_length=14, blank=True)
    ativo = models.BooleanField("Ativo", default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Unidade Gestora"
        verbose_name_plural = "Unidades Gestoras"
        ordering = ["municipio__nome", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "codigo"], name="ug_codigo_unico_por_municipio"
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.municipio.nome}/{self.municipio.uf})"


class Orgao(models.Model):
    """
    Órgão da estrutura organizacional do município (ex.: Secretaria,
    Gabinete) — ex.: "Secretaria Municipal de Educação" pertence ao
    município, não a uma Unidade Gestora específica. Isso porque um mesmo
    órgão pode ter unidades orçamentárias geridas por UGs diferentes (ex.:
    a Secretaria de Educação tem uma unidade na Prefeitura/no Fundo
    Municipal de Educação e outra no FUNDEB) — ver UnidadeOrcamentaria,
    que é o nível em que a Unidade Gestora de fato se liga.
    """

    municipio = models.ForeignKey(
        Municipio, on_delete=models.PROTECT, related_name="orgaos"
    )
    codigo = models.CharField("Código do órgão", max_length=20)
    nome = models.CharField("Nome", max_length=200)
    ativo = models.BooleanField("Ativo", default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Órgão"
        verbose_name_plural = "Órgãos"
        ordering = ["municipio", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "codigo"], name="orgao_codigo_unico_por_municipio"
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.municipio.nome})"


class UnidadeOrcamentaria(models.Model):
    """
    Unidade Orçamentária: subdivisão de um Órgão para fins de execução do
    orçamento. É aqui que a Unidade Gestora responsável pela execução
    daquela unidade é de fato definida (ver nota em Orgao).
    """

    orgao = models.ForeignKey(Orgao, on_delete=models.PROTECT, related_name="unidades_orcamentarias")
    unidade_gestora = models.ForeignKey(
        UnidadeGestora, on_delete=models.PROTECT, related_name="unidades_orcamentarias"
    )
    codigo = models.CharField("Código da unidade orçamentária", max_length=20)
    nome = models.CharField("Nome", max_length=200)
    ativo = models.BooleanField("Ativo", default=True, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Unidade Orçamentária"
        verbose_name_plural = "Unidades Orçamentárias"
        ordering = ["orgao", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["orgao", "codigo"], name="unidade_orcamentaria_codigo_unico_por_orgao"
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.orgao.nome})"
