from rest_framework.routers import DefaultRouter

from .views import ParametroViewSet

router = DefaultRouter()
router.register("parametros", ParametroViewSet, basename="parametro")

urlpatterns = router.urls
