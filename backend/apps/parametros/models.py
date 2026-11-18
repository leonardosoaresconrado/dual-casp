from django.db import models


class Parametro(models.Model):
    """
    Configurações globais simples (chave/valor booleano), editáveis em
    Administração > Parâmetros — nunca por-município, afetam a interface
    igualmente para todos os usuários do sistema (equipe do escritório e
    clientes). Pedido do usuário: "esses avisos em azul, poderíamos
    parametrizar em Administração -> Parâmetros exibir ou não".

    `chave`/`descricao` não são editáveis via API (ver `ParametroSerializer`)
    — os parâmetros são predefinidos pelo sistema (uma por migration de
    seed, ver `0002_seed_...`), só o `valor_booleano` é ajustável pelo
    usuário. O modelo é genérico (chave/valor) de propósito, pra um novo
    parâmetro no futuro não precisar de uma tabela/migration de schema
    nova — só mais uma linha.
    """

    chave = models.SlugField("Chave", max_length=100, unique=True)
    descricao = models.CharField("Descrição", max_length=255)
    valor_booleano = models.BooleanField("Valor", default=True)

    class Meta:
        verbose_name = "Parâmetro do Sistema"
        verbose_name_plural = "Parâmetros do Sistema"
        ordering = ["chave"]

    def __str__(self):
        return self.chave
