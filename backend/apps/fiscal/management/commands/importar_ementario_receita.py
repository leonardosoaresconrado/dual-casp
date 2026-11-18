from django.core.management.base import BaseCommand, CommandError

from apps.fiscal.services import importar_ementario_receita


class Command(BaseCommand):
    help = (
        "Preenche o nome oficial de cada nível 1-6 da hierarquia de "
        "classificação de receita (Categoria/Origem/Espécie/Rubrica/Alínea/"
        "Subalínea) a partir do xlsx oficial 'Ementário da Natureza de "
        "Receita' da STN/SOF, casando pelo código NR de 8 dígitos. Rode "
        "popular_classificacao_receita antes, para a hierarquia já existir."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_xlsx", type=str)

    def handle(self, *args, **options):
        try:
            out = importar_ementario_receita(options["caminho_xlsx"])
        except KeyError as exc:
            raise CommandError(f"Aba não encontrada no arquivo: {exc}") from exc

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s):"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Concluído: {out.nomes_disponiveis} nomes disponíveis na planilha. Atualizados — "
            f"Categorias: {out.categorias_atualizadas}, Origens: {out.origens_atualizadas}, "
            f"Espécies: {out.especies_atualizadas}, Rubricas: {out.rubricas_atualizadas}, "
            f"Alíneas: {out.alineas_atualizadas}, Subalíneas: {out.subalineas_atualizadas}, "
            f"Tipos: {out.tipos_atualizados}."
        ))
