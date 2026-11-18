"""
Parser para "SALDO DAS FICHAS DE RESTOS A PAGAR" do ASPEC
(`DADOS/RESTOS/FICHAS_RESTOS.PDF`) — um único arquivo cobrindo TODAS as
Unidades Gestoras (seção por UG, nome na linha 3 de cada página, mesma
convenção de `aspec_restos_a_pagar.py`/relatórios de saldo), foto de
02/01/2026.

Ao contrário de `RP01.PDF`..`RP09.PDF` (que só dão exercício/número do
empenho/valores), este relatório traz a classificação orçamentária
completa e o credor de cada empenho em aberto — órgão/unidade
orçamentária, função/subfunção/programa/ação, elemento de despesa e
fonte — exatamente o que falta em `RestoAPagar` para virar algo
navegável além de um número de empenho isolado. Por isso este parser
não cria `RestoAPagar` novo: `services.enriquecer_restos_a_pagar_fichas()`
usa (unidade_gestora, exercício, número do empenho) como chave para
preencher os campos descritivos nos registros que `importar_restos_a_pagar`
já gravou.

Hierarquia por seção de UG (uma árvore, não colunas fixas):

    <exercício, 4 dígitos sozinhos>
    <órgão (2 díg.)> <unidade orçamentária (2 díg.)>.
    <função> <subfunção> <programa> <ação ("D.DDD")> [nome da ação]
    <elemento de despesa: "D.D.DD.DD.DD nome">
    <código do empenho (8 díg.)> <nome do credor>
    <código da fonte (8 díg.)> - <nome da fonte>
    Sdo não proc. <valor> Sdo proc. <valor> <total>

Cada nível pode repetir vários filhos antes do próximo "irmão" (vários
elementos sob uma ação, vários empenhos sob um elemento, várias fontes
— raro — sob um empenho). Um novo bloco "função/subfunção/programa/ação"
ou um novo "órgão/unidade" encerra implicitamente os níveis mais
profundos, igual a `aspec_fichas.py`.

As linhas de "SUB-TOTAL"/"TOTAL do detalhamento"/"TOTAL GERAL" não
precisam ser lidas (os valores já vêm de `RP0x.PDF`) — o parser entra em
modo "resumo" na primeira linha desse tipo e ignora tudo até o próximo
exercício (4 dígitos sozinhos) ou troca de UG (reset de página), o que
elimina de forma simples a ambiguidade entre uma linha de fonte real
("<código> - <nome>", sem mais nada na linha) e a mesma fonte reaparecendo
num resumo ("<código> - <nome truncado> <3 valores>" — o layout dessas
duas é quase idêntico, a única diferença confiável é estar ou não dentro
de um bloco de resumo).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from .base import ParserBase, ResultadoParsing

RE_EXERCICIO = re.compile(r"^(\d{4})$")
RE_ORGAO_UNIDADE = re.compile(r"^(\d{2})\s+(\d{2})\.$")
RE_CLASSIFICACAO = re.compile(r"^(\d{2})\s+(\d{3})\s+(\d{4})\s+(\d\.\d{3})(?:\s+(.+?))?\s*$")
RE_ELEMENTO = re.compile(r"^(\d)\.(\d)\.(\d{2})\.(\d{2})\.(\d{2})\s+(.+?)\s*$")
RE_FONTE = re.compile(r"^(\d{8})\s*-\s*(.+?)\s*$")
RE_CREDOR = re.compile(r"^(\d{8})\s+(.+?)\s*$")
RE_SALDO = re.compile(r"^Sdo n[ãa]o proc\.")

LINHAS_IGNORAR_PREFIXO = (
    "Par", "Governo Municipal", "Prefeitura Municipal", "Camara Municipal", "Câmara Municipal",
    "Fundo ", "EXERC.", "FONTE",
)
LINHAS_RESUMO_PREFIXO = ("SUB-TOTAL", "TOTAL do detalhamento", "TOTAL GERAL", "Detalhamento Geral")


def _soh_separador(texto: str) -> bool:
    return bool(texto) and set(texto) <= {"-", "=", " "}


@dataclass
class _ContextoAtual:
    unidade_gestora_nome: str | None = None
    exercicio: str | None = None
    orgao_codigo: str | None = None
    unidade_orc_codigo: str | None = None
    funcao: str | None = None
    subfuncao: str | None = None
    programa: str | None = None
    acao: str | None = None
    acao_nome: str | None = None
    elemento_codigo: str | None = None
    elemento_nome: str | None = None
    classificacao_economica_codigo: str | None = None
    em_resumo: bool = False


class FichasRestosASPECParser(ParserBase):
    tipo_relatorio = "FICHAS_RESTOS"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        resultado = ResultadoParsing()
        ctx = _ContextoAtual()
        credor_pendente: tuple[str, str] | None = None

        with pdfplumber.open(caminho_arquivo) as pdf:
            for pagina in pdf.pages:
                linhas_pagina = (pagina.extract_text() or "").split("\n")

                nome_ug_pagina = linhas_pagina[2].strip() if len(linhas_pagina) > 2 else None
                if nome_ug_pagina and not nome_ug_pagina.startswith("EXERC."):
                    if nome_ug_pagina != ctx.unidade_gestora_nome:
                        ctx = _ContextoAtual(unidade_gestora_nome=nome_ug_pagina)
                        credor_pendente = None

                for linha in linhas_pagina:
                    texto = linha.strip()
                    if not texto or _soh_separador(texto):
                        continue
                    if texto.startswith(LINHAS_IGNORAR_PREFIXO):
                        continue
                    if texto.startswith(LINHAS_RESUMO_PREFIXO):
                        ctx.em_resumo = True
                        continue

                    m_exercicio = RE_EXERCICIO.match(texto)
                    if m_exercicio:
                        ctx.exercicio = m_exercicio.group(1)
                        ctx.em_resumo = False
                        credor_pendente = None
                        continue

                    if ctx.em_resumo:
                        continue

                    m_org_un = RE_ORGAO_UNIDADE.match(texto)
                    if m_org_un:
                        ctx.orgao_codigo, ctx.unidade_orc_codigo = m_org_un.groups()
                        credor_pendente = None
                        continue

                    m_classif = RE_CLASSIFICACAO.match(texto)
                    if m_classif:
                        func, subf, prog, acao_pontuada, nome = m_classif.groups()
                        ctx.funcao, ctx.subfuncao, ctx.programa = func, subf, prog
                        ctx.acao = acao_pontuada
                        ctx.acao_nome = nome
                        ctx.elemento_codigo = ctx.elemento_nome = ctx.classificacao_economica_codigo = None
                        credor_pendente = None
                        continue

                    m_elemento = RE_ELEMENTO.match(texto)
                    if m_elemento:
                        cat, grp, mod, elem, sub, nome = m_elemento.groups()
                        ctx.elemento_codigo, ctx.elemento_nome = elem, nome
                        ctx.classificacao_economica_codigo = f"{cat}.{grp}.{mod}.{elem}.{sub}"
                        credor_pendente = None
                        continue

                    m_fonte = RE_FONTE.match(texto)
                    if m_fonte and credor_pendente is not None:
                        if not (ctx.exercicio and ctx.unidade_gestora_nome):
                            resultado.avisos.append(f"Linha de fonte sem contexto completo: {texto!r}")
                            credor_pendente = None
                            continue
                        numero_empenho, credor_nome = credor_pendente
                        resultado.linhas.append({
                            "unidade_gestora_nome": ctx.unidade_gestora_nome,
                            "exercicio_origem": int(ctx.exercicio),
                            "numero_empenho": numero_empenho,
                            "credor_nome": credor_nome,
                            "orgao_codigo": ctx.orgao_codigo,
                            "unidade_orc_codigo": ctx.unidade_orc_codigo,
                            "funcao": ctx.funcao,
                            "subfuncao": ctx.subfuncao,
                            "programa": ctx.programa,
                            "acao": ctx.acao,
                            "acao_nome": ctx.acao_nome,
                            "elemento_codigo": ctx.elemento_codigo,
                            "elemento_nome": ctx.elemento_nome,
                            "classificacao_economica_codigo": ctx.classificacao_economica_codigo,
                        })
                        credor_pendente = None
                        continue

                    if RE_SALDO.match(texto):
                        continue

                    m_credor = RE_CREDOR.match(texto)
                    if m_credor:
                        credor_pendente = m_credor.groups()
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "FICHAS_RESTOS"): FichasRestosASPECParser,
}
