from rest_framework.routers import DefaultRouter

from .views import ImportacaoViewSet

router = DefaultRouter()
router.register("importacoes", ImportacaoViewSet, basename="importacao")

urlpatterns = router.urls
