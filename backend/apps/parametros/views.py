from rest_framework import mixins, viewsets

from apps.usuarios.permissions import IsEquipeEscritorioOuSomenteLeitura

from .models import Parametro
from .serializers import ParametroSerializer


class ParametroViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Só list/retrieve/update — nunca create/delete via API, já que os
    parâmetros são predefinidos (ver models.py). `lookup_field = "chave"`
    deixa o frontend sempre apontar pra uma URL estável
    (`/parametros/exibir_avisos_informativos/`) em vez de depender do id
    numérico. Leitura liberada pra todo usuário autenticado (inclusive
    clientes — o parâmetro afeta o que eles veem); escrita só equipe do
    escritório.
    """

    queryset = Parametro.objects.all()
    serializer_class = ParametroSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]
    lookup_field = "chave"
