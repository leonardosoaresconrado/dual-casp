from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario, VinculoAcesso


class VinculoAcessoInline(admin.TabularInline):
    model = VinculoAcesso
    extra = 1
    autocomplete_fields = ["municipio", "unidade_gestora", "orgao"]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    ordering = ["nome_completo"]
    list_display = ["cpf", "nome_completo", "email", "is_equipe_escritorio", "is_active", "is_staff"]
    search_fields = ["cpf", "nome_completo", "email"]
    inlines = [VinculoAcessoInline]
    fieldsets = (
        (None, {"fields": ("cpf", "password")}),
        ("Dados pessoais", {"fields": ("nome_completo", "email", "telefone")}),
        (
            "Permissões",
            {
                "fields": (
                    "is_equipe_escritorio",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "fields": ("cpf", "nome_completo", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ["date_joined"]


@admin.register(VinculoAcesso)
class VinculoAcessoAdmin(admin.ModelAdmin):
    list_display = ["usuario", "municipio", "unidade_gestora", "orgao", "papel"]
    list_filter = ["papel", "municipio"]
    autocomplete_fields = ["usuario", "municipio", "unidade_gestora", "orgao"]
    search_fields = ["usuario__nome_completo", "usuario__cpf", "municipio__nome"]
