from django.contrib import admin

from .models import Importacao


@admin.register(Importacao)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = [
        "municipio", "tipo_relatorio", "sistema_origem", "status",
        "linhas_importadas", "usuario", "criado_em",
    ]
    list_filter = ["status", "sistema_origem", "tipo_relatorio"]
    search_fields = ["municipio__nome"]
    autocomplete_fields = ["municipio", "exercicio", "usuario"]
    readonly_fields = ["status", "mensagem_erro", "linhas_importadas", "processado_em", "criado_em"]
