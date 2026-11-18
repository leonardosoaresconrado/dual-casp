from django.db import migrations
from django.db.migrations.exceptions import IrreversibleError


def mesclar_fontes_duplicadas(apps, schema_editor):
    """
    `FonteRecursos` tinha `unidade_gestora` como parte da chave, criando
    uma linha duplicada por UG para o mesmo código/nome real (confirmado:
    89 códigos distintos espalhados em 138 linhas, zero divergência de
    nome entre as duplicatas de cada código — ver nota no model). Antes de
    remover a coluna `unidade_gestora` (próxima migration) e tornar
    `codigo` globalmente único, é preciso mesclar cada grupo de
    duplicatas: escolhe uma linha canônica (a de menor id; se alguma
    duplicata tiver `tipo` preenchido e a canônica não, usa essa), repõe
    todo FK que apontava para as outras linhas do grupo, e só então apaga
    as duplicatas — sem isso, o `UniqueConstraint` em `codigo` sozinho
    falharia na migration seguinte, e um `on_delete=PROTECT` ingênuo
    bloquearia a exclusão das duplicatas ainda referenciadas.
    """
    FonteRecursos = apps.get_model("orcamento", "FonteRecursos")
    RubricaOrcamentaria = apps.get_model("orcamento", "RubricaOrcamentaria")
    RubricaReceita = apps.get_model("fiscal", "RubricaReceita")
    SaldoBalancoContaFonte = apps.get_model("financeiro", "SaldoBalancoContaFonte")
    SaldoContaBancariaFonte = apps.get_model("financeiro", "SaldoContaBancariaFonte")
    RestoAPagar = apps.get_model("financeiro", "RestoAPagar")

    grupos: dict[str, list] = {}
    for fonte in FonteRecursos.objects.all().order_by("id"):
        grupos.setdefault(fonte.codigo, []).append(fonte)

    for codigo, fontes in grupos.items():
        if len(fontes) <= 1:
            continue

        canonica = fontes[0]
        for candidata in fontes[1:]:
            if not canonica.tipo and candidata.tipo:
                canonica = candidata
                break

        duplicatas_ids = [f.id for f in fontes if f.id != canonica.id]

        RubricaOrcamentaria.objects.filter(fonte_recursos_id__in=duplicatas_ids).update(
            fonte_recursos_id=canonica.id
        )
        RubricaReceita.objects.filter(fonte_recursos_id__in=duplicatas_ids).update(fonte_recursos_id=canonica.id)
        SaldoBalancoContaFonte.objects.filter(fonte_recursos_id__in=duplicatas_ids).update(
            fonte_recursos_id=canonica.id
        )
        SaldoContaBancariaFonte.objects.filter(fonte_recursos_id__in=duplicatas_ids).update(
            fonte_recursos_id=canonica.id
        )
        RestoAPagar.objects.filter(fonte_recursos_id__in=duplicatas_ids).update(fonte_recursos_id=canonica.id)

        FonteRecursos.objects.filter(id__in=duplicatas_ids).delete()


def reverter_noop(apps, schema_editor):
    # Irreversível de verdade (a informação de "qual UG tinha qual linha"
    # já foi perdida) — não há como desfazer com segurança.
    raise IrreversibleError("Mesclagem de FonteRecursos duplicadas não pode ser revertida.")


class Migration(migrations.Migration):

    dependencies = [
        ("orcamento", "0011_lancamentoexecucaoorcamentaria_atualizado_em_and_more"),
        ("fiscal", "0008_remove_arrecadacao_fiscal_arre_municip_39159e_idx_and_more"),
        ("financeiro", "0006_restoapagar_atualizado_em_and_more"),
    ]

    operations = [
        migrations.RunPython(mesclar_fontes_duplicadas, reverter_noop),
    ]
