from rest_framework.routers import DefaultRouter

from .views import (
    ClassificacaoReceitaAlineaViewSet,
    ClassificacaoReceitaEspecieViewSet,
    ClassificacaoReceitaOrigemViewSet,
    ClassificacaoReceitaRubricaViewSet,
    ClassificacaoReceitaSubalineaViewSet,
    ClassificacaoReceitaTipoViewSet,
    LancamentoExecucaoReceitaViewSet,
    RubricaReceitaViewSet,
)

router = DefaultRouter()
router.register("rubricas-receita", RubricaReceitaViewSet, basename="rubrica-receita")
router.register("execucao-receita", LancamentoExecucaoReceitaViewSet, basename="execucao-receita")
router.register(
    "classificacao-receita-origens", ClassificacaoReceitaOrigemViewSet, basename="classificacao-receita-origem"
)
router.register(
    "classificacao-receita-especies", ClassificacaoReceitaEspecieViewSet, basename="classificacao-receita-especie"
)
router.register(
    "classificacao-receita-rubricas", ClassificacaoReceitaRubricaViewSet, basename="classificacao-receita-rubrica"
)
router.register(
    "classificacao-receita-alineas", ClassificacaoReceitaAlineaViewSet, basename="classificacao-receita-alinea"
)
router.register(
    "classificacao-receita-subalineas", ClassificacaoReceitaSubalineaViewSet, basename="classificacao-receita-subalinea"
)
router.register(
    "classificacao-receita-tipos", ClassificacaoReceitaTipoViewSet, basename="classificacao-receita-tipo"
)

urlpatterns = router.urls
