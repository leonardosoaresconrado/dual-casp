from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_rreo_mde import RREOMDEASPECParser
from apps.importacao.services import importar_mde_e_magisterio
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa o RREO-Anexo 8 (Demonstrativo das Receitas e Despesas com MDE) para "
        "ApuracaoMDE, ApuracaoMagisterioFundeb, ApuracaoVAATEducacaoInfantil, "
        "ApuracaoVAATDespesaCapital, ApuracaoValorNaoAplicadoFundeb e "
        "ApuracaoReprogramacaoFundeb (um único PDF alimenta os seis índices). "
        "Bimestre/exercício vêm do cabeçalho do relatório, não do nome do arquivo."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        resultado = RREOMDEASPECParser().parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = importar_mde_e_magisterio(resultado, municipio)

        if not resultado.linhas:
            raise CommandError("Nenhuma apuração extraída do relatório — confira os avisos acima.")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.gravados} registro(s) gravados "
            f"(ApuracaoMDE/ApuracaoMagisterioFundeb/ApuracaoETIFundeb/ApuracaoVAATEducacaoInfantil/ApuracaoVAATDespesaCapital/"
            f"ApuracaoValorNaoAplicadoFundeb/ApuracaoReprogramacaoFundeb)."
        ))
