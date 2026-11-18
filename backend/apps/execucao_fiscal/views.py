from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.importacao.services import (
    _calcular_aplicacao_pnae_recursos_proprios,
    _calcular_despesa_ensino_medio_superior_recursos_proprios,
)
from apps.usuarios.mixins import RegistroManualMixin
from apps.usuarios.permissions import IsEquipeEscritorioOuSomenteLeitura, municipios_acessiveis

from .models import (
    ApuracaoASPS,
    ApuracaoDTP,
    ApuracaoETIFundeb,
    ApuracaoMagisterioFundeb,
    ApuracaoMDE,
    ApuracaoReprogramacaoFundeb,
    ApuracaoVAATDespesaCapital,
    ApuracaoVAATEducacaoInfantil,
    ApuracaoValorNaoAplicadoFundeb,
)
from .serializers import (
    ApuracaoASPSSerializer,
    ApuracaoDTPSerializer,
    ApuracaoETIFundebSerializer,
    ApuracaoMagisterioFundebSerializer,
    ApuracaoMDESerializer,
    ApuracaoReprogramacaoFundebSerializer,
    ApuracaoVAATDespesaCapitalSerializer,
    ApuracaoVAATEducacaoInfantilSerializer,
    ApuracaoValorNaoAplicadoFundebSerializer,
)


class _ApuracaoFiscalViewSetBase(RegistroManualMixin, ModelViewSet):
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = self.queryset_model.objects.filter(municipio__in=municipios_acessiveis(self.request.user))
        municipio_id = self.request.query_params.get("municipio")
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)
        exercicio = self.request.query_params.get("exercicio")
        if exercicio:
            qs = qs.filter(exercicio=exercicio)
        return qs


class ApuracaoDTPViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoDTPSerializer
    queryset_model = ApuracaoDTP


class ApuracaoMDEViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoMDESerializer
    queryset_model = ApuracaoMDE

    @action(detail=False, methods=["post"], url_path="recalcular-mde-derivados")
    def recalcular_mde_derivados(self, request):
        """
        Recalcula `aplicacao_pnae_recursos_proprios` e
        `despesa_ensino_medio_superior_recursos_proprios` de todos os
        bimestres já importados pro município/exercício informado (query
        params, mesmo filtro de `get_queryset()`) — sem precisar
        reimportar o PDF do RREO, já que os dois campos são 100%
        derivados da execução orçamentária real, nunca do relatório.
        Chamado pelo frontend depois de alterar quais Ações têm
        `desconsiderar_pnae_peae=True` (gerenciado direto no
        demonstrativo, `ExecucaoFiscalDetalhadoPage`) — a despesa de
        ensino médio/superior não depende de flag nenhuma, mas é
        recalculada junto por simplicidade (mesmo botão, mesma ação).
        """
        atualizados = 0
        for apuracao in self.get_queryset():
            apuracao.aplicacao_pnae_recursos_proprios = _calcular_aplicacao_pnae_recursos_proprios(
                apuracao.municipio, apuracao.bimestre
            )
            apuracao.despesa_ensino_medio_superior_recursos_proprios = (
                _calcular_despesa_ensino_medio_superior_recursos_proprios(apuracao.municipio, apuracao.bimestre)
            )
            apuracao.save(
                update_fields=["aplicacao_pnae_recursos_proprios", "despesa_ensino_medio_superior_recursos_proprios"]
            )
            atualizados += 1
        return Response({"atualizados": atualizados})


class ApuracaoMagisterioFundebViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoMagisterioFundebSerializer
    queryset_model = ApuracaoMagisterioFundeb


class ApuracaoETIFundebViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoETIFundebSerializer
    queryset_model = ApuracaoETIFundeb


class ApuracaoASPSViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoASPSSerializer
    queryset_model = ApuracaoASPS


class ApuracaoVAATEducacaoInfantilViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoVAATEducacaoInfantilSerializer
    queryset_model = ApuracaoVAATEducacaoInfantil


class ApuracaoVAATDespesaCapitalViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoVAATDespesaCapitalSerializer
    queryset_model = ApuracaoVAATDespesaCapital


class ApuracaoValorNaoAplicadoFundebViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoValorNaoAplicadoFundebSerializer
    queryset_model = ApuracaoValorNaoAplicadoFundeb


class ApuracaoReprogramacaoFundebViewSet(_ApuracaoFiscalViewSetBase):
    serializer_class = ApuracaoReprogramacaoFundebSerializer
    queryset_model = ApuracaoReprogramacaoFundeb
