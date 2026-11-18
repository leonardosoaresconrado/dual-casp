from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_estrutura import EstruturaOrganizacionalASPECParser
from apps.importacao.services import importar_estrutura_organizacional
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa a 'Estrutura organizacional' do ASPEC para cadastrar Unidade Gestora/"
        "Órgão/Unidade Orçamentária com nomes reais e a UG correta de cada unidade. "
        "Deve rodar antes de qualquer outra importação que crie Órgão/Unidade Orçamentária."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_estrutura = EstruturaOrganizacionalASPECParser()
        resultado = parser_estrutura.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = importar_estrutura_organizacional(resultado, municipio)

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {out.unidades_gestoras_criadas} unidades gestoras novas, "
            f"{out.orgaos_criados} órgãos novos, {out.unidades_orcamentarias_criadas} "
            f"unidades orçamentárias novas."
        ))
