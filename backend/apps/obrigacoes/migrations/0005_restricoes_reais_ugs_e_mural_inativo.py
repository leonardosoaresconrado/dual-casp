from django.db import migrations

# Correção do usuário, 2026-11-16: nem todo Tipo de escopo UNIDADE_GESTORA é
# responsabilidade de toda UG — RREO/Balanço Geral/Matriz de Saldos
# Contábeis/as duas Consolidações/LDO só são submetidos pela Prefeitura
# (PMNP); RGF é submetido por Prefeitura + Câmara (PMNP+CMNP), já que a LRF
# exige RGF de cada Poder, não dos Fundos. Mural de Licitações não deve ser
# acompanhado neste módulo por enquanto — inativado, não excluído (reversível,
# sem perder o cadastro caso volte a ser necessário).

SO_PMNP = [
    "RREO",
    "Balanço Geral",
    "Matriz de Saldos Contábeis",
    "Arquivo Contábil - Consolidação de Saldos",
    "Matriz de Saldos Contábeis - Consolidação de Saldos",
    "LDO",
]
PMNP_E_CMNP = ["RGF"]
NOME_PMNP = "Prefeitura Municipal de Novo Progresso"
NOME_CMNP = "Câmara Municipal de Novo Progresso"
NOME_MURAL = "Mural de Licitações"


def aplicar(apps, schema_editor):
    TipoObrigacao = apps.get_model("obrigacoes", "TipoObrigacao")
    UnidadeGestora = apps.get_model("municipios", "UnidadeGestora")

    pmnp = UnidadeGestora.objects.filter(nome=NOME_PMNP).first()
    cmnp = UnidadeGestora.objects.filter(nome=NOME_CMNP).first()
    if not pmnp:
        return

    for nome in SO_PMNP:
        tipo = TipoObrigacao.objects.filter(nome=nome).first()
        if tipo:
            tipo.unidades_gestoras_restritas.set([pmnp])

    if cmnp:
        for nome in PMNP_E_CMNP:
            tipo = TipoObrigacao.objects.filter(nome=nome).first()
            if tipo:
                tipo.unidades_gestoras_restritas.set([pmnp, cmnp])

    mural = TipoObrigacao.objects.filter(nome=NOME_MURAL).first()
    if mural:
        mural.ativo = False
        mural.save()


def reverter(apps, schema_editor):
    TipoObrigacao = apps.get_model("obrigacoes", "TipoObrigacao")

    for nome in SO_PMNP + PMNP_E_CMNP:
        tipo = TipoObrigacao.objects.filter(nome=nome).first()
        if tipo:
            tipo.unidades_gestoras_restritas.clear()

    mural = TipoObrigacao.objects.filter(nome=NOME_MURAL).first()
    if mural:
        mural.ativo = True
        mural.save()


class Migration(migrations.Migration):
    dependencies = [("obrigacoes", "0004_tipoobrigacao_unidades_gestoras_restritas")]
    operations = [migrations.RunPython(aplicar, reverter)]
