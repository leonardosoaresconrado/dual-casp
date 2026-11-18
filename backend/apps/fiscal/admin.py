from django.contrib import admin

from .models import RubricaReceita


@admin.register(RubricaReceita)
class RubricaReceitaAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nome", "unidade_gestora", "fonte_recursos", "valor_orcado"]
    list_filter = ["unidade_gestora"]
    search_fields = ["codigo", "nome"]
    autocomplete_fields = ["loa", "unidade_gestora", "fonte_recursos"]
