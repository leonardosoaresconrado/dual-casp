from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_fontes import FontesRecursosASPECParser
from apps.importacao.services import importar_fontes_recursos
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa 'Fontes de recursos' do ASPEC para atualizar nome/tipo de toda "
        "FonteRecursos já cadastrada (não cria fontes novas)."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_fontes = FontesRecursosASPECParser()
        resultado = parser_fontes.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = importar_fontes_recursos(resultado, municipio)

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.fontes_atualizadas} fontes de recursos atualizadas."
        ))
