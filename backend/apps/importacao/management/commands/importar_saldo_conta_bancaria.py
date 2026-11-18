from django.core.management.base import BaseCommand, CommandError

from apps.importacao.parsers.aspec_saldo_conta_bancaria import SaldoContaBancariaASPECParser
from apps.importacao.services import importar_saldo_conta_bancaria
from apps.municipios.models import Municipio


class Command(BaseCommand):
    help = (
        "Importa 'Relação de saldos - Por UG titular da conta' (um único PDF por mês cobrindo "
        "todas as Unidades Gestoras) para SaldoContaBancaria/SaldoContaBancariaFonte. UG (por "
        "página) e mês vêm do relatório, nunca do nome do arquivo/pasta — a importação é abortada "
        "se o mês não for identificado."
    )

    def add_arguments(self, parser):
        parser.add_argument("caminho_pdf", type=str)
        parser.add_argument("--municipio", type=int, required=True, help="ID do Município")

    def handle(self, *args, **options):
        try:
            municipio = Municipio.objects.get(pk=options["municipio"])
        except Municipio.DoesNotExist as exc:
            raise CommandError(f"Município {options['municipio']} não encontrado.") from exc

        parser_saldo = SaldoContaBancariaASPECParser()
        resultado = parser_saldo.parse(options["caminho_pdf"])

        if resultado.avisos:
            self.stdout.write(self.style.WARNING(f"{len(resultado.avisos)} aviso(s) durante o parsing:"))
            for aviso in resultado.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        try:
            out = importar_saldo_conta_bancaria(resultado, municipio)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if out.avisos:
            self.stdout.write(self.style.WARNING(f"{len(out.avisos)} aviso(s) durante a importação:"))
            for aviso in out.avisos[:20]:
                self.stdout.write(f"  - {aviso}")

        self.stdout.write(self.style.SUCCESS(
            f"Importação concluída: {len(out.unidades_gestoras or [])} Unidade(s) Gestora(s), "
            f"mês {out.mes_referencia} — {out.contas_criadas} contas / {out.fontes_criadas} fontes gravadas."
        ))
        for nome_ug in out.unidades_gestoras or []:
            self.stdout.write(f"  - {nome_ug}")
