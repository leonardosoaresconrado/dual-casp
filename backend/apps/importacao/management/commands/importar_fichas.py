from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_fichas import FichasDespesaASPECParser
from apps.importacao.services import importar_fichas_despesa
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa a 'Tabela de fichas de despesa' do ASPEC para refinar origem_dotacao "
        "(Orçamento/Crédito Suplementar/Crédito Especial) e criar as combinações previstas "
        "ainda sem valor. Rode depois de importar_dotacoes_loa."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_fichas = FichasDespesaASPECParser()
        resultado = parser_fichas.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = importar_fichas_despesa(resultado, municipio)

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante a importação:"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.rubricas_criadas} rubricas novas, "
            f"{out.rubricas_origem_corrigida} com origem corrigida."
        ))
