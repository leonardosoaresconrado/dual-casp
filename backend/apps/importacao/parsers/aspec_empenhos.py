"""
Parser para o "Relatório para conferência dos empenhos" exportado pelo
sistema ASPEC em planilha.

Apesar da extensão .ods, o arquivo real é um documento binário legado
(OLE2/Compound File, o mesmo formato de .xls antigo) — não um OpenDocument
de verdade. Por isso é lido com pandas (engine automático via assinatura do
arquivo, não pela extensão), e não com odfpy.

Cada linha é a MOVIMENTAÇÃO de um empenho NUM MÊS (não um total acumulado):
o ASPEC exporta uma planilha por mês, e quando um empenho de um mês
anterior ainda tem atividade (liquidação/pagamento), ele reaparece na
planilha do mês seguinte com "Valor empenho" geralmente zerado (nenhum
empenhamento novo) e "Valor liquidado"/"Valor pago" só com o que se moveu
NAQUELE mês — não repete o acumulado. Tratar esses valores como snapshot
acumulado (em vez de somar as aparições de cada número de empenho ao longo
dos meses) já causou uma corrupção de dados real nesta base; ver
`services.importar_empenhos`/`Empenho`/`EmpenhoMovimento`, que somam as
aparições em vez de sobrescrever.

O mês de referência de cada linha é o mês do RELATÓRIO/ARQUIVO (cabeçalho
"Mês de <Nome>/<ano>", linha 5 da planilha), não o mês da "Data Empenho" da
linha — "Data Empenho" é a data de abertura original do empenho e não muda
quando ele reaparece num arquivo de mês seguinte, então usá-la como mês de
referência faz linhas de meses diferentes colidirem na mesma chave
(empenho, mês) e se sobrescreverem em vez de somarem (outro bug real já
cometido aqui). Se o cabeçalho não casar com "Mês de <nome>/<ano>" (ex.:
um arquivo consolidado de vários meses, formato antigo), cai de volta para
derivar por linha a partir da "Data Empenho" — correto nesse caso porque
esse formato antigo tem uma única linha por empenho (sem reaparição).

Já traz a classificação orçamentária completa (órgão/unidade orçamentária,
função/subfunção/programa/ação, classificação econômica, fonte de
recursos) — a mesma classificação que já existe em RubricaOrcamentaria a
partir do balancete mensal (ver aspec.py).
"""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from .aspec import MESES
from .base import ParserBase, ResultadoParsing

RE_MES_UNICO = re.compile(r"M[êe]s de (\w+)/(\d{4})", re.IGNORECASE)

COLUNAS = [
    "orgao_unidade", "programatica", "classificacao_economica", "fonte",
    "evento", "subconta", "data_empenho", "numero_empenho",
    "entra_calc_educacao", "entra_calc_fundeb", "entra_calc_magisterio", "entra_calc_saude",
    "destinacao_especifica", "valor_empenho", "valor_liquidado", "valor_pago",
    "credor", "historico",
]

RE_ORGAO_UNIDADE = re.compile(r"^\s*(\d{2})\s+(\d{2})\.?\s*$")
RE_PROGRAMATICA = re.compile(r"^\s*(\d{2})\s+(\d{3})\s+(\d{4})\s+(\d\.\d{3})\s*-\s*(.+?)\s*$")
RE_CLASSIFICACAO = re.compile(r"^\s*(\d)\.(\d)\.(\d{2})\.(\d{2})\.(\d{2})\s*-\s*(.+?)\s*$")
RE_FONTE = re.compile(r"^\s*(\d+)\s*-\s*(.+?)\s*$")


def _para_decimal(valor) -> Decimal:
    try:
        return Decimal(str(valor))
    except InvalidOperation:
        return Decimal("0")


class EmpenhosASPECParser(ParserBase):
    tipo_relatorio = "EXECUCAO_ORCAMENTARIA"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        bruto = pd.read_excel(caminho_arquivo, header=None)
        m_mes = RE_MES_UNICO.search(str(bruto.iloc[4, 0]))
        mes_referencia_arquivo = MESES.get(m_mes.group(1).upper()) if m_mes else None

        df = bruto.iloc[6:].reset_index(drop=True)
        df.columns = COLUNAS[: len(df.columns)]
        df = df.dropna(subset=["data_empenho", "numero_empenho"])

        resultado = ResultadoParsing(metadados={"mes_referencia_arquivo": mes_referencia_arquivo})

        for _, linha in df.iterrows():
            m_orgao = RE_ORGAO_UNIDADE.match(str(linha["orgao_unidade"]))
            m_prog = RE_PROGRAMATICA.match(str(linha["programatica"]))
            m_classif = RE_CLASSIFICACAO.match(str(linha["classificacao_economica"]))
            m_fonte = RE_FONTE.match(str(linha["fonte"]))

            if not (m_orgao and m_prog and m_classif and m_fonte):
                resultado.avisos.append(f"Linha não reconhecida: {linha.to_dict()!r}")
                continue

            orgao_codigo, unidade_orc_codigo = m_orgao.groups()
            funcao, subfuncao, programa, acao_pontuada, acao_nome = m_prog.groups()
            categoria, grupo, modalidade, elemento, subelemento, elemento_nome = m_classif.groups()
            fonte_codigo, fonte_nome = m_fonte.groups()

            try:
                data_empenho = pd.to_datetime(linha["data_empenho"], dayfirst=True).date()
            except (ValueError, TypeError):
                resultado.avisos.append(f"Data de empenho inválida: {linha['data_empenho']!r}")
                continue

            resultado.linhas.append({
                "orgao_codigo": orgao_codigo,
                "unidade_orc_codigo": unidade_orc_codigo,
                "funcao": funcao,
                "subfuncao": subfuncao,
                "programa": programa,
                "acao": acao_pontuada.replace(".", ""),
                "acao_nome": acao_nome,
                "categoria_economica": categoria,
                "grupo_natureza_despesa": grupo,
                "modalidade_aplicacao": modalidade,
                "elemento_despesa": elemento,
                "subelemento": subelemento,
                "elemento_nome": elemento_nome,
                "fonte_codigo": fonte_codigo.zfill(8),
                "fonte_nome": fonte_nome,
                "numero_empenho": str(linha["numero_empenho"]),
                "data_empenho": data_empenho,
                "mes_referencia": mes_referencia_arquivo or data_empenho.month,
                "valor_empenho": _para_decimal(linha["valor_empenho"]),
                "valor_liquidado": _para_decimal(linha["valor_liquidado"]),
                "valor_pago": _para_decimal(linha["valor_pago"]),
                "credor": str(linha["credor"]).strip() if pd.notna(linha["credor"]) else "",
                "historico": str(linha["historico"]).strip() if pd.notna(linha["historico"]) else "",
            })

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "EMPENHOS"): EmpenhosASPECParser,
}
