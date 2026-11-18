from django.contrib import admin

from .models import (
    LOA,
    Acao,
    CategoriaEconomica,
    ElementoDespesa,
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


@admin.register(Exercicio)
class ExercicioAdmin(admin.ModelAdmin):
    list_display = ["municipio", "ano", "status"]
    list_filter = ["status", "ano"]
    search_fields = ["municipio__nome"]
    autocomplete_fields = ["municipio"]


@admin.register(LOA)
class LOAAdmin(admin.ModelAdmin):
    list_display = ["exercicio", "numero_lei", "valor_total_despesa_fixada"]
    search_fields = ["numero_lei", "exercicio__municipio__nome"]
    autocomplete_fields = ["exercicio"]


@admin.register(Funcao)
class FuncaoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome"]
    search_fields = ["codigo", "nome"]


@admin.register(Subfuncao)
class SubfuncaoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome"]
    search_fields = ["codigo", "nome"]


@admin.register(CategoriaEconomica)
class CategoriaEconomicaAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome"]
    search_fields = ["codigo", "nome"]


@admin.register(GrupoNaturezaDespesa)
class GrupoNaturezaDespesaAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome"]
    search_fields = ["codigo", "nome"]


@admin.register(ModalidadeAplicacao)
class ModalidadeAplicacaoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome"]
    search_fields = ["codigo", "nome"]


@admin.register(ElementoDespesa)
class ElementoDespesaAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome"]
    search_fields = ["codigo", "nome"]


@admin.register(Subelemento)
class SubelementoAdmin(admin.ModelAdmin):
    list_display = ["elemento", "codigo", "nome"]
    search_fields = ["codigo", "nome", "elemento__codigo"]
    autocomplete_fields = ["elemento"]


@admin.register(FonteRecursos)
class FonteRecursosAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome", "tipo", "natureza_label"]
    search_fields = ["codigo", "nome"]


@admin.register(Programa)
class ProgramaAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome", "loa"]
    search_fields = ["codigo", "nome"]
    autocomplete_fields = ["loa"]


@admin.register(Acao)
class AcaoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome", "tipo", "programa"]
    list_filter = ["tipo"]
    search_fields = ["codigo", "nome"]
    autocomplete_fields = ["programa"]


@admin.register(RubricaOrcamentaria)
class RubricaOrcamentariaAdmin(admin.ModelAdmin):
    list_display = [
        "loa", "unidade_gestora", "orgao", "funcao", "subfuncao",
        "programa", "acao", "elemento_despesa", "dotacao_inicial",
    ]
    list_filter = ["unidade_gestora", "categoria_economica"]
    search_fields = ["acao__nome", "elemento_despesa__nome", "orgao__nome"]
    autocomplete_fields = [
        "loa", "unidade_gestora", "orgao", "unidade_orcamentaria", "funcao", "subfuncao",
        "programa", "acao", "categoria_economica", "grupo_natureza_despesa",
        "modalidade_aplicacao", "elemento_despesa", "subelemento", "fonte_recursos",
    ]


@admin.register(LancamentoExecucaoOrcamentaria)
class LancamentoExecucaoOrcamentariaAdmin(admin.ModelAdmin):
    list_display = [
        "rubrica", "mes_referencia", "dotacao_atualizada",
        "empenhado_acumulado", "liquidado_acumulado", "pago_acumulado",
    ]
    list_filter = ["mes_referencia"]
    autocomplete_fields = ["rubrica", "importacao"]
