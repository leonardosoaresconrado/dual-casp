from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_execucao_receita import ExecucaoReceitaASPECParser
from apps.importacao.services import importar_execucao_receita
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa 'Demonstrativo da receita por classificação econômica' (um PDF por mês, "
        "R01.PDF..R09.PDF) para LancamentoExecucaoReceita — receita arrecadada quebrada por "
        "fonte de recursos. Rode um arquivo por vez; a ordem entre meses não importa."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_execucao = ExecucaoReceitaASPECParser()
        resultado = parser_execucao.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = importar_execucao_receita(resultado, municipio)

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante a importação:"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.lancamentos_criados} lançamentos novos, "
            f"{out.lancamentos_atualizados} atualizados, {out.rubricas_criadas} rubricas de receita novas."
        ))
