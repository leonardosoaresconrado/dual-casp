from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from .managers import UsuarioManager
from .validators import validar_cpf


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Usuário do sistema. Login é feito pelo CPF (somente dígitos)."""

    cpf = models.CharField(
        "CPF",
        max_length=11,
        unique=True,
        validators=[
            RegexValidator(r"^\d{11}$", "O CPF deve conter exatamente 11 dígitos."),
            validar_cpf,
        ],
        help_text="Somente dígitos, sem pontuação.",
    )
    nome_completo = models.CharField("Nome completo", max_length=150)
    email = models.EmailField("E-mail", blank=True)
    telefone = models.CharField("Telefone", max_length=20, blank=True)

    is_equipe_escritorio = models.BooleanField(
        "Equipe do escritório",
        default=False,
        help_text=(
            "Usuários da equipe do escritório têm acesso irrestrito a todos os "
            "municípios/câmaras. Usuários de clientes (prefeitura/câmara) devem "
            "ter esta opção desmarcada e receber Vínculos de Acesso específicos."
        ),
    )
    is_active = models.BooleanField("Ativo", default=True)
    is_staff = models.BooleanField("Acesso ao admin", default=False)

    date_joined = models.DateTimeField("Data de cadastro", auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "cpf"
    REQUIRED_FIELDS = ["nome_completo"]

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["nome_completo"]

    def __str__(self):
        return f"{self.nome_completo} ({self.cpf_formatado})"

    @property
    def cpf_formatado(self) -> str:
        c = self.cpf
        return f"{c[0:3]}.{c[3:6]}.{c[6:9]}-{c[9:11]}" if len(c) == 11 else c


class PapelAcesso(models.TextChoices):
    ADMINISTRADOR = "ADMIN", "Administrador"
    GESTOR = "GESTOR", "Gestor"
    ANALISTA = "ANALISTA", "Analista"
    VISUALIZACAO = "VISUALIZACAO", "Somente visualização"


class VinculoAcesso(models.Model):
    """
    Concede a um usuário acesso a um escopo do município: Unidade Gestora
    e/ou Órgão (independentes entre si — um órgão pode ter unidades
    orçamentárias em UGs diferentes, ver nota em municipios.models.Orgao).

    - unidade_gestora e orgao em branco: acesso a todo o município.
    - unidade_gestora preenchida (orgao em branco): acesso a toda a UG.
    - orgao preenchido (unidade_gestora em branco): acesso a esse órgão
      inteiro, em qualquer UG que ele tenha unidades.
    - os dois preenchidos: acesso restrito às unidades orçamentárias
      desse órgão que pertencem a essa UG especificamente.
    """

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="vinculos_acesso"
    )
    municipio = models.ForeignKey(
        "municipios.Municipio", on_delete=models.CASCADE, related_name="vinculos_acesso"
    )
    unidade_gestora = models.ForeignKey(
        "municipios.UnidadeGestora",
        on_delete=models.CASCADE,
        related_name="vinculos_acesso",
        null=True,
        blank=True,
    )
    orgao = models.ForeignKey(
        "municipios.Orgao",
        on_delete=models.CASCADE,
        related_name="vinculos_acesso",
        null=True,
        blank=True,
    )
    papel = models.CharField(
        "Papel", max_length=20, choices=PapelAcesso.choices, default=PapelAcesso.VISUALIZACAO
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vínculo de acesso"
        verbose_name_plural = "Vínculos de acesso"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "municipio", "unidade_gestora", "orgao"],
                name="vinculo_unico_por_escopo",
            ),
            # A UniqueConstraint acima não pega duplicatas quando
            # unidade_gestora/orgao são NULL — NULL não é igual a NULL em
            # SQLite/Postgres, então duas linhas idênticas de "acesso ao
            # município inteiro" (os dois nulos) passariam pela constraint
            # de cima sem erro. As 3 constraints condicionais abaixo
            # cobrem especificamente os 3 casos com algum campo nulo.
            models.UniqueConstraint(
                fields=["usuario", "municipio"],
                condition=models.Q(unidade_gestora__isnull=True, orgao__isnull=True),
                name="vinculo_unico_municipio_inteiro",
            ),
            models.UniqueConstraint(
                fields=["usuario", "municipio", "unidade_gestora"],
                condition=models.Q(orgao__isnull=True),
                name="vinculo_unico_por_ug_inteira",
            ),
            models.UniqueConstraint(
                fields=["usuario", "municipio", "orgao"],
                condition=models.Q(unidade_gestora__isnull=True),
                name="vinculo_unico_por_orgao_inteiro",
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.orgao_id and self.unidade_gestora_id:
            existe = self.orgao.unidades_orcamentarias.filter(
                unidade_gestora_id=self.unidade_gestora_id
            ).exists()
            if not existe:
                raise ValidationError(
                    "O órgão informado não tem nenhuma unidade orçamentária na unidade gestora selecionada."
                )
        if self.unidade_gestora and self.unidade_gestora.municipio_id != self.municipio_id:
            raise ValidationError("A unidade gestora informada não pertence ao município selecionado.")

    def __str__(self):
        escopo = self.municipio.nome
        if self.unidade_gestora:
            escopo += f" / {self.unidade_gestora.nome}"
        if self.orgao:
            escopo += f" / {self.orgao.nome}"
        return f"{self.usuario.nome_completo} -> {escopo} ({self.get_papel_display()})"
