from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_fichas_restos import FichasRestosASPECParser
from apps.importacao.services import enriquecer_restos_a_pagar_fichas
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Enriquece RestoAPagar já importado (via importar_restos_a_pagar) com credor, órgão, "
        "unidade orçamentária, elemento de despesa e classificação funcional-programática, a partir "
        "de 'SALDO DAS FICHAS DE RESTOS A PAGAR' (FICHAS_RESTOS.PDF). Rodar depois de importar_restos_a_pagar "
        "para pelo menos um mês — não cria RestoAPagar novo, só preenche os campos descritivos."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_fichas = FichasRestosASPECParser()
        resultado = parser_fichas.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        out = enriquecer_restos_a_pagar_fichas(resultado, municipio)

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante o enriquecimento:"))
            for aviso in out.avisos[:30]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Enriquecimento concluído: {out.registros_atualizados} registro(s) de RestoAPagar atualizados "
            f"({out.empenhos_nao_encontrados} empenho(s) do relatório sem correspondência)."
        ))
