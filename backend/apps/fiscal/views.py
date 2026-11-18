from django.db.models import Sum
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.usuarios.mixins import RegistroManualMixin
from apps.usuarios.permissions import (
    IsEquipeEscritorioOuSomenteLeitura,
    aplicar_filtro_ativo,
    unidades_gestoras_acessiveis,
)

from .models import (
    ClassificacaoReceitaAlinea,
    ClassificacaoReceitaEspecie,
    ClassificacaoReceitaOrigem,
    ClassificacaoReceitaRubrica,
    ClassificacaoReceitaSubalinea,
    ClassificacaoReceitaTipo,
    LancamentoExecucaoReceita,
    RubricaReceita,
)
from .serializers import (
    ClassificacaoReceitaAlineaSerializer,
    ClassificacaoReceitaEspecieSerializer,
    ClassificacaoReceitaOrigemSerializer,
    ClassificacaoReceitaRubricaSerializer,
    ClassificacaoReceitaSubalineaSerializer,
    ClassificacaoReceitaTipoSerializer,
    LancamentoExecucaoReceitaSerializer,
    RubricaReceitaSerializer,
)


class ClassificacaoReceitaOrigemViewSet(ModelViewSet):
    """Catálogo nacional (Ementário da Receita, STN) — nível 2."""
    serializer_class = ClassificacaoReceitaOrigemSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = aplicar_filtro_ativo(self.request, ClassificacaoReceitaOrigem.objects.select_related("categoria"))
        categoria_id = self.request.query_params.get("categoria")
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        return qs


class ClassificacaoReceitaEspecieViewSet(ModelViewSet):
    """Catálogo nacional (Ementário da Receita, STN) — nível 3."""
    serializer_class = ClassificacaoReceitaEspecieSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = aplicar_filtro_ativo(self.request, ClassificacaoReceitaEspecie.objects.select_related("origem"))
        origem_id = self.request.query_params.get("origem")
        if origem_id:
            qs = qs.filter(origem_id=origem_id)
        return qs


class ClassificacaoReceitaRubricaViewSet(ModelViewSet):
    """Catálogo nacional (Ementário da Receita, STN) — nível 4 ("Rubrica" oficial, não confundir com RubricaReceita)."""
    serializer_class = ClassificacaoReceitaRubricaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = aplicar_filtro_ativo(self.request, ClassificacaoReceitaRubrica.objects.select_related("especie"))
        especie_id = self.request.query_params.get("especie")
        if especie_id:
            qs = qs.filter(especie_id=especie_id)
        return qs


class ClassificacaoReceitaAlineaViewSet(ModelViewSet):
    """Catálogo nacional (Ementário da Receita, STN) — nível 5."""
    serializer_class = ClassificacaoReceitaAlineaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = aplicar_filtro_ativo(self.request, ClassificacaoReceitaAlinea.objects.select_related("rubrica"))
        rubrica_id = self.request.query_params.get("rubrica")
        if rubrica_id:
            qs = qs.filter(rubrica_id=rubrica_id)
        return qs


class ClassificacaoReceitaSubalineaViewSet(ModelViewSet):
    """Catálogo nacional (Ementário da Receita, STN) — nível 6."""
    serializer_class = ClassificacaoReceitaSubalineaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = aplicar_filtro_ativo(self.request, ClassificacaoReceitaSubalinea.objects.select_related("alinea"))
        alinea_id = self.request.query_params.get("alinea")
        if alinea_id:
            qs = qs.filter(alinea_id=alinea_id)
        return qs


class ClassificacaoReceitaTipoViewSet(ModelViewSet):
    """Catálogo nacional (Ementário da Receita, STN) — nível 7 (folha)."""
    serializer_class = ClassificacaoReceitaTipoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = aplicar_filtro_ativo(self.request, ClassificacaoReceitaTipo.objects.select_related("subalinea"))
        subalinea_id = self.request.query_params.get("subalinea")
        if subalinea_id:
            qs = qs.filter(subalinea_id=subalinea_id)
        return qs


class RubricaReceitaViewSet(RegistroManualMixin, ModelViewSet):
    serializer_class = RubricaReceitaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        usuario = self.request.user
        qs = RubricaReceita.objects.filter(
            unidade_gestora__in=unidades_gestoras_acessiveis(usuario)
        ).select_related("unidade_gestora", "fonte_recursos")

        loa_id = self.request.query_params.get("loa")
        if loa_id:
            qs = qs.filter(loa_id=loa_id)
        ug_id = self.request.query_params.get("unidade_gestora")
        if ug_id:
            qs = qs.filter(unidade_gestora_id=ug_id)
        return qs


class LancamentoExecucaoReceitaViewSet(RegistroManualMixin, ModelViewSet):
    serializer_class = LancamentoExecucaoReceitaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        usuario = self.request.user
        qs = LancamentoExecucaoReceita.objects.filter(
            rubrica__unidade_gestora__in=unidades_gestoras_acessiveis(usuario)
        ).select_related("rubrica__unidade_gestora", "rubrica__fonte_recursos")

        loa_id = self.request.query_params.get("loa")
        if loa_id:
            qs = qs.filter(rubrica__loa_id=loa_id)
        mes = self.request.query_params.get("mes_referencia")
        if mes:
            qs = qs.filter(mes_referencia=mes)
        mes_ate = self.request.query_params.get("mes_referencia_ate")
        if mes_ate:
            qs = qs.filter(mes_referencia__lte=mes_ate)
        return qs

    @action(detail=False)
    def resumo(self, request):
        """
        Agrupa/soma por código de rubrica no banco — substitui o agrupar()
        client-side do lado "realizado" de ReceitaPage.tsx.
        """
        qs = self.get_queryset()
        dados = (
            qs.values("rubrica__codigo", "rubrica__nome")
            .annotate(
                valor_bruto_no_mes=Sum("valor_bruto_no_mes"),
                deducao_no_mes=Sum("deducao_no_mes"),
                anulacao_no_mes=Sum("anulacao_no_mes"),
                valor_liquido_no_mes=Sum("valor_liquido_no_mes"),
            )
            .order_by("-valor_liquido_no_mes")
        )
        resultado = [
            {
                "codigo": row["rubrica__codigo"],
                "nome": row["rubrica__nome"],
                "valor_bruto_no_mes": row["valor_bruto_no_mes"],
                "deducao_no_mes": row["deducao_no_mes"],
                "anulacao_no_mes": row["anulacao_no_mes"],
                "valor_liquido_no_mes": row["valor_liquido_no_mes"],
            }
            for row in dados
        ]
        return Response(resultado)
