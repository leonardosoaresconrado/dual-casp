from django.core.management.base import BaseCommand

from apps.fiscal.services import popular_classificacao_receita


class Command(BaseCommand):
    help = (
        "Decompõe o código de cada RubricaReceita já importada nos 7 níveis "
        "oficiais do Ementário da Receita (STN) e vincula cada rubrica ao "
        "nível folha (Tipo) correspondente. Não lê nenhum arquivo — deriva "
        "da estrutura DB existente. Seguro rodar de novo a qualquer momento "
        "(idempotente)."
    )

    def handle(self, *args, **options):
        out = popular_classificacao_receita()

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s):"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Concluído: {out.rubricas_processadas} rubricas processadas, "
            f"{out.rubricas_vinculadas} vinculadas à hierarquia STN, "
            f"{out.niveis_criados} níveis novos criados, "
            f"{out.deducoes_vinculadas} deduções vinculadas à rubrica principal."
        ))
