"""
Parser para o "Movimentos de Despesa Fixada" exportado em PDF pelo ASPEC —
é a LOA com valores: cada combinação de órgão/unidade orçamentária,
classificação funcional/programática, classificação econômica e fonte de
recursos aparece com a dotação fixada (data, valor, número da lei).

No arquivo de amostra (2026), todas as linhas citam a mesma data
(02/01/2026) e a mesma lei (00772/25) — a lei que institui a própria LOA.
Ou seja, este relatório é a fixação ORIGINAL da LOA, não um histórico de
créditos adicionais ao longo do ano (créditos adicionais, quando
existirem, chegam por outro caminho — ver `services.importar_empenhos`,
que cria uma RubricaOrcamentaria nova com origem=CREDITO_ADICIONAL sempre
que uma classificação do relatório de empenhos não foi prevista aqui).
Se uma mesma fonte tiver mais de uma linha data/valor/lei, os valores são
somados (o parser não assume uma única linha por fonte).

Mesma estrutura de página-com-cabeçalho-repetido do aspec.py (balancete);
reaproveita a mesma técnica de agrupar palavras em linhas por coordenada
vertical e descartar cabeçalho/separadores de cada página.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from .base import ParserBase, ResultadoParsing

RE_SOMENTE_SEPARADOR = re.compile(r"^[_\s]+$")
RE_ORGAO_UNIDADE = re.compile(r"^(\d{2})\s+(\d{2})\.\s*$")
RE_ACAO = re.compile(r"^(\d{2})\s+(\d{3})\s+(\d{4})\s+(\d\.\d{3})\s+(.+?)\s*$")
RE_ELEMENTO = re.compile(r"^(\d)\.(\d)\.(\d{2})\.(\d{2})\.(\d{2})\s+(.+?)\s*$")
RE_FONTE = re.compile(r"^(\d{8})\s+(.+?)\s*$")
RE_VALOR = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+R\$\s*([\d.,]+)\s+(\S+)\s*$")
RE_TOTAL = re.compile(r"^TOTAL\s", re.IGNORECASE)
RE_EXERCICIO = re.compile(r"Exerc[ií]cio de (\d{4})", re.IGNORECASE)

LINHAS_CABECALHO_IGNORAR = (
    "PARÁ",
    "GOVERNO MUNICIPAL DE",
    "CONSOLIDADO",
    "DOTAÇÃO",
)


def _para_decimal(valor_str: str) -> Decimal:
    limpo = valor_str.replace(".", "").replace(",", ".")
    try:
        return Decimal(limpo)
    except InvalidOperation:
        return Decimal("0")


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
    acao_nome: str | None = None
    categoria: str | None = None
    grupo: str | None = None
    modalidade: str | None = None
    elemento: str | None = None
    subelemento: str | None = None
    fonte_codigo: str | None = None
    fonte_nome: str | None = None


class LOADespesasASPECParser(ParserBase):
    tipo_relatorio = "LOA_DESPESAS"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        resultado = ResultadoParsing()
        ctx = _ContextoAtual()
        acumulador_fonte: dict[tuple, Decimal] = {}

        def _descarregar_fonte():
            if ctx.fonte_codigo is None:
                return
            chave = (
                ctx.orgao_codigo, ctx.unidade_orc_codigo, ctx.funcao, ctx.subfuncao,
                ctx.programa, ctx.acao, ctx.categoria, ctx.grupo, ctx.modalidade,
                ctx.elemento, ctx.subelemento, ctx.fonte_codigo,
            )
            valor = acumulador_fonte.pop(chave, None)
            if valor is None:
                return
            resultado.linhas.append({
                "orgao_codigo": ctx.orgao_codigo,
                "unidade_orc_codigo": ctx.unidade_orc_codigo,
                "funcao": ctx.funcao,
                "subfuncao": ctx.subfuncao,
                "programa": ctx.programa,
                "acao": ctx.acao,
                "acao_nome": ctx.acao_nome,
                "categoria_economica": ctx.categoria,
                "grupo_natureza_despesa": ctx.grupo,
                "modalidade_aplicacao": ctx.modalidade,
                "elemento_despesa": ctx.elemento,
                "subelemento": ctx.subelemento,
                "fonte_codigo": ctx.fonte_codigo,
                "fonte_nome": ctx.fonte_nome,
                "valor": valor,
            })

        with pdfplumber.open(caminho_arquivo) as pdf:
            for indice_pagina, pagina in enumerate(pdf.pages):
                linhas_pagina = _agrupar_linhas(pagina)
                if indice_pagina == 0:
                    m_exercicio = RE_EXERCICIO.search("\n".join(linhas_pagina))
                    if m_exercicio:
                        resultado.metadados["ano"] = int(m_exercicio.group(1))

                for texto in linhas_pagina:
                    texto = texto.strip()
                    if not texto or RE_SOMENTE_SEPARADOR.match(texto):
                        continue
                    if any(texto.upper().startswith(h) for h in LINHAS_CABECALHO_IGNORAR):
                        continue
                    if RE_TOTAL.match(texto):
                        continue

                    m_valor = RE_VALOR.match(texto)
                    if m_valor:
                        if not (ctx.fonte_codigo and ctx.elemento and ctx.acao):
                            resultado.avisos.append(f"Linha de valor sem contexto completo: {texto!r}")
                            continue
                        _, valor_texto, _lei = m_valor.groups()
                        chave = (
                            ctx.orgao_codigo, ctx.unidade_orc_codigo, ctx.funcao, ctx.subfuncao,
                            ctx.programa, ctx.acao, ctx.categoria, ctx.grupo, ctx.modalidade,
                            ctx.elemento, ctx.subelemento, ctx.fonte_codigo,
                        )
                        acumulador_fonte[chave] = acumulador_fonte.get(chave, Decimal("0")) + _para_decimal(valor_texto)
                        continue

                    m_fonte = RE_FONTE.match(texto)
                    if m_fonte:
                        _descarregar_fonte()
                        ctx.fonte_codigo, ctx.fonte_nome = m_fonte.groups()
                        continue

                    m_elemento = RE_ELEMENTO.match(texto)
                    if m_elemento:
                        _descarregar_fonte()
                        cat, grp, mod, elem, sub, _nome = m_elemento.groups()
                        ctx.categoria, ctx.grupo, ctx.modalidade = cat, grp, mod
                        ctx.elemento, ctx.subelemento = elem, sub
                        ctx.fonte_codigo = ctx.fonte_nome = None
                        continue

                    m_acao = RE_ACAO.match(texto)
                    if m_acao:
                        _descarregar_fonte()
                        func, subf, prog, acao_pontuada, nome = m_acao.groups()
                        ctx.funcao, ctx.subfuncao, ctx.programa = func, subf, prog
                        ctx.acao = acao_pontuada.replace(".", "")
                        ctx.acao_nome = nome
                        ctx.categoria = ctx.grupo = ctx.modalidade = None
                        ctx.elemento = ctx.subelemento = None
                        ctx.fonte_codigo = ctx.fonte_nome = None
                        continue

                    m_unidade = RE_ORGAO_UNIDADE.match(texto)
                    if m_unidade:
                        _descarregar_fonte()
                        ctx.orgao_codigo, ctx.unidade_orc_codigo = m_unidade.groups()
                        continue

                    if not any(c.isdigit() for c in texto):
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        _descarregar_fonte()
        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "LOA_DESPESAS"): LOADespesasASPECParser,
}
