from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MeView, UsuarioViewSet, VinculoAcessoViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("vinculos-acesso", VinculoAcessoViewSet, basename="vinculo-acesso")

urlpatterns = [
    path("me/", MeView.as_view(), name="usuario_me"),
    *router.urls,
]
