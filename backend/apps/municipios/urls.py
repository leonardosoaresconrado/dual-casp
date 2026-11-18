from rest_framework.routers import DefaultRouter

from .views import MunicipioViewSet, OrgaoViewSet, UnidadeGestoraViewSet, UnidadeOrcamentariaViewSet

router = DefaultRouter()
router.register("municipios", MunicipioViewSet, basename="municipio")
router.register("unidades-gestoras", UnidadeGestoraViewSet, basename="unidade-gestora")
router.register("orgaos", OrgaoViewSet, basename="orgao")
router.register("unidades-orcamentarias", UnidadeOrcamentariaViewSet, basename="unidade-orcamentaria")

urlpatterns = router.urls
