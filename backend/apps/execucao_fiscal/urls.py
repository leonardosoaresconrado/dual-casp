from rest_framework.routers import DefaultRouter

from .views import (
    ApuracaoASPSViewSet,
    ApuracaoDTPViewSet,
    ApuracaoETIFundebViewSet,
    ApuracaoMagisterioFundebViewSet,
    ApuracaoMDEViewSet,
    ApuracaoReprogramacaoFundebViewSet,
    ApuracaoVAATDespesaCapitalViewSet,
    ApuracaoVAATEducacaoInfantilViewSet,
    ApuracaoValorNaoAplicadoFundebViewSet,
)

router = DefaultRouter()
router.register("apuracao-dtp", ApuracaoDTPViewSet, basename="apuracao-dtp")
router.register("apuracao-mde", ApuracaoMDEViewSet, basename="apuracao-mde")
router.register("apuracao-magisterio-fundeb", ApuracaoMagisterioFundebViewSet, basename="apuracao-magisterio-fundeb")
router.register("apuracao-fundeb-eti", ApuracaoETIFundebViewSet, basename="apuracao-fundeb-eti")
router.register("apuracao-asps", ApuracaoASPSViewSet, basename="apuracao-asps")
router.register(
    "apuracao-vaat-educacao-infantil", ApuracaoVAATEducacaoInfantilViewSet, basename="apuracao-vaat-educacao-infantil"
)
router.register("apuracao-vaat-despesa-capital", ApuracaoVAATDespesaCapitalViewSet, basename="apuracao-vaat-despesa-capital")
router.register(
    "apuracao-fundeb-nao-aplicado", ApuracaoValorNaoAplicadoFundebViewSet, basename="apuracao-fundeb-nao-aplicado"
)
router.register(
    "apuracao-fundeb-reprogramacao", ApuracaoReprogramacaoFundebViewSet, basename="apuracao-fundeb-reprogramacao"
)

urlpatterns = router.urls
