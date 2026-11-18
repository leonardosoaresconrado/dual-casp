"""
Parser para "Tabela de fichas de despesa" exportado em PDF pelo ASPEC —
mesma árvore de classificação do "Movimentos de Despesa Fixada"
(órgão/unidade/função/subfunção/programa/ação/elemento/fonte), mas em vez
de data/valor/lei, cada linha-folha (fonte) traz a coluna "Origem ficha"
nativa do ASPEC: "Orçamento", "Créd suple." (crédito suplementar) ou
"Créd espec." (crédito especial) — granularidade maior que o flag
ORCAMENTO/CREDITO_ADICIONAL usado até aqui (ver RubricaOrcamentaria).

Particularidades deste relatório (diferentes do "Movimentos de Despesa
Fixada"):
- O código de Função (2 dígitos) tem o mesmo formato do código de Órgão —
  só dá pra diferenciar pela posição: Função sempre vem logo após uma
  linha de Unidade Orçamentária. O parser rastreia isso com
  `aguardando_funcao`.
- O nome da Ação às vezes quebra em duas linhas (ex.: "...Convênios e
  Parcerias com Entidades sem" / "Fins Lucrativos") — toda linha que não
  bate em nenhum padrão estrutural e aparece logo após uma linha de Ação
  é tratada como continuação do nome dela.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from .base import ParserBase, ResultadoParsing

RE_SOMENTE_SEPARADOR = re.compile(r"^[-\s]+$")
RE_FONTE = re.compile(r"^(\d{8})\s+(.+?)\s+(?:Sim\s+)?(Orçamento|Créd suple\.|Créd espec\.)\s*$", re.IGNORECASE)
RE_ELEMENTO = re.compile(r"^(\d)\.(\d)\.(\d{2})\.(\d{2})\.(\d{2})\s+(.+?)\s*$")
RE_ACAO = re.compile(r"^(\d{2})\s+(\d{3})\s+(\d{4})\s+(\d\.\d{3})\s+(.+?)\s*$")
RE_PROGRAMA = re.compile(r"^(\d{2})\s+(\d{3})\s+(\d{4})\s+(.+?)\s*$")
RE_SUBFUNCAO = re.compile(r"^(\d{2})\s+(\d{3})\s+(.+?)\s*$")
RE_UNIDADE = re.compile(r"^(\d{2})\s+(\d{2})\.\s+(.+?)\s*$")
RE_ORGAO_OU_FUNCAO = re.compile(r"^(\d{2})\s+(.+?)\s*$")

LINHAS_CABECALHO_IGNORAR = (
    "PREFEITURA MUNICIPAL",
    "GOVERNO MUNICIPAL",
    "CONSOLIDADO",
    "TABELA DE FICHAS",
    "CÓDIGO NOME",
    "SUGER. ORIGEM",
    "TOTAL DE ITENS",
)

ORIGEM_MAP = {"orçamento": "ORCAMENTO", "créd suple.": "CREDITO_SUPLEMENTAR", "créd espec.": "CREDITO_ESPECIAL"}


def _agrupar_linhas(pagina) -> list[str]:
    palavras = sorted(pagina.extract_words(), key=lambda w: (round(w["top"]), w["x0"]))
    linhas: list[list[dict]] = []
    linha_atual: list[dict] = []
    top_atual = None
    for palavra in palavras:
        if top_atual is None or abs(palavra["top"] - top_atual) <= 2.5:
            linha_atual.append(palavra)
            top_atual = palavra["top"] if top_atual is None else top_atual
        else:
            linhas.append(linha_atual)
            linha_atual = [palavra]
            top_atual = palavra["top"]
    if linha_atual:
        linhas.append(linha_atual)
    return [" ".join(p["text"] for p in sorted(l, key=lambda p: p["x0"])) for l in linhas]


@dataclass
class _ContextoAtual:
    orgao_codigo: str | None = None
    unidade_orc_codigo: str | None = None
    funcao: str | None = None
    subfuncao: str | None = None
    programa: str | None = None
    acao: str | None = None
    acao_nome_partes: list[str] = field(default_factory=list)
    categoria: str | None = None
    grupo: str | None = None
    modalidade: str | None = None
    elemento: str | None = None
    subelemento: str | None = None
    aguardando_funcao: bool = False
    aguardando_continuacao_acao: bool = False


class FichasDespesaASPECParser(ParserBase):
    tipo_relatorio = "FICHAS_DESPESA"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        resultado = ResultadoParsing()
        ctx = _ContextoAtual()

        with pdfplumber.open(caminho_arquivo) as pdf:
            for pagina in pdf.pages:
                for texto in _agrupar_linhas(pagina):
                    texto = texto.strip()
                    if not texto or RE_SOMENTE_SEPARADOR.match(texto):
                        continue
                    if any(texto.upper().startswith(h) for h in LINHAS_CABECALHO_IGNORAR):
                        continue

                    m_fonte = RE_FONTE.match(texto)
                    if m_fonte:
                        ctx.aguardando_continuacao_acao = False
                        if not (ctx.elemento and ctx.acao and ctx.unidade_orc_codigo):
                            resultado.avisos.append(f"Linha de origem sem contexto completo: {texto!r}")
                            continue
                        fonte_codigo, _fonte_nome, origem_texto = m_fonte.groups()
                        resultado.linhas.append({
                            "orgao_codigo": ctx.orgao_codigo,
                            "unidade_orc_codigo": ctx.unidade_orc_codigo,
                            "funcao": ctx.funcao,
                            "subfuncao": ctx.subfuncao,
                            "programa": ctx.programa,
                            "acao": ctx.acao,
                            "categoria_economica": ctx.categoria,
                            "grupo_natureza_despesa": ctx.grupo,
                            "modalidade_aplicacao": ctx.modalidade,
                            "elemento_despesa": ctx.elemento,
                            "subelemento": ctx.subelemento,
                            "fonte_codigo": fonte_codigo.zfill(8),
                            "origem": ORIGEM_MAP.get(origem_texto.lower(), ""),
                        })
                        continue

                    m_elemento = RE_ELEMENTO.match(texto)
                    if m_elemento:
                        ctx.aguardando_continuacao_acao = False
                        cat, grp, mod, elem, sub, _nome = m_elemento.groups()
                        ctx.categoria, ctx.grupo, ctx.modalidade = cat, grp, mod
                        ctx.elemento, ctx.subelemento = elem, sub
                        continue

                    m_acao = RE_ACAO.match(texto)
                    if m_acao:
                        func, subf, prog, acao_pontuada, nome = m_acao.groups()
                        ctx.funcao, ctx.subfuncao, ctx.programa = func, subf, prog
                        ctx.acao = acao_pontuada.replace(".", "")
                        ctx.acao_nome_partes = [nome]
                        ctx.categoria = ctx.grupo = ctx.modalidade = ctx.elemento = ctx.subelemento = None
                        ctx.aguardando_funcao = False
                        ctx.aguardando_continuacao_acao = True
                        continue

                    if ctx.aguardando_continuacao_acao:
                        # Nome da ação quebrado em mais de uma linha — não é um erro de
                        # parsing, não gera aviso (ver nota no topo do arquivo).
                        ctx.acao_nome_partes.append(texto)
                        continue

                    m_programa = RE_PROGRAMA.match(texto)
                    if m_programa:
                        func, subf, prog, _nome = m_programa.groups()
                        ctx.funcao, ctx.subfuncao, ctx.programa = func, subf, prog
                        ctx.acao = None
                        ctx.aguardando_funcao = False
                        continue

                    m_subfuncao = RE_SUBFUNCAO.match(texto)
                    if m_subfuncao:
                        func, subf, _nome = m_subfuncao.groups()
                        ctx.funcao, ctx.subfuncao = func, subf
                        ctx.aguardando_funcao = False
                        continue

                    m_unidade = RE_UNIDADE.match(texto)
                    if m_unidade:
                        orgao_cod, unid_cod, _nome = m_unidade.groups()
                        ctx.orgao_codigo, ctx.unidade_orc_codigo = orgao_cod, unid_cod
                        ctx.aguardando_funcao = True
                        continue

                    m_org_func = RE_ORGAO_OU_FUNCAO.match(texto)
                    if m_org_func:
                        codigo, _nome = m_org_func.groups()
                        if ctx.aguardando_funcao:
                            ctx.funcao = codigo
                            ctx.aguardando_funcao = False
                        else:
                            # Novo órgão: alguns (ex.: "28 Encargos Especiais") não têm
                            # nenhuma linha de unidade orçamentária própria neste
                            # relatório — zera para não herdar por engano a unidade do
                            # órgão anterior (e virar um aviso claro, não um código
                            # errado) se uma linha de função/fonte aparecer sem uma
                            # unidade ter sido definida para este órgão.
                            ctx.orgao_codigo = codigo
                            ctx.unidade_orc_codigo = None
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "FICHAS_DESPESA"): FichasDespesaASPECParser,
}
