from rest_framework.viewsets import ModelViewSet

from apps.usuarios.permissions import (
    aplicar_filtro_ativo,
    municipios_acessiveis,
    orgaos_acessiveis,
    unidades_gestoras_acessiveis,
)

from .models import Municipio, Orgao, UnidadeGestora, UnidadeOrcamentaria
from .permissions import IsEquipeEscritorioOuSomenteLeitura
from .serializers import (
    MunicipioSerializer,
    OrgaoSerializer,
    UnidadeGestoraSerializer,
    UnidadeOrcamentariaSerializer,
)


class MunicipioViewSet(ModelViewSet):
    serializer_class = MunicipioSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        return municipios_acessiveis(self.request.user)


class UnidadeGestoraViewSet(ModelViewSet):
    serializer_class = UnidadeGestoraSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = unidades_gestoras_acessiveis(self.request.user)
        municipio_id = self.request.query_params.get("municipio")
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)
        return qs


class OrgaoViewSet(ModelViewSet):
    serializer_class = OrgaoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = orgaos_acessiveis(self.request.user)
        municipio_id = self.request.query_params.get("municipio")
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)
        ug_id = self.request.query_params.get("unidade_gestora")
        if ug_id:
            qs = qs.filter(unidades_orcamentarias__unidade_gestora_id=ug_id).distinct()
        return qs


class UnidadeOrcamentariaViewSet(ModelViewSet):
    serializer_class = UnidadeOrcamentariaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = aplicar_filtro_ativo(
            self.request,
            UnidadeOrcamentaria.objects.filter(
                orgao__in=orgaos_acessiveis(self.request.user)
            ).select_related("orgao", "unidade_gestora"),
        )
        orgao_id = self.request.query_params.get("orgao")
        if orgao_id:
            qs = qs.filter(orgao_id=orgao_id)
        ug_id = self.request.query_params.get("unidade_gestora")
        if ug_id:
            qs = qs.filter(unidade_gestora_id=ug_id)
        return qs
