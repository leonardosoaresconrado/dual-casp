from django.db import migrations

# Confirmado pelo usuário e verificado contra o calendário real de 2026
# (12/12 meses, zero exceção): o vencimento de Arquivo Contábil/Arquivo de
# Folha de Pagamento/Matriz de Saldos Contábeis é o último dia do mês
# subsequente à competência (prazo_meses_apos_periodo=1,
# prazo_dia_limite=31 — já clampado pelo próprio `calcular_prazo_limite`
# pro último dia real do mês), ajustado para a segunda-feira seguinte
# quando cai em sábado/domingo. Isso torna o gerador por fórmula
# (`gerar_obrigacoes_pendentes`) preciso para estes 3 tipos a partir de
# agora, útil como reserva para competências futuras ainda não coladas via
# `importar_calendario_obrigacoes`.

TIPOS_MENSAIS_DIA_UTIL = [
    "Arquivo Contábil",
    "Arquivo de Folha de Pagamento",
    "Matriz de Saldos Contábeis",
]


def aplicar(apps, schema_editor):
    TipoObrigacao = apps.get_model("obrigacoes", "TipoObrigacao")
    TipoObrigacao.objects.filter(nome__in=TIPOS_MENSAIS_DIA_UTIL).update(
        prazo_meses_apos_periodo=1,
        prazo_dia_limite=31,
        ajustar_prazo_para_dia_util=True,
    )


def reverter(apps, schema_editor):
    TipoObrigacao = apps.get_model("obrigacoes", "TipoObrigacao")
    TipoObrigacao.objects.filter(nome__in=TIPOS_MENSAIS_DIA_UTIL).update(
        prazo_meses_apos_periodo=None,
        prazo_dia_limite=None,
        ajustar_prazo_para_dia_util=False,
    )


class Migration(migrations.Migration):
    dependencies = [("obrigacoes", "0006_tipoobrigacao_ajustar_prazo_para_dia_util")]
    operations = [migrations.RunPython(aplicar, reverter)]
