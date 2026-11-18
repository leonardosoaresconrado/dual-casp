from django.contrib import admin

from .models import Parametro


@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ["chave", "descricao", "valor_booleano"]
    list_editable = ["valor_booleano"]
