# -*- coding: utf-8 -*-
"""
Script de introspecção one-off: varre todos os models Django dos apps do
projeto (exclui apps do Django/terceiros) e gera um Markdown estruturado
com toda a modelagem de dados atual (campos, tipos, relações, mixins
abstratos, properties/campos computados, constraints) para análise de
granularidade e otimização da arquitetura.

Rodar como script standalone (não via `manage.py shell <`, que quebra em
funções multi-linha por causa do buffering do REPL):

    cd D:\\DUAL_CASP\\backend
    source venv/Scripts/activate
    python /caminho/para/exportar_modelagem.py
"""
import inspect
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps as django_apps  # noqa: E402
from django.db import models  # noqa: E402
from django.db.models.fields.reverse_related import ForeignObjectRel  # noqa: E402
import django.db.models.fields as _f  # noqa: E402

PROJECT_APPS = [
    "usuarios",
    "municipios",
    "orcamento",
    "fiscal",
    "financeiro",
    "execucao_fiscal",
    "importacao",
]

TIPO_LEGIVEL = {
    "AutoField": "ID (auto)",
    "BigAutoField": "ID (auto, big)",
    "CharField": "Texto curto",
    "TextField": "Texto longo",
    "DecimalField": "Decimal",
    "IntegerField": "Inteiro",
    "PositiveIntegerField": "Inteiro positivo",
    "PositiveSmallIntegerField": "Inteiro positivo (small)",
    "BooleanField": "Booleano",
    "DateField": "Data",
    "DateTimeField": "Data/Hora",
    "ForeignKey": "FK",
    "OneToOneField": "FK (1:1)",
    "FileField": "Arquivo",
    "EmailField": "Email",
}


def nome_tipo(field):
    cls = field.get_internal_type()
    return TIPO_LEGIVEL.get(cls, cls)


def linha_campo(field):
    partes = [f"`{field.name}`", nome_tipo(field)]
    extras = []
    if field.get_internal_type() == "DecimalField":
        extras.append(f"max_digits={field.max_digits}, decimal_places={field.decimal_places}")
    if field.get_internal_type() in ("CharField", "TextField") and getattr(field, "max_length", None):
        extras.append(f"max_length={field.max_length}")
    if getattr(field, "choices", None):
        valores = [c[0] for c in field.choices]
        extras.append(f"choices={valores}")
    if field.is_relation:
        destino = field.related_model
        destino_nome = f"{destino._meta.app_label}.{destino.__name__}" if destino else "?"
        on_delete = getattr(field.remote_field, "on_delete", None)
        on_delete_nome = getattr(on_delete, "__name__", str(on_delete))
        extras.append(f"-> {destino_nome} (on_delete={on_delete_nome})")
    if field.null:
        extras.append("null")
    if field.blank:
        extras.append("blank")
    default = getattr(field, "default", None)
    if default is not _f.NOT_PROVIDED and default is not None and not field.is_relation:
        extras.append(f"default={default!r}")
    if getattr(field, "verbose_name", None) and str(field.verbose_name) != field.name.replace("_", " "):
        extras.append(f'rotulo="{field.verbose_name}"')
    linha = " | ".join(partes)
    if extras:
        linha += " — " + "; ".join(extras)
    return linha


def mixins_abstratos(model):
    nomes = []
    for base in model.__mro__[1:]:
        if getattr(base, "_meta", None) is not None and getattr(base._meta, "abstract", False):
            if base is not models.Model:
                nomes.append(f"{base.__module__}.{base.__name__}")
    return nomes


def properties_computadas(model):
    resultado = []
    campo_nomes = {f.name for f in model._meta.get_fields()}
    for nome, membro in inspect.getmembers(model, lambda x: isinstance(x, property)):
        if nome.startswith("_") or nome in campo_nomes:
            continue
        modulo_getter = getattr(membro.fget, "__module__", "") or ""
        if not modulo_getter.startswith("apps."):
            continue  # exclui properties herdadas do Django/contrib (pk, is_authenticated etc.)
        doc = (membro.fget.__doc__ or "").strip().split("\n")[0]
        resultado.append((nome, doc))
    return resultado


def constraints_e_indexes(model):
    linhas = []
    meta = model._meta
    if meta.unique_together:
        linhas.append(f"unique_together: {list(meta.unique_together)}")
    for c in meta.constraints:
        tipo = type(c).__name__
        campos = getattr(c, "fields", None)
        linhas.append(f"constraint ({tipo}): name={c.name}" + (f", fields={campos}" if campos else ""))
    for idx in meta.indexes:
        linhas.append(f"index: fields={idx.fields}" + (f", name={idx.name}" if idx.name else ""))
    if meta.ordering:
        linhas.append(f"ordering: {list(meta.ordering)}")
    return linhas


def main():
    linhas_saida = []
    linhas_saida.append("# Modelagem de Dados — DUAL_CASP (export automático)\n")
    linhas_saida.append(
        "Gerado por introspecção direta dos models Django (`apps/*/models.py`) — "
        "reflete o schema real aplicado no banco, não uma transcrição manual.\n"
    )

    for app_label in PROJECT_APPS:
        try:
            app_config = django_apps.get_app_config(app_label)
        except LookupError:
            continue
        modelos = list(app_config.get_models())
        if not modelos:
            continue
        linhas_saida.append(f"\n## App `{app_label}`\n")
        for model in modelos:
            meta = model._meta
            linhas_saida.append(f"### `{app_label}.{model.__name__}`")
            if model.__doc__ and not model.__doc__.strip().startswith(f"{model.__name__}("):
                doc = model.__doc__.strip()
                linhas_saida.append(f"\n> {doc}\n")
            mixins = mixins_abstratos(model)
            if mixins:
                linhas_saida.append(f"**Mixins abstratos:** {', '.join(mixins)}\n")
            linhas_saida.append("**Campos:**")
            for f in meta.get_fields():
                if isinstance(f, ForeignObjectRel) or not hasattr(f, "get_internal_type"):
                    continue  # reverse relations (acessadas via related_name), não são campos reais da tabela
                try:
                    linhas_saida.append(f"- {linha_campo(f)}")
                except Exception as e:
                    linhas_saida.append(f"- `{f.name}` (erro ao introspeccionar: {e})")
            props = properties_computadas(model)
            if props:
                linhas_saida.append("\n**Campos computados (`@property`, não são colunas reais):**")
                for nome, doc in props:
                    linhas_saida.append(f"- `{nome}`" + (f" — {doc}" if doc else ""))
            extras = constraints_e_indexes(model)
            if extras:
                linhas_saida.append("\n**Constraints/índices/ordenação:**")
                for e in extras:
                    linhas_saida.append(f"- {e}")
            linhas_saida.append("")

    saida = "\n".join(linhas_saida)
    destino = os.path.join(os.path.dirname(os.getcwd()), "MODELAGEM_DADOS.md")
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(saida)

    print(f"Gravado em {destino}: {len(saida)} caracteres, {len(linhas_saida)} linhas.")


if __name__ == "__main__":
    main()
