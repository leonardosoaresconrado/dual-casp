from django.db import migrations

URL_PORTAL_NEC_TCMPA = "https://www.tcm.pa.gov.br/nec/jurisdicionados/"

# Escopo MUNICIPIO/UNIDADE_GESTORA é o melhor palpite com base no portal —
# UNICAD, Pauta de Julgamentos e Decisões Plenárias são município-wide
# (cadastro único/pautas do próprio TCM); os demais 5 variam por Unidade
# Gestora (cada UG presta contas/folha/licitação separadamente). Tudo
# editável depois em "Tipos de Obrigação" sem precisar de nova migration.
TIPOS = [
    {"nome": "UNICAD", "escopo": "MUNICIPIO", "ordem": 1},
    {"nome": "Prestação de Contas", "escopo": "UNIDADE_GESTORA", "ordem": 2},
    {"nome": "Dados Contábeis", "escopo": "UNIDADE_GESTORA", "ordem": 3},
    {"nome": "Folha de Pagamento", "escopo": "UNIDADE_GESTORA", "ordem": 4},
    {"nome": "Mural de Licitações", "escopo": "UNIDADE_GESTORA", "ordem": 5},
    {"nome": "Processos Eletrônicos", "escopo": "UNIDADE_GESTORA", "ordem": 6},
    {"nome": "Pauta de Julgamentos", "escopo": "MUNICIPIO", "ordem": 7},
    {"nome": "Decisões Plenárias", "escopo": "MUNICIPIO", "ordem": 8},
]


def seed(apps, schema_editor):
    TipoObrigacao = apps.get_model("obrigacoes", "TipoObrigacao")
    for t in TIPOS:
        TipoObrigacao.objects.get_or_create(
            nome=t["nome"],
            defaults={
                "orgao_externo": "TCM-PA",
                "escopo": t["escopo"],
                "periodicidade": None,
                "url_consulta": URL_PORTAL_NEC_TCMPA,
                "ordem": t["ordem"],
                "descricao": (
                    "Consulta pública do Portal NEC do TCM-PA — periodicidade e prazo "
                    "ainda não configurados; defina-os neste cadastro antes que esta "
                    "obrigação passe a gerar competências."
                ),
            },
        )


def remover(apps, schema_editor):
    TipoObrigacao = apps.get_model("obrigacoes", "TipoObrigacao")
    TipoObrigacao.objects.filter(nome__in=[t["nome"] for t in TIPOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("obrigacoes", "0001_initial")]
    operations = [migrations.RunPython(seed, remover)]
