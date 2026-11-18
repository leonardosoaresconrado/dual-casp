from rest_framework.routers import DefaultRouter

from .views import (
    AcaoViewSet,
    CategoriaEconomicaViewSet,
    ElementoDespesaViewSet,
    EmpenhoViewSet,
    ExercicioViewSet,
    FonteRecursosViewSet,
    FuncaoViewSet,
    GrupoNaturezaDespesaViewSet,
    LOAViewSet,
    LancamentoExecucaoOrcamentariaViewSet,
    ModalidadeAplicacaoViewSet,
    ProgramaViewSet,
    RubricaOrcamentariaViewSet,
    SubelementoViewSet,
    SubfuncaoViewSet,
)

router = DefaultRouter()
router.register("exercicios", ExercicioViewSet, basename="exercicio")
router.register("loas", LOAViewSet, basename="loa")
router.register("funcoes", FuncaoViewSet, basename="funcao")
router.register("subfuncoes", SubfuncaoViewSet, basename="subfuncao")
router.register("programas", ProgramaViewSet, basename="programa")
router.register("acoes", AcaoViewSet, basename="acao")
router.register("categorias-economicas", CategoriaEconomicaViewSet, basename="categoria-economica")
router.register("grupos-natureza-despesa", GrupoNaturezaDespesaViewSet, basename="grupo-natureza-despesa")
router.register("modalidades-aplicacao", ModalidadeAplicacaoViewSet, basename="modalidade-aplicacao")
router.register("elementos-despesa", ElementoDespesaViewSet, basename="elemento-despesa")
router.register("subelementos", SubelementoViewSet, basename="subelemento")
router.register("fontes-recursos", FonteRecursosViewSet, basename="fonte-recursos")
router.register("rubricas-orcamentarias", RubricaOrcamentariaViewSet, basename="rubrica-orcamentaria")
router.register(
    "execucao-orcamentaria", LancamentoExecucaoOrcamentariaViewSet, basename="execucao-orcamentaria"
)
router.register("empenhos", EmpenhoViewSet, basename="empenho")

urlpatterns = router.urls
