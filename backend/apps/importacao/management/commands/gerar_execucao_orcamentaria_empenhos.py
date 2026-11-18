from django.core.management.base import BaseCommand, CommandError

from apps.importacao.services import gerar_execucao_orcamentaria_por_empenhos
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Gera/atualiza LancamentoExecucaoOrcamentaria de um mês agregando "
        "Empenho/EmpenhoMovimento por RubricaOrcamentaria, sem depender de "
        "balancete em PDF (fonte usada a partir do mês em que o ASPEC "
        "deixou de fornecer balancete). Rode importar_empenhos do mês antes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")
        parser.add_argument("--mes", type=int, required=True, help="Mês de referência (1-12)")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        mes = options["mes"]
        if not 1 <= mes <= 12:
            raise CommandError("--mes deve estar entre 1 e 12.")

        out = gerar_execucao_orcamentaria_por_empenhos(municipio, mes)

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s):"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Geração concluída: {out.rubricas_processadas} rubricas processadas, "
            f"{out.linhas_criadas} lançamentos criados, {out.linhas_atualizadas} atualizados."
        ))
