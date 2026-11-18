from django.contrib import admin

from .models import Municipio, Orgao, UnidadeGestora, UnidadeOrcamentaria


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ["nome", "uf", "codigo_ibge", "ativo"]
    list_filter = ["uf", "ativo"]
    search_fields = ["nome", "codigo_ibge"]


@admin.register(UnidadeGestora)
class UnidadeGestoraAdmin(admin.ModelAdmin):
    list_display = ["nome", "municipio", "poder", "codigo", "ativo"]
    list_filter = ["poder", "ativo", "municipio"]
    search_fields = ["nome", "codigo", "municipio__nome"]
    autocomplete_fields = ["municipio"]


@admin.register(Orgao)
class OrgaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "municipio", "codigo", "ativo"]
    list_filter = ["ativo"]
    search_fields = ["nome", "codigo", "municipio__nome"]
    autocomplete_fields = ["municipio"]


@admin.register(UnidadeOrcamentaria)
class UnidadeOrcamentariaAdmin(admin.ModelAdmin):
    list_display = ["nome", "orgao", "unidade_gestora", "codigo", "ativo"]
    list_filter = ["ativo", "unidade_gestora"]
    search_fields = ["nome", "codigo", "orgao__nome"]
    autocomplete_fields = ["orgao", "unidade_gestora"]
