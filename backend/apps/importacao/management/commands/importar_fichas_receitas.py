from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_fichas_receitas import FichasReceitasASPECParser
from apps.importacao.services import importar_fichas_receitas
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa 'Classificação Econômica da Receita - Local' (FICHAS_RECEITAS.PDF) "
        "para criar/atualizar RubricaReceita (código x fonte, por Unidade Gestora)."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_fichas = FichasReceitasASPECParser()
        resultado = parser_fichas.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = importar_fichas_receitas(resultado, municipio)

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante a importação:"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.rubricas_criadas} rubricas novas, "
            f"{out.rubricas_atualizadas} atualizadas, {out.fontes_criadas} fontes de recursos novas."
        ))
