from rest_framework.viewsets import ModelViewSet

from apps.usuarios.mixins import RegistroManualMixin
from apps.usuarios.permissions import IsEquipeEscritorioOuSomenteLeitura, unidades_gestoras_acessiveis

from .models import RestoAPagar, SaldoBalancoConta, SaldoContaBancaria
from .serializers import RestoAPagarSerializer, SaldoBalancoContaSerializer, SaldoContaBancariaSerializer


class SaldoBalancoContaViewSet(RegistroManualMixin, ModelViewSet):
    serializer_class = SaldoBalancoContaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        usuario = self.request.user
        qs = SaldoBalancoConta.objects.filter(
            unidade_gestora__in=unidades_gestoras_acessiveis(usuario)
        ).select_related("unidade_gestora").prefetch_related("fontes__fonte_recursos")

        ug_id = self.request.query_params.get("unidade_gestora")
        if ug_id:
            qs = qs.filter(unidade_gestora_id=ug_id)
        data = self.request.query_params.get("data_referencia")
        if data:
            qs = qs.filter(data_referencia=data)
        return qs


class SaldoContaBancariaViewSet(RegistroManualMixin, ModelViewSet):
    serializer_class = SaldoContaBancariaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        usuario = self.request.user
        qs = SaldoContaBancaria.objects.filter(
            unidade_gestora__in=unidades_gestoras_acessiveis(usuario)
        ).select_related("unidade_gestora").prefetch_related("fontes__fonte_recursos")

        ug_id = self.request.query_params.get("unidade_gestora")
        if ug_id:
            qs = qs.filter(unidade_gestora_id=ug_id)
        mes = self.request.query_params.get("mes_referencia")
        if mes:
            qs = qs.filter(mes_referencia=mes)
        return qs


class RestoAPagarViewSet(RegistroManualMixin, ModelViewSet):
    serializer_class = RestoAPagarSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        usuario = self.request.user
        qs = RestoAPagar.objects.filter(
            unidade_gestora__in=unidades_gestoras_acessiveis(usuario)
        ).select_related("unidade_gestora", "fonte_recursos")

        ug_id = self.request.query_params.get("unidade_gestora")
        if ug_id:
            qs = qs.filter(unidade_gestora_id=ug_id)
        mes = self.request.query_params.get("mes_referencia")
        if mes:
            qs = qs.filter(mes_referencia=mes)
        return qs
