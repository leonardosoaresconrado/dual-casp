from rest_framework.routers import DefaultRouter

from .views import RestoAPagarViewSet, SaldoBalancoContaViewSet, SaldoContaBancariaViewSet

router = DefaultRouter()
router.register("saldo-balanco", SaldoBalancoContaViewSet, basename="saldo-balanco")
router.register("saldo-conta-bancaria", SaldoContaBancariaViewSet, basename="saldo-conta-bancaria")
router.register("restos-a-pagar", RestoAPagarViewSet, basename="resto-a-pagar")

urlpatterns = router.urls
