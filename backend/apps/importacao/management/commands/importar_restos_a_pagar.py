from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_restos_a_pagar import RestosAPagarASPECParser
from apps.importacao.services import importar_restos_a_pagar
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa 'DEMONSTRATIVO DOS RESTOS A PAGAR POR FONTE DE RECURSOS' (um PDF por mês, "
        "RP01.PDF..RP09.PDF, cobrindo todas as UGs) para RestoAPagar. É um relatório cumulativo "
        "reimpresso por inteiro todo mês — reimportar um mês substitui integralmente aquele mês."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_restos = RestosAPagarASPECParser()
        resultado = parser_restos.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        try:
            out = importar_restos_a_pagar(resultado, municipio)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante a importação:"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: mês {out.mes_referencia} — {out.restos_criados} restos a pagar gravados."
        ))
