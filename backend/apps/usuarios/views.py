from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Usuario, VinculoAcesso
from .permissions import IsEquipeEscritorio
from .serializers import UsuarioSerializer, VinculoAcessoSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class UsuarioViewSet(ModelViewSet):
    """
    Gestão de usuários — restrita à equipe do escritório (ver
    IsEquipeEscritorio): um usuário de cliente não deve listar nome/CPF de
    outros usuários do sistema.
    """
    queryset = Usuario.objects.all().prefetch_related("vinculos_acesso")
    serializer_class = UsuarioSerializer
    permission_classes = [IsEquipeEscritorio]


class VinculoAcessoViewSet(ModelViewSet):
    """Concede/revoga acesso de um usuário a um escopo de município — só a equipe do escritório mexe aqui."""
    serializer_class = VinculoAcessoSerializer
    permission_classes = [IsEquipeEscritorio]

    def get_queryset(self):
        qs = VinculoAcesso.objects.select_related("usuario", "municipio", "unidade_gestora", "orgao")
        usuario_id = self.request.query_params.get("usuario")
        if usuario_id:
            qs = qs.filter(usuario_id=usuario_id)
        municipio_id = self.request.query_params.get("municipio")
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)
        return qs
