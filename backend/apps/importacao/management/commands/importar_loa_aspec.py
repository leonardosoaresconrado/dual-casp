from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_loa import RelacionamentoAcoesASPECParser
from apps.importacao.services import seed_catalogos_loa
from apps.orcamento.models import LOA


class Command(BaseCommand):
    help = (
        "Importa o 'Relacionamento das ações com projetos/atividades' (PDF do ASPEC) "
        "para cadastrar Função, Subfunção, Programa e Ação de uma LOA."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--loa", type=int, required=True, help="ID da LOA de destino")

    def handle(self, *args, **options):
        try:
            loa = LOA.objects.get(pk=options["loa"])
        except LOA.DoesNotExist as exc:
            raise CommandError(f"LOA {options['loa']} não encontrada.") from exc

        parser_loa = RelacionamentoAcoesASPECParser()
        resultado = parser_loa.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = seed_catalogos_loa(resultado, loa)

        self.stdout.write(self.style.SUCCESS(
            f"Catálogos atualizados: {out.funcoes_criadas} funções novas, "
            f"{out.subfuncoes_criadas} subfunções novas, {out.programas_criados} programas novos, "
            f"{out.acoes_criadas} ações novas."
        ))
