from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec import ExecucaoOrcamentariaASPECParser
from apps.importacao.services import importar_execucao_orcamentaria
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa um relatório PDF do ASPEC (Demonstrativo Resumido da Despesa). A Unidade "
        "Gestora de cada linha é resolvida pela estrutura organizacional já cadastrada "
        "(rode importar_estrutura antes)."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")
        parser.add_argument("--numero-lei-loa", type=str, default="(a definir)")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_aspec = ExecucaoOrcamentariaASPECParser()
        resultado = parser_aspec.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = importar_execucao_orcamentaria(
            resultado, municipio, numero_lei_loa_padrao=options["numero_lei_loa"]
        )

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante a importação:"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.linhas_criadas} lançamentos criados, "
            f"{out.linhas_atualizadas} atualizados, {out.rubricas_criadas} rubricas novas."
        ))
