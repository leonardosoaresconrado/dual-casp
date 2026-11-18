from django.contrib import admin

from .models import Obrigacao, TipoObrigacao


@admin.register(TipoObrigacao)
class TipoObrigacaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "escopo", "periodicidade", "ativo", "ordem"]
    list_filter = ["escopo", "periodicidade", "ativo"]
    search_fields = ["nome"]
    filter_horizontal = ["unidades_gestoras_restritas"]


@admin.register(Obrigacao)
class ObrigacaoAdmin(admin.ModelAdmin):
    list_display = ["tipo_obrigacao", "municipio", "unidade_gestora", "rotulo_competencia", "prazo_limite", "status"]
    list_filter = ["status", "tipo_obrigacao"]
    autocomplete_fields = ["tipo_obrigacao", "municipio", "unidade_gestora"]
