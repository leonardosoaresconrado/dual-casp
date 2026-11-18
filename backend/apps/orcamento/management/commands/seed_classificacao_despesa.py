"""
Semeia os catálogos nacionais de Categoria Econômica e Grupo de Natureza de
Despesa, cujos códigos e nomes são fixados pela Lei 4.320/64 e pelo Manual
de Contabilidade Aplicada ao Setor Público (STN) — idênticos em todos os
municípios brasileiros.
"""

from django.core.management.base import BaseCommand

from apps.orcamento.models import CategoriaEconomica, GrupoNaturezaDespesa

CATEGORIAS = [
    ("3", "Despesas Correntes"),
    ("4", "Despesas de Capital"),
]

GRUPOS = [
    ("1", "Pessoal e Encargos Sociais"),
    ("2", "Juros e Encargos da Dívida"),
    ("3", "Outras Despesas Correntes"),
    ("4", "Investimentos"),
    ("5", "Inversões Financeiras"),
    ("6", "Amortização da Dívida"),
    ("9", "Reserva de Contingência"),
]


class Command(BaseCommand):
    help = "Semeia Categoria Econômica e Grupo de Natureza de Despesa (catálogos nacionais fixos)."

    def handle(self, *args, **options):
        criadas = sum(
            CategoriaEconomica.objects.get_or_create(codigo=c, defaults={"nome": n})[1]
            for c, n in CATEGORIAS
        )
        criados = sum(
            GrupoNaturezaDespesa.objects.get_or_create(codigo=c, defaults={"nome": n})[1]
            for c, n in GRUPOS
        )
        self.stdout.write(self.style.SUCCESS(
            f"{criadas} categoria(s) econômica(s) nova(s), {criados} grupo(s) de natureza nova(s)."
        ))
