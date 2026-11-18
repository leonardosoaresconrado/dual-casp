from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_empenhos import EmpenhosASPECParser
from apps.importacao.services import importar_empenhos
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa o relatório de empenhos do ASPEC (planilha) para o detalhamento por "
        "empenho (Empenho/EmpenhoMovimento). Cria RubricaOrcamentaria novas "
        "(origem_dotacao=CREDITO_ADICIONAL) quando a classificação não foi prevista na LOA."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_planilha", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_empenhos = EmpenhosASPECParser()
        resultado = parser_empenhos.parse(options["caminho_planilha"])

        out = importar_empenhos(resultado, municipio)

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante a importação:"))
            for aviso in out.avisos[:30]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.empenhos_criados} empenhos criados, "
            f"{out.empenhos_atualizados} atualizados, {out.rubricas_criadas} rubricas "
            f"novas (crédito adicional)."
        ))
