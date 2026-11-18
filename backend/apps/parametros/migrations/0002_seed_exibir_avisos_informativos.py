from django.db import migrations


def seed(apps, schema_editor):
    Parametro = apps.get_model("parametros", "Parametro")
    Parametro.objects.get_or_create(
        chave="exibir_avisos_informativos",
        defaults={
            "descricao": "Exibir os avisos informativos (azuis) nas páginas do sistema",
            "valor_booleano": True,
        },
    )


def remover(apps, schema_editor):
    Parametro = apps.get_model("parametros", "Parametro")
    Parametro.objects.filter(chave="exibir_avisos_informativos").delete()


class Migration(migrations.Migration):
    dependencies = [("parametros", "0001_initial")]
    operations = [migrations.RunPython(seed, remover)]
