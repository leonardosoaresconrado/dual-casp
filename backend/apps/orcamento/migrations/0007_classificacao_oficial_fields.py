import django.utils.timezone
from django.db import migrations, models


def add_classificacao_fields(model_name):
    return [
        migrations.AddField(
            model_name=model_name,
            name="ativo",
            field=models.BooleanField(default=True, verbose_name="Ativo"),
        ),
        migrations.AddField(
            model_name=model_name,
            name="origem",
            field=models.CharField(
                choices=[("OFICIAL", "Oficial (STN/SOF)"), ("MUNICIPAL", "Municipal")],
                default="OFICIAL",
                max_length=10,
                verbose_name="Origem da classificação",
            ),
        ),
        migrations.AddField(
            model_name=model_name,
            name="ano_vigencia_inicial",
            field=models.PositiveSmallIntegerField(
                blank=True, null=True, verbose_name="Vigente desde (ano)"
            ),
        ),
        migrations.AddField(
            model_name=model_name,
            name="criado_em",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name=model_name,
            name="atualizado_em",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]


class Migration(migrations.Migration):

    dependencies = [
        ("orcamento", "0006_alter_rubricaorcamentaria_origem_dotacao"),
    ]

    operations = [
        *add_classificacao_fields("categoriaeconomica"),
        *add_classificacao_fields("gruponaturezadespesa"),
        *add_classificacao_fields("modalidadeaplicacao"),
        *add_classificacao_fields("elementodespesa"),
        *add_classificacao_fields("subelemento"),
    ]
