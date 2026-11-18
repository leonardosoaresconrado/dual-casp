"""
Helpers para resolver o escopo de acesso Município -> UG -> Órgão de um usuário.

Usuários da equipe do escritório (is_equipe_escritorio=True) têm acesso
irrestrito. Demais usuários só acessam o que estiver liberado em
VinculoAcesso, respeitando a hierarquia: um vínculo em nível de município
libera todas as UGs/órgãos daquele município; um vínculo em nível de UG
libera todos os órgãos daquela UG.
"""

from django.db.models import Q, QuerySet
from rest_framework.permissions import BasePermission


class IsEquipeEscritorioOuSomenteLeitura(BasePermission):
    """Escrita restrita à equipe do escritório; leitura segue o queryset filtrado por acesso."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return bool(request.user.is_equipe_escritorio or request.user.is_superuser)


class IsEquipeEscritorio(BasePermission):
    """
    Acesso total (leitura e escrita) restrito à equipe do escritório —
    diferente de `IsEquipeEscritorioOuSomenteLeitura`, aqui nem leitura é
    liberada para usuários de cliente. Usado em `Usuario`/`VinculoAcesso`:
    um usuário de prefeitura/câmara não deve conseguir listar outros
    usuários do sistema (nome/CPF de terceiros) nem os vínculos de acesso
    de ninguém.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return bool(request.user.is_equipe_escritorio or request.user.is_superuser)


def municipios_acessiveis(usuario) -> QuerySet:
    from apps.municipios.models import Municipio

    if usuario.is_equipe_escritorio or usuario.is_superuser:
        return Municipio.objects.filter(ativo=True)

    ids = usuario.vinculos_acesso.values_list("municipio_id", flat=True)
    return Municipio.objects.filter(id__in=ids, ativo=True)


def unidades_gestoras_acessiveis(usuario) -> QuerySet:
    from apps.municipios.models import UnidadeGestora

    if usuario.is_equipe_escritorio or usuario.is_superuser:
        return UnidadeGestora.objects.filter(ativo=True)

    vinculos = usuario.vinculos_acesso.all()
    municipios_amplos = vinculos.filter(unidade_gestora__isnull=True).values_list(
        "municipio_id", flat=True
    )
    ugs_diretas = vinculos.filter(unidade_gestora__isnull=False).values_list(
        "unidade_gestora_id", flat=True
    )
    return UnidadeGestora.objects.filter(
        Q(municipio_id__in=municipios_amplos) | Q(id__in=ugs_diretas),
        ativo=True,
    )


def orgaos_acessiveis(usuario) -> QuerySet:
    """
    Órgão não pertence a uma única UG (ver nota em municipios.models.Orgao),
    então um vínculo em nível de UG libera os órgãos que tenham QUALQUER
    unidade orçamentária naquela UG — não necessariamente o órgão inteiro.
    """
    from apps.municipios.models import Orgao

    if usuario.is_equipe_escritorio or usuario.is_superuser:
        return Orgao.objects.filter(ativo=True)

    vinculos = usuario.vinculos_acesso.all()
    municipios_amplos = vinculos.filter(unidade_gestora__isnull=True, orgao__isnull=True).values_list(
        "municipio_id", flat=True
    )
    ugs_amplas = vinculos.filter(
        unidade_gestora__isnull=False, orgao__isnull=True
    ).values_list("unidade_gestora_id", flat=True)
    orgaos_diretos = vinculos.filter(orgao__isnull=False).values_list(
        "orgao_id", flat=True
    )
    return Orgao.objects.filter(
        Q(municipio_id__in=municipios_amplos)
        | Q(unidades_orcamentarias__unidade_gestora_id__in=ugs_amplas)
        | Q(id__in=orgaos_diretos),
        ativo=True,
    ).distinct()


def aplicar_filtro_ativo(request, queryset) -> QuerySet:
    """
    Esconde registros `ativo=False` por padrão em cadastros — antes disso
    nenhum get_queryset filtrava por `ativo`, então desativar um registro
    não tinha efeito nenhum na listagem. `?incluir_inativos=1` religa a
    visão completa (necessário na própria tela de cadastro para poder
    reativar algo).
    """
    if request.query_params.get("incluir_inativos"):
        return queryset
    return queryset.filter(ativo=True)


def tem_acesso(usuario, municipio=None, unidade_gestora=None, orgao=None) -> bool:
    """Verifica se o usuário tem acesso ao escopo mais específico informado."""

    if usuario.is_equipe_escritorio or usuario.is_superuser:
        return True

    if orgao is not None:
        return orgaos_acessiveis(usuario).filter(pk=orgao.pk).exists()
    if unidade_gestora is not None:
        return unidades_gestoras_acessiveis(usuario).filter(pk=unidade_gestora.pk).exists()
    if municipio is not None:
        return municipios_acessiveis(usuario).filter(pk=municipio.pk).exists()
    return False
