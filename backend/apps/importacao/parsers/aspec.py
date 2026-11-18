"""
Parser para o relatório "Demonstrativo Resumido da Despesa" (Movimento
Orçamentário) exportado em PDF pelo sistema ASPEC.

Layout do relatório (confirmado a partir de amostras reais):

  <código unidade orçamentária 4 díg.> <nome da unidade>
  <órgão 2> <unidade 2>. <função 2> <subfunção 3> <programa 4> <ação d.ddd> <nome da ação>
  <elemento d.d.dd.dd.dd> <nome do elemento>
  <fonte 8 dígitos espaçados>  FIXADA ADICIONAIS REDUÇÕES EMPENHADA SALDO LIQUIDADA PAGA
  ... (repete elementos) ...
  TOTAL <ação> <7 valores>
  ... (repete ações) ...
  TOTAL <unidade 4 díg.> <7 valores>
  ... (repete unidades/órgãos, cada um tipicamente começando em nova página) ...
  TOTAL ORÇAMENTÁRIO <7 valores>

Cada página reimprime um cabeçalho fixo (título, mês/ano, município,
cabeçalho de colunas) e um rodapé (data por extenso + assinaturas), que são
removidos antes da análise linha a linha.

O parser é agnóstico a UG/Órgão do nosso modelo de dados: ele apenas
reconhece a estrutura do PDF. A função `importar_execucao_orcamentaria`
(em apps/importacao/services.py) decide a qual UnidadeGestora cadastrada
o relatório pertence e grava os dados.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from .base import ParserBase, ResultadoParsing

MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6,
    "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12,
}

RE_CABECALHO_MES = re.compile(r"AT[ÉE]\s+(\w+)\s+DE\s+(\d{4})", re.IGNORECASE)
RE_MUNICIPIO = re.compile(r"Governo Municipal de (.+?)\s+MOVIMENTO OR", re.IGNORECASE)
RE_DATA_EXTENSO = re.compile(r"^.+,\s*\d{1,2}\s+de\s+\S+\s+de\s+\d{4}\.?$", re.IGNORECASE)
RE_SOMENTE_SEPARADOR = re.compile(r"^[-=\s]+$")
RE_ACAO = re.compile(
    r"^(\d{2})\s+(\d{2})\.\s+(\d{2})\s+(\d{3})\s+(\d{4})\s+(\d\.\d{3})\s+(.+)$"
)
RE_UNIDADE = re.compile(r"^(\d{4})\s+(.+)$")
RE_ELEMENTO = re.compile(r"^(\d\.\d\.\d{2}\.\d{2}\.\d{2})\s+(.+)$")
RE_TOTAL = re.compile(r"^TOTAL\s+(\S+)\s+(.+)$", re.IGNORECASE)
RE_VALOR = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}-?")

LINHAS_CABECALHO_IGNORAR = (
    "DEMONSTRATIVO RESUMIDO DA DESPESA",
    "MOVIMENTO ORÇAMENTÁRIO",
)


def _para_decimal(valor_str: str) -> Decimal:
    negativo = valor_str.endswith("-")
    limpo = valor_str.rstrip("-").replace(".", "").replace(",", ".")
    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        valor = Decimal("0")
    return -valor if negativo else valor


def _agrupar_linhas(pagina) -> list[list[dict]]:
    """Agrupa as palavras de uma página em linhas, pela coordenada vertical."""
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
    return linhas


def _texto_linha(linha: list[dict]) -> str:
    return " ".join(p["text"] for p in sorted(linha, key=lambda p: p["x0"]))


def _e_linha_fonte_valores(linha: list[dict]) -> bool:
    palavras = sorted(linha, key=lambda p: p["x0"])
    if len(palavras) < 9:
        return False
    primeiros_8 = palavras[:8]
    return all(re.fullmatch(r"\d", p["text"]) for p in primeiros_8)


def _extrair_fonte_e_valores(linha: list[dict]) -> tuple[str, list[Decimal]]:
    palavras = sorted(linha, key=lambda p: p["x0"])
    fonte = "".join(p["text"] for p in palavras[:8])
    valores_texto = [p["text"] for p in palavras[8:] if RE_VALOR.fullmatch(p["text"])]
    valores = [_para_decimal(v) for v in valores_texto]
    return fonte, valores


@dataclass
class _Totalizador:
    nivel: str
    codigo: str
    valores: list[Decimal]


def _extrair_linhas_conteudo(caminho_arquivo) -> tuple[list[tuple[str, list[dict]]], list[_Totalizador], dict]:
    """
    Retorna (linhas_conteudo, totalizadores, metadados).
    linhas_conteudo: lista de (texto, palavras) já sem cabeçalho/rodapé de página.
    """
    linhas_conteudo: list[tuple[str, list[dict]]] = []
    totalizadores: list[_Totalizador] = []
    metadados: dict = {}

    with pdfplumber.open(caminho_arquivo) as pdf:
        for indice_pagina, pagina in enumerate(pdf.pages):
            linhas = _agrupar_linhas(pagina)
            textos = [_texto_linha(l) for l in linhas]

            if indice_pagina == 0:
                texto_completo = "\n".join(textos)
                m_mes = RE_CABECALHO_MES.search(texto_completo)
                if m_mes:
                    nome_mes = m_mes.group(1).upper().replace("Ç", "Ç")
                    metadados["mes_referencia"] = MESES.get(nome_mes)
                    metadados["ano"] = int(m_mes.group(2))
                m_mun = RE_MUNICIPIO.search(texto_completo)
                if m_mun:
                    metadados["municipio_nome"] = m_mun.group(1).strip()

            # localizar fim do cabeçalho de página (linha "CÓDIGO ...")
            idx_inicio = 0
            for i, t in enumerate(textos):
                if t.startswith("CÓDIGO"):
                    idx_inicio = i + 2  # pula a linha de separador logo abaixo
                    break

            # localizar início do rodapé (linha "Município, dd de mês de ano.")
            idx_fim = len(textos)
            for i in range(idx_inicio, len(textos)):
                if RE_DATA_EXTENSO.match(textos[i].strip()):
                    idx_fim = i
                    break

            for i in range(idx_inicio, idx_fim):
                texto = textos[i].strip()
                if not texto or RE_SOMENTE_SEPARADOR.match(texto):
                    continue
                if any(texto.upper().startswith(h) for h in LINHAS_CABECALHO_IGNORAR):
                    continue

                m_total = RE_TOTAL.match(texto)
                if m_total:
                    valores = [_para_decimal(v) for v in RE_VALOR.findall(m_total.group(2))]
                    nivel = "GERAL" if not m_total.group(1)[0].isdigit() else (
                        "ACAO" if "." in m_total.group(1) else "UNIDADE"
                    )
                    totalizadores.append(_Totalizador(nivel, m_total.group(1), valores))
                    continue

                linhas_conteudo.append((texto, linhas[i]))

    return linhas_conteudo, totalizadores, metadados


class ExecucaoOrcamentariaASPECParser(ParserBase):
    tipo_relatorio = "EXECUCAO_ORCAMENTARIA"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        linhas_conteudo, totalizadores, metadados = _extrair_linhas_conteudo(caminho_arquivo)

        resultado = ResultadoParsing(metadados=metadados)

        unidade_codigo = unidade_nome = None
        funcao = subfuncao = programa = acao = acao_nome = None
        elemento_codigo = elemento_nome = None

        for texto, palavras in linhas_conteudo:
            m_acao = RE_ACAO.match(texto)
            if m_acao:
                _, _, funcao, subfuncao, programa, acao_pontuada, acao_nome = m_acao.groups()
                acao = acao_pontuada.replace(".", "")
                elemento_codigo = elemento_nome = None
                continue

            if _e_linha_fonte_valores(palavras):
                if not (elemento_codigo and unidade_codigo and acao):
                    resultado.avisos.append(f"Linha de valores sem contexto completo: {texto!r}")
                    continue
                fonte, valores = _extrair_fonte_e_valores(palavras)
                if len(valores) != 7:
                    resultado.avisos.append(f"Linha de valores com {len(valores)} valores (esperado 7): {texto!r}")
                    continue
                fixada, adicionais, reducoes, empenhada, saldo, liquidada, paga = valores
                resultado.linhas.append({
                    "unidade_codigo": unidade_codigo,
                    "unidade_nome": unidade_nome,
                    "funcao": funcao,
                    "subfuncao": subfuncao,
                    "programa": programa,
                    "acao": acao,
                    "acao_nome": acao_nome,
                    "elemento_codigo": elemento_codigo,
                    "elemento_nome": elemento_nome,
                    "fonte_recursos": fonte,
                    "dotacao_inicial": fixada,
                    "creditos_adicionais": adicionais,
                    "anulacoes": reducoes,
                    "empenhado_acumulado": empenhada,
                    "saldo_orcamentario": saldo,
                    "liquidado_acumulado": liquidada,
                    "pago_acumulado": paga,
                })
                continue

            m_elemento = RE_ELEMENTO.match(texto)
            if m_elemento:
                elemento_codigo, elemento_nome = m_elemento.groups()
                continue

            m_unidade = RE_UNIDADE.match(texto)
            if m_unidade:
                unidade_codigo, unidade_nome = m_unidade.groups()
                continue

            if not any(c.isdigit() for c in texto):
                # bloco de assinatura (nomes/cargos) remanescente em páginas sem
                # a linha "Município, dd de mês de ano." (páginas de preenchimento)
                continue

            resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        resultado.metadados["totalizadores"] = totalizadores
        self._validar_totais(resultado, totalizadores)
        return resultado

    @staticmethod
    def _validar_totais(resultado: ResultadoParsing, totalizadores: list[_Totalizador]) -> None:
        """Confere TOTAL <ação> contra a soma dos lançamentos daquela ação, como checagem de integridade."""
        from collections import defaultdict

        somas_por_acao: dict[str, list[Decimal]] = defaultdict(lambda: [Decimal("0")] * 6)
        for linha in resultado.linhas:
            chave = linha["acao"]
            somas_por_acao[chave][0] += linha["dotacao_inicial"]
            somas_por_acao[chave][1] += linha["creditos_adicionais"]
            somas_por_acao[chave][2] += linha["anulacoes"]
            somas_por_acao[chave][3] += linha["empenhado_acumulado"]
            somas_por_acao[chave][4] += linha["liquidado_acumulado"]
            somas_por_acao[chave][5] += linha["pago_acumulado"]

        for tot in totalizadores:
            if tot.nivel != "ACAO":
                continue
            codigo = tot.codigo.replace(".", "")
            soma = somas_por_acao.get(codigo)
            if soma is None or len(tot.valores) != 7:
                continue
            fixada, adicionais, reducoes, empenhada, _saldo, liquidada, paga = tot.valores
            esperado = [fixada, adicionais, reducoes, empenhada, liquidada, paga]
            if any(abs(a - b) > Decimal("0.01") for a, b in zip(esperado, soma)):
                resultado.avisos.append(
                    f"Divergência no total da ação {tot.codigo}: relatório={tot.valores} calculado={soma}"
                )


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "EXECUCAO_ORCAMENTARIA"): ExecucaoOrcamentariaASPECParser,
}
