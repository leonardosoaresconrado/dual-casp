from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_loa_despesas import LOADespesasASPECParser
from apps.importacao.services import importar_dotacoes_loa
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa o 'Movimentos de Despesa Fixada' do ASPEC (a LOA com valores) para "
        "cadastrar a dotação inicial (origem_dotacao=ORCAMENTO) de cada rubrica."
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

        parser_loa = LOADespesasASPECParser()
        resultado = parser_loa.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = importar_dotacoes_loa(resultado, municipio, numero_lei_loa_padrao=options["numero_lei_loa"])

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante a importação:"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.rubricas_criadas} rubricas novas, "
            f"{out.rubricas_atualizadas} atualizadas, {out.unidades_orcamentarias_criadas} "
            f"unidades orçamentárias novas."
        ))
