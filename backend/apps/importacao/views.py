from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.usuarios.permissions import IsEquipeEscritorioOuSomenteLeitura, municipios_acessiveis

from .dispatcher import ErroDispatcher, processar_importacao
from .models import Importacao, StatusImportacao
from .serializers import ImportacaoSerializer


class ImportacaoViewSet(ModelViewSet):
    """
    Histórico de arquivos enviados para importação. Upload grava o
    arquivo e metadados (status=PENDENTE); `POST /importacoes/<id>/processar/`
    roda o parser+service certos (ver `dispatcher.py`) e atualiza o
    próprio registro com o resultado — mesma semântica de reimportação
    (substitui, não soma) que o management command equivalente já tinha.
    """
    serializer_class = ImportacaoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = Importacao.objects.filter(
            municipio__in=municipios_acessiveis(self.request.user)
        ).select_related("municipio", "exercicio", "usuario")
        municipio_id = self.request.query_params.get("municipio")
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)
        tipo = self.request.query_params.get("tipo_relatorio")
        if tipo:
            qs = qs.filter(tipo_relatorio=tipo)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def processar(self, request, pk=None):
        importacao = self.get_object()
        if importacao.status == StatusImportacao.PROCESSANDO:
            return Response({"detail": "Esta importação já está sendo processada."}, status=409)
        try:
            processar_importacao(importacao)
        except ErroDispatcher as exc:
            return Response({"detail": str(exc)}, status=400)
        importacao.refresh_from_db()
        return Response(self.get_serializer(importacao).data)
