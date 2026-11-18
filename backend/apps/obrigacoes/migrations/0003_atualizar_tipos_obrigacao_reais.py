from django.db import migrations

# A lista original (semeada em 0002) foi chutada a partir dos itens do menu
# do Portal NEC — nenhuma delas bate com o calendário real de competências
# que o escritório exporta de uma área logada (ver histórico da conversa,
# 2026-11-16). Esta migration corrige o catálogo: renomeia 3 tipos para seus
# nomes reais e acrescenta os demais tipos reais encontrados no calendário.
# UNICAD/Mural de Licitações/Processos Eletrônicos/Pauta de
# Julgamentos/Decisões Plenárias não aparecem nesse calendário de prazos —
# ficam como estavam (sem periodicidade, sem geração automática de
# competência), só com o botão "Verificar agora".

RENOMEIOS = [
    # (nome_antigo, nome_novo, periodicidade_nova)
    ("Dados Contábeis", "Arquivo Contábil", "MENSAL"),
    ("Folha de Pagamento", "Arquivo de Folha de Pagamento", "MENSAL"),
    ("Prestação de Contas", "Prestação de Contas", "QUADRIMESTRAL"),
]

NOVOS_TIPOS = [
    {"nome": "Matriz de Saldos Contábeis", "escopo": "UNIDADE_GESTORA", "periodicidade": "MENSAL", "ordem": 9},
    {"nome": "RREO", "escopo": "UNIDADE_GESTORA", "periodicidade": "BIMESTRAL", "ordem": 10},
    {"nome": "RGF", "escopo": "UNIDADE_GESTORA", "periodicidade": "QUADRIMESTRAL", "ordem": 11},
    {"nome": "LDO", "escopo": "UNIDADE_GESTORA", "periodicidade": "ANUAL", "ordem": 12},
    {"nome": "Balanço Geral", "escopo": "UNIDADE_GESTORA", "periodicidade": "ANUAL", "ordem": 13},
    {
        "nome": "Arquivo Contábil - Consolidação de Saldos",
        "escopo": "UNIDADE_GESTORA",
        "periodicidade": "ANUAL",
        "ordem": 14,
    },
    {
        "nome": "Matriz de Saldos Contábeis - Consolidação de Saldos",
        "escopo": "UNIDADE_GESTORA",
        "periodicidade": "ANUAL",
        "ordem": 15,
    },
]

DESCRICAO_PADRAO = (
    "Prazo exato ainda não segue uma fórmula fixa (há ajustes de dia útil/feriado) — "
    "as competências reais são importadas literalmente via "
    "`importar_calendario_obrigacoes`; `prazo_meses_apos_periodo`/`prazo_dia_limite` "
    "ficam em aberto como aproximação de reserva, se um dia você quiser preenchê-los."
)


def atualizar(apps, schema_editor):
    TipoObrigacao = apps.get_model("obrigacoes", "TipoObrigacao")

    for nome_antigo, nome_novo, periodicidade in RENOMEIOS:
        tipo = TipoObrigacao.objects.filter(nome=nome_antigo).first()
        if tipo:
            tipo.nome = nome_novo
            tipo.periodicidade = periodicidade
            tipo.save()

    for t in NOVOS_TIPOS:
        TipoObrigacao.objects.get_or_create(
            nome=t["nome"],
            defaults={
                "orgao_externo": "TCM-PA",
                "escopo": t["escopo"],
                "periodicidade": t["periodicidade"],
                "ordem": t["ordem"],
                "descricao": DESCRICAO_PADRAO,
            },
        )


def reverter(apps, schema_editor):
    TipoObrigacao = apps.get_model("obrigacoes", "TipoObrigacao")

    for nome_antigo, nome_novo, _periodicidade in RENOMEIOS:
        tipo = TipoObrigacao.objects.filter(nome=nome_novo).first()
        if tipo:
            tipo.nome = nome_antigo
            tipo.periodicidade = None
            tipo.save()

    TipoObrigacao.objects.filter(nome__in=[t["nome"] for t in NOVOS_TIPOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("obrigacoes", "0002_seed_tipos_obrigacao_tcmpa")]
    operations = [migrations.RunPython(atualizar, reverter)]
