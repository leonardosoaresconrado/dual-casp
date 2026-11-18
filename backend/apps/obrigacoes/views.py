from datetime import date

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.usuarios.permissions import IsEquipeEscritorioOuSomenteLeitura, aplicar_filtro_ativo, municipios_acessiveis

from .models import Obrigacao, StatusObrigacao, TipoObrigacao
from .serializers import ObrigacaoSerializer, TipoObrigacaoSerializer
from .services import gerar_obrigacoes_pendentes


def _aplicar_confirmacao(obrigacao, usuario, dados, arquivo=None):
    cumprida = bool(dados.get("cumprida"))

    obrigacao.verificado_por = usuario
    obrigacao.verificado_em = timezone.now()
    if "protocolo" in dados:
        obrigacao.protocolo = dados.get("protocolo") or ""
    if "observacao" in dados:
        obrigacao.observacao = dados.get("observacao") or ""
    if arquivo is not None:
        obrigacao.comprovante = arquivo

    if cumprida:
        obrigacao.status = StatusObrigacao.CUMPRIDA
        data_cumprimento = dados.get("data_cumprimento")
        obrigacao.data_cumprimento = data_cumprimento or date.today().isoformat()

    obrigacao.save()


class TipoObrigacaoViewSet(ModelViewSet):
    """Catálogo global (não escopado por município) — mesmo padrão de FonteRecursosViewSet."""

    serializer_class = TipoObrigacaoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        return aplicar_filtro_ativo(self.request, TipoObrigacao.objects.all())


class ObrigacaoViewSet(ModelViewSet):
    serializer_class = ObrigacaoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = Obrigacao.objects.select_related("tipo_obrigacao", "municipio", "unidade_gestora").filter(
            municipio__in=municipios_acessiveis(self.request.user)
        )
        municipio_id = self.request.query_params.get("municipio")
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)
        exercicio = self.request.query_params.get("exercicio")
        if exercicio:
            qs = qs.filter(exercicio=exercicio)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    @action(detail=False, methods=["post"], url_path="gerar")
    def gerar(self, request):
        """
        Chamada pelo frontend ao montar o painel (`ObrigacoesPage`) — gera
        (idempotente) as competências pendentes dos Tipos já configurados para
        o(s) município(s) acessíveis ao usuário, opcionalmente restrito a
        `?municipio=<id>`.
        """
        municipios = municipios_acessiveis(request.user)
        municipio_id = request.query_params.get("municipio")
        if municipio_id:
            municipios = municipios.filter(id=municipio_id)
        criadas = gerar_obrigacoes_pendentes(municipios)
        return Response({"criadas": criadas})

    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        """
        Fecha o ciclo de verificação manual — sempre grava
        verificado_por/verificado_em (toda tentativa fica registrada, mesmo
        se cumprida=False), só avança o status para CUMPRIDA quando
        `cumprida=true`. Aceita multipart com `comprovante` (PDF/imagem do
        recibo visto na consulta) — anexado manualmente, nunca baixado
        automaticamente de nenhum sistema do TCM-PA.
        """
        obrigacao = self.get_object()
        _aplicar_confirmacao(obrigacao, request.user, request.data, request.FILES.get("comprovante"))
        return Response(ObrigacaoSerializer(obrigacao, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="confirmar-lote")
    def confirmar_lote(self, request):
        """
        Mesma confirmação de `confirmar`, aplicada a vários IDs de uma vez —
        ex. "tudo que vence em Janeiro/2026" selecionado de uma vez no
        painel, ou importar em lote um histórico de competências já
        entregues antes deste sistema existir. `ids` é restrito ao
        queryset já filtrado por `municipios_acessiveis`, então não dá pra
        confirmar uma obrigação de um município sem acesso.
        """
        ids = request.data.get("ids") or []
        obrigacoes = list(self.get_queryset().filter(id__in=ids))
        for obrigacao in obrigacoes:
            _aplicar_confirmacao(obrigacao, request.user, request.data)
        return Response({"confirmadas": len(obrigacoes)})
