"""
Dispatcher: liga `Importacao.tipo_relatorio` (escolhido pelo usuário no
upload, via `ImportacoesPage.tsx`) ao par parser+service corretos — a
peça que faltava para o upload pela tela virar uma importação de verdade,
sem precisar rodar `manage.py importar_*` no terminal (ver nota em
CLAUDE.md, "dispatch pro parser certo ainda é manual").

Cada entrada de `MAPEAMENTO` replica exatamente o que o management
command equivalente já faz (mesmo parser, mesma função de `services.py`,
mesma semântica de reimportação) — este módulo não duplica lógica de
negócio, só decide QUAL parser/service chamar a partir do tipo escolhido
e QUAL destino resolver (município, na maioria; LOA, só para o
relacionamento de ações).

Deliberadamente síncrono (sem fila/celery) — este projeto não tem
infraestrutura assíncrona, e os parsers já rodam em segundos mesmo para
os PDFs maiores vistos (5-12 páginas). Se um dia os arquivos ficarem
grandes o bastante para isso doer, revisitar.
"""

from dataclasses import dataclass
from typing import Callable, Literal

from apps.importacao.parsers.aspec_empenhos import EmpenhosASPECParser
from apps.importacao.parsers.aspec_estrutura import EstruturaOrganizacionalASPECParser
from apps.importacao.parsers.aspec_execucao_receita import ExecucaoReceitaASPECParser
from apps.importacao.parsers.aspec_fichas import FichasDespesaASPECParser
from apps.importacao.parsers.aspec_fichas_receitas import FichasReceitasASPECParser
from apps.importacao.parsers.aspec_fichas_restos import FichasRestosASPECParser
from apps.importacao.parsers.aspec_fontes import FontesRecursosASPECParser
from apps.importacao.parsers.aspec_loa import RelacionamentoAcoesASPECParser
from apps.importacao.parsers.aspec_loa_despesas import LOADespesasASPECParser
from apps.importacao.parsers.aspec_restos_a_pagar import RestosAPagarASPECParser
from apps.importacao.parsers.aspec_rgf_dtp import RGFDTPASPECParser
from apps.importacao.parsers.aspec_rreo_asps import RREOASPSASPECParser
from apps.importacao.parsers.aspec_rreo_mde import RREOMDEASPECParser
from apps.importacao.parsers.aspec_saldo_balanco import SaldoBalancoASPECParser
from apps.importacao.parsers.aspec_saldo_conta_bancaria import SaldoContaBancariaASPECParser
from apps.importacao.parsers.base import ParserBase
from apps.importacao.services import (
    enriquecer_restos_a_pagar_fichas,
    importar_asps,
    importar_dotacoes_loa,
    importar_dtp,
    importar_empenhos,
    importar_estrutura_organizacional,
    importar_execucao_receita,
    importar_fichas_despesa,
    importar_fichas_receitas,
    importar_fontes_recursos,
    importar_mde_e_magisterio,
    importar_restos_a_pagar,
    importar_saldo_balanco,
    importar_saldo_conta_bancaria,
    seed_catalogos_loa,
)
from apps.importacao.models import Importacao, StatusImportacao, TipoRelatorio


class ErroDispatcher(Exception):
    """Erro de pré-condição do dispatcher (destino não resolvível, tipo sem mapeamento) — não um erro de parsing."""


@dataclass
class DispatchEntry:
    parser_cls: type[ParserBase]
    service_fn: Callable
    destino: Literal["municipio", "loa"] = "municipio"
    aceita_importacao: bool = False  # service_fn aceita kwarg importacao= para stampar o FK de volta


MAPEAMENTO: dict[str, DispatchEntry] = {
    TipoRelatorio.ESTRUTURA_ORGANIZACIONAL: DispatchEntry(
        EstruturaOrganizacionalASPECParser, importar_estrutura_organizacional
    ),
    TipoRelatorio.LOA_RELACIONAMENTO_ACOES: DispatchEntry(
        RelacionamentoAcoesASPECParser, seed_catalogos_loa, destino="loa"
    ),
    TipoRelatorio.LOA_DOTACOES: DispatchEntry(
        LOADespesasASPECParser, importar_dotacoes_loa, aceita_importacao=True
    ),
    TipoRelatorio.FICHAS_DESPESA: DispatchEntry(FichasDespesaASPECParser, importar_fichas_despesa),
    TipoRelatorio.EMPENHOS: DispatchEntry(EmpenhosASPECParser, importar_empenhos, aceita_importacao=True),
    TipoRelatorio.FONTES_RECURSOS: DispatchEntry(FontesRecursosASPECParser, importar_fontes_recursos),
    TipoRelatorio.FICHAS_RECEITAS: DispatchEntry(FichasReceitasASPECParser, importar_fichas_receitas),
    TipoRelatorio.EXECUCAO_RECEITA: DispatchEntry(ExecucaoReceitaASPECParser, importar_execucao_receita),
    TipoRelatorio.SALDO_BALANCO: DispatchEntry(SaldoBalancoASPECParser, importar_saldo_balanco),
    TipoRelatorio.SALDO_CONTA_BANCARIA: DispatchEntry(SaldoContaBancariaASPECParser, importar_saldo_conta_bancaria),
    TipoRelatorio.RESTOS_A_PAGAR: DispatchEntry(RestosAPagarASPECParser, importar_restos_a_pagar),
    TipoRelatorio.ENRIQUECIMENTO_RESTOS_A_PAGAR: DispatchEntry(
        FichasRestosASPECParser, enriquecer_restos_a_pagar_fichas
    ),
    TipoRelatorio.DTP: DispatchEntry(RGFDTPASPECParser, importar_dtp),
    TipoRelatorio.MDE_MAGISTERIO_VAAT_FUNDEB: DispatchEntry(RREOMDEASPECParser, importar_mde_e_magisterio),
    TipoRelatorio.ASPS: DispatchEntry(RREOASPSASPECParser, importar_asps),
}


def processar_importacao(importacao: Importacao) -> None:
    """
    Roda o parser+service certos para `importacao.arquivo`, atualizando
    `status`/`mensagem_erro`/`linhas_importadas`/`processado_em` no
    próprio registro (sempre salvo, sucesso ou erro — nunca deixa em
    PROCESSANDO). Só levanta `ErroDispatcher` pra cima (sem marcar o
    registro) quando o `tipo_relatorio` não tem mapeamento — um erro de
    configuração, não de dado. Qualquer outra falha (LOA não resolvível,
    exceção do parser/service) é capturada e vira status=ERRO com a
    mensagem em `mensagem_erro`, igual a um aviso de management command,
    nunca um 500 pro usuário.
    """
    from django.utils import timezone

    entrada = MAPEAMENTO.get(importacao.tipo_relatorio)
    if entrada is None:
        raise ErroDispatcher(
            f"Tipo de relatório '{importacao.get_tipo_relatorio_display()}' não tem parser automático "
            "configurado — importe via management command."
        )

    importacao.status = StatusImportacao.PROCESSANDO
    importacao.save(update_fields=["status"])

    try:
        if entrada.destino == "loa":
            if not importacao.exercicio_id or not hasattr(importacao.exercicio, "loa"):
                raise ErroDispatcher(
                    "Este tipo de relatório grava na LOA do exercício — selecione um Exercício que já "
                    "tenha uma LOA cadastrada antes de processar."
                )
            destino = importacao.exercicio.loa
        else:
            destino = importacao.municipio

        resultado = entrada.parser_cls().parse(importacao.arquivo.path)

        kwargs = {}
        if entrada.aceita_importacao:
            kwargs["importacao"] = importacao
        out = entrada.service_fn(resultado, destino, **kwargs)

        avisos = list(resultado.avisos) + list(getattr(out, "avisos", None) or [])
        importacao.status = StatusImportacao.CONCLUIDA
        importacao.linhas_importadas = len(resultado.linhas)
        importacao.mensagem_erro = "\n".join(f"Aviso: {a}" for a in avisos)
    except Exception as exc:  # noqa: BLE001 — qualquer falha de parsing/import vira ERRO, nunca um 500
        importacao.status = StatusImportacao.ERRO
        importacao.mensagem_erro = str(exc)
    finally:
        importacao.processado_em = timezone.now()
        importacao.save(update_fields=["status", "mensagem_erro", "linhas_importadas", "processado_em"])
