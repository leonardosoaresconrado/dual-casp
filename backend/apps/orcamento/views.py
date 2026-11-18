from django.db.models import Sum
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.usuarios.mixins import RegistroManualMixin
from apps.usuarios.permissions import (
    IsEquipeEscritorioOuSomenteLeitura,
    aplicar_filtro_ativo,
    municipios_acessiveis,
    orgaos_acessiveis,
    unidades_gestoras_acessiveis,
)

from .models import (
    LOA,
    Acao,
    CategoriaEconomica,
    ElementoDespesa,
    Empenho,
    Exercicio,
    FonteRecursos,
    Funcao,
    GrupoNaturezaDespesa,
    LancamentoExecucaoOrcamentaria,
    ModalidadeAplicacao,
    Programa,
    RubricaOrcamentaria,
    Subelemento,
    Subfuncao,
)
from .serializers import (
    AcaoSerializer,
    CategoriaEconomicaSerializer,
    ElementoDespesaSerializer,
    EmpenhoSerializer,
    ExercicioSerializer,
    FonteRecursosSerializer,
    FuncaoSerializer,
    GrupoNaturezaDespesaSerializer,
    LOASerializer,
    LancamentoExecucaoOrcamentariaSerializer,
    ModalidadeAplicacaoSerializer,
    ProgramaSerializer,
    RubricaOrcamentariaSerializer,
    SubelementoSerializer,
    SubfuncaoSerializer,
)

RUBRICA_SELECT_RELATED = (
    "unidade_gestora", "orgao", "unidade_orcamentaria",
    "funcao", "subfuncao", "programa", "acao", "loa__exercicio",
    "categoria_economica", "grupo_natureza_despesa", "modalidade_aplicacao",
    "elemento_despesa", "subelemento", "fonte_recursos",
)


class ExercicioViewSet(ModelViewSet):
    serializer_class = ExercicioSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = Exercicio.objects.filter(municipio__in=municipios_acessiveis(self.request.user))
        municipio_id = self.request.query_params.get("municipio")
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)
        return qs


class LOAViewSet(ModelViewSet):
    serializer_class = LOASerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = LOA.objects.filter(
            exercicio__municipio__in=municipios_acessiveis(self.request.user)
        )
        exercicio_id = self.request.query_params.get("exercicio")
        if exercicio_id:
            qs = qs.filter(exercicio_id=exercicio_id)
        return qs


class FuncaoViewSet(ModelViewSet):
    """Catálogo nacional de Funções de governo (Portaria MOG nº 42/1999)."""
    queryset = Funcao.objects.all()
    serializer_class = FuncaoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]


class SubfuncaoViewSet(ModelViewSet):
    """Catálogo nacional de Subfunções de governo."""
    queryset = Subfuncao.objects.all()
    serializer_class = SubfuncaoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]


class ProgramaViewSet(ModelViewSet):
    serializer_class = ProgramaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = Programa.objects.filter(
            loa__exercicio__municipio__in=municipios_acessiveis(self.request.user)
        )
        loa_id = self.request.query_params.get("loa")
        if loa_id:
            qs = qs.filter(loa_id=loa_id)
        return qs


class AcaoViewSet(ModelViewSet):
    serializer_class = AcaoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = Acao.objects.filter(
            programa__loa__exercicio__municipio__in=municipios_acessiveis(self.request.user)
        )
        programa_id = self.request.query_params.get("programa")
        if programa_id:
            qs = qs.filter(programa_id=programa_id)
        loa_id = self.request.query_params.get("loa")
        if loa_id:
            qs = qs.filter(programa__loa_id=loa_id)
        return qs


class CategoriaEconomicaViewSet(ModelViewSet):
    """Catálogo nacional (Lei 4.320/64)."""
    serializer_class = CategoriaEconomicaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        return aplicar_filtro_ativo(self.request, CategoriaEconomica.objects.all())


class GrupoNaturezaDespesaViewSet(ModelViewSet):
    """Catálogo nacional (padrão STN)."""
    serializer_class = GrupoNaturezaDespesaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        return aplicar_filtro_ativo(self.request, GrupoNaturezaDespesa.objects.all())


class ModalidadeAplicacaoViewSet(ModelViewSet):
    """Catálogo nacional (padrão STN)."""
    serializer_class = ModalidadeAplicacaoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        return aplicar_filtro_ativo(self.request, ModalidadeAplicacao.objects.all())


class ElementoDespesaViewSet(ModelViewSet):
    """Catálogo nacional (padrão STN)."""
    serializer_class = ElementoDespesaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        return aplicar_filtro_ativo(self.request, ElementoDespesa.objects.all())


class SubelementoViewSet(ModelViewSet):
    serializer_class = SubelementoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        qs = aplicar_filtro_ativo(self.request, Subelemento.objects.select_related("elemento"))
        elemento_id = self.request.query_params.get("elemento")
        if elemento_id:
            qs = qs.filter(elemento_id=elemento_id)
        return qs


class FonteRecursosViewSet(ModelViewSet):
    """Catálogo nacional (STN), sem escopo de UG/município — ver docstring do model."""
    serializer_class = FonteRecursosSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        return FonteRecursos.objects.all()


class RubricaOrcamentariaViewSet(RegistroManualMixin, ModelViewSet):
    serializer_class = RubricaOrcamentariaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        usuario = self.request.user
        orgaos_ids = list(orgaos_acessiveis(usuario).values_list("id", flat=True))
        qs = RubricaOrcamentaria.objects.filter(
            unidade_gestora__in=unidades_gestoras_acessiveis(usuario),
            orgao_id__in=orgaos_ids,
        ).select_related(*RUBRICA_SELECT_RELATED)

        loa_id = self.request.query_params.get("loa")
        if loa_id:
            qs = qs.filter(loa_id=loa_id)
        ug_id = self.request.query_params.get("unidade_gestora")
        if ug_id:
            qs = qs.filter(unidade_gestora_id=ug_id)
        origem = self.request.query_params.get("origem_dotacao")
        if origem:
            qs = qs.filter(origem_dotacao=origem)
        return qs


AGRUPAMENTO_EXECUCAO = {
    "unidade_gestora": ("rubrica__unidade_gestora_id", "rubrica__unidade_gestora__nome"),
    "orgao": ("rubrica__orgao_id", "rubrica__orgao__nome"),
    "funcao": ("rubrica__funcao_id", "rubrica__funcao__nome"),
    "subfuncao": ("rubrica__subfuncao_id", "rubrica__subfuncao__nome"),
    "programa": ("rubrica__programa_id", "rubrica__programa__nome"),
    "origem_dotacao": ("rubrica__origem_dotacao", "rubrica__origem_dotacao"),
}


class LancamentoExecucaoOrcamentariaViewSet(RegistroManualMixin, ModelViewSet):
    serializer_class = LancamentoExecucaoOrcamentariaSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        usuario = self.request.user
        ugs_ids = list(unidades_gestoras_acessiveis(usuario).values_list("id", flat=True))
        orgaos_ids = list(orgaos_acessiveis(usuario).values_list("id", flat=True))

        qs = LancamentoExecucaoOrcamentaria.objects.select_related(
            *(f"rubrica__{campo}" for campo in RUBRICA_SELECT_RELATED)
        ).filter(
            rubrica__unidade_gestora_id__in=ugs_ids,
            rubrica__orgao_id__in=orgaos_ids,
        )

        loa_id = self.request.query_params.get("loa")
        mes = self.request.query_params.get("mes_referencia")
        ug_id = self.request.query_params.get("unidade_gestora")
        if loa_id:
            qs = qs.filter(rubrica__loa_id=loa_id)
        if mes:
            qs = qs.filter(mes_referencia=mes)
        if ug_id:
            qs = qs.filter(rubrica__unidade_gestora_id=ug_id)
        return qs

    @action(detail=False)
    def resumo(self, request):
        """
        Agrupa/soma no banco em vez do frontend buscar as linhas cruas e
        agrupar com Map() — substitui o agrupar() client-side de
        RelatorioExecucaoPage.tsx. Reaproveita os mesmos filtros de
        get_queryset() (loa/mes_referencia/unidade_gestora) + `agrupar_por`.
        """
        agrupar_por = request.query_params.get("agrupar_por", "unidade_gestora")
        if agrupar_por not in AGRUPAMENTO_EXECUCAO:
            return Response(
                {"detail": f"agrupar_por inválido. Use um de: {', '.join(AGRUPAMENTO_EXECUCAO)}."},
                status=400,
            )
        campo_chave, campo_nome = AGRUPAMENTO_EXECUCAO[agrupar_por]
        qs = self.get_queryset()
        dados = (
            qs.values(campo_chave, campo_nome)
            .annotate(
                dotacao_atualizada=Sum("dotacao_atualizada"),
                empenhado_no_mes=Sum("empenhado_no_mes"),
                empenhado_acumulado=Sum("empenhado_acumulado"),
                liquidado_no_mes=Sum("liquidado_no_mes"),
                liquidado_acumulado=Sum("liquidado_acumulado"),
                pago_no_mes=Sum("pago_no_mes"),
                pago_acumulado=Sum("pago_acumulado"),
            )
            .order_by("-empenhado_acumulado")
        )
        resultado = [
            {
                "chave": row[campo_chave],
                "nome": row[campo_nome],
                "dotacao_atualizada": row["dotacao_atualizada"],
                "empenhado_no_mes": row["empenhado_no_mes"],
                "empenhado_acumulado": row["empenhado_acumulado"],
                "liquidado_no_mes": row["liquidado_no_mes"],
                "liquidado_acumulado": row["liquidado_acumulado"],
                "pago_no_mes": row["pago_no_mes"],
                "pago_acumulado": row["pago_acumulado"],
            }
            for row in dados
        ]
        return Response(resultado)

    @action(detail=False)
    def tendencia(self, request):
        """
        Série mensal agregada (soma de todas as rubricas por mês) — uma
        única query, substitui as N requisições sequenciais (uma por mês)
        que RelatorioExecucaoPage.tsx fazia para montar a linha de
        tendência. `ate_mes` corta a série (senão vem o exercício inteiro).
        """
        qs = self.get_queryset()
        ate_mes = request.query_params.get("ate_mes")
        if ate_mes:
            qs = qs.filter(mes_referencia__lte=ate_mes)
        dados = (
            qs.values("mes_referencia")
            .annotate(
                empenhado_acumulado=Sum("empenhado_acumulado"),
                liquidado_acumulado=Sum("liquidado_acumulado"),
                pago_acumulado=Sum("pago_acumulado"),
            )
            .order_by("mes_referencia")
        )
        return Response(list(dados))


class EmpenhoViewSet(RegistroManualMixin, ModelViewSet):
    serializer_class = EmpenhoSerializer
    permission_classes = [IsEquipeEscritorioOuSomenteLeitura]

    def get_queryset(self):
        usuario = self.request.user
        ugs_ids = list(unidades_gestoras_acessiveis(usuario).values_list("id", flat=True))
        qs = Empenho.objects.filter(unidade_gestora_id__in=ugs_ids).select_related(
            "unidade_gestora"
        ).prefetch_related("movimentos")

        rubrica_id = self.request.query_params.get("rubrica")
        if rubrica_id:
            qs = qs.filter(rubrica_id=rubrica_id)
        ug_id = self.request.query_params.get("unidade_gestora")
        if ug_id:
            qs = qs.filter(unidade_gestora_id=ug_id)
        numero = self.request.query_params.get("numero")
        if numero:
            qs = qs.filter(numero__icontains=numero)
        mes = self.request.query_params.get("mes_referencia")
        if mes:
            qs = qs.filter(movimentos__mes_referencia=mes).distinct()
        return qs
