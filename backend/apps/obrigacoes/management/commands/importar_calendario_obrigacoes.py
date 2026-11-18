from django.core.management.base import BaseCommand, CommandError

from apps.municipios.models import Municipio
from apps.obrigacoes.services import importar_calendario_literal


class Command(BaseCommand):
    help = (
        "Importa literalmente um calendário de competências/prazos de obrigações "
        "(colado de uma área logada do escritório — não é um PDF da ASPEC nem a "
        "consulta pública do TCM-PA). Formato esperado por linha: "
        "'<exercício> - <competência>' + Data Início (YYYY-MM-DD) + "
        "Data Limite (DD.MM.YYYY), campos separados por 2+ espaços ou tab."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_arquivo", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        with open(options["caminho_arquivo"], encoding="utf-8") as f:
            texto = f.read()

        resultado = importar_calendario_literal(municipio, texto)

        if resultado["avisos"]:
            self.stdout.write(self.style.WARNING(f"{len(resultado['avisos'])} aviso(s):"))
            for aviso in resultado["avisos"][:50]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(
            self.style.SUCCESS(f"Importação concluída: {resultado['linhas_processadas']} linha(s) processada(s).")
        )
