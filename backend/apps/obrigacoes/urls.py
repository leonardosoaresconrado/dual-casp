from rest_framework.routers import DefaultRouter

from .views import ObrigacaoViewSet, TipoObrigacaoViewSet

router = DefaultRouter()
router.register("tipos-obrigacao", TipoObrigacaoViewSet, basename="tipos-obrigacao")
router.register("obrigacoes", ObrigacaoViewSet, basename="obrigacoes")

urlpatterns = router.urls
