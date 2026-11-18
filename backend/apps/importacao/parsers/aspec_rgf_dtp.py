"""
Parser para o RGF-Anexo 1 (LRF, art.55, inciso I, alínea 'a') — Demonstrativo
da Despesa com Pessoal — um PDF por bimestre em
`DADOS/FISCAL/EXECUÇÃO FISCAL/<bimestre>/`, nomeação inconsistente entre
pastas (`RGF11.PDF`, `RGF35.PDF`, ...) — o bimestre e o exercício vêm do
cabeçalho do próprio relatório, nunca do nome do arquivo.

Só a seção final "APURAÇÃO DO CUMPRIMENTO DO LIMITE LEGAL" é extraída — é
o que alimenta o índice DTP (Despesa Total com Pessoal) acompanhado pela
planilha de controle do cliente; as 9 páginas de detalhamento mensal que a
precedem (execução por mês dos últimos 12 meses) não são necessárias para
o índice em si.

O cabeçalho do período aparece em formatos diferentes conforme o
bimestre (`"Novembro/2024 a Fevereiro/2025 (até Fevereiro)"`,
`"1º quadrimestre de 2025 (até Abril)"`, `"Março a Junho/2025 (até
Junho)"`) — em vez de tentar casar cada variação, o bimestre é derivado
do nome do mês dentro do "(até <mês>)" via `ceil(mês/2)` (Fevereiro→1,
Abril→2, ..., Dezembro→6), que vale para qualquer frase de período desde
que termine nesse padrão.
"""

import math
import re
from pathlib import Path

import pdfplumber

from .aspec import MESES
from .base import ParserBase, ResultadoParsing

RE_PERIODO = re.compile(r"at[ée]\s+(\w+)\)", re.IGNORECASE)
RE_ANO = re.compile(r"(20\d{2})")


def _para_decimal(texto: str) -> str:
    return texto.replace(".", "").replace(",", ".").strip()


def _valores_da_linha(linha: str) -> list[str]:
    return [p.strip() for p in linha.split("|")][1:]


class RGFDTPASPECParser(ParserBase):
    tipo_relatorio = "RGF_DTP"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        resultado = ResultadoParsing()
        linha_final: dict = {}
        bimestre = None
        exercicio = None
        somando_deducoes = False

        with pdfplumber.open(caminho_arquivo) as pdf:
            texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

        linhas = texto_completo.split("\n")

        for i, linha in enumerate(linhas[:6]):
            m_periodo = RE_PERIODO.search(linha)
            if m_periodo:
                nome_mes = m_periodo.group(1).upper()
                mes_num = MESES.get(nome_mes)
                if mes_num:
                    bimestre = math.ceil(mes_num / 2)
                anos = RE_ANO.findall(linha)
                if anos:
                    # linhas como "Novembro/2024 a Fevereiro/2025" trazem dois
                    # anos — o exercício é sempre o mais recente (o mês de
                    # fechamento do período, não o início).
                    exercicio = max(int(a) for a in anos)

        for linha in linhas:
            if "RCL(IV)" in linha and "AJUSTADA" not in linha:
                valores = _valores_da_linha(linha)
                linha_final["rcl"] = _para_decimal(valores[0])
                somando_deducoes = True
                continue
            if somando_deducoes and linha.strip().startswith("(-)"):
                valores = _valores_da_linha(linha)
                if "emendas individuais" in linha.lower():
                    linha_final["deducao_emendas_individuais"] = _para_decimal(valores[0])
                elif "emendas de bancada" in linha.lower():
                    linha_final["deducao_emendas_bancada"] = _para_decimal(valores[0])
                elif "agentes comun" in linha.lower():
                    linha_final["deducao_agentes_saude"] = _para_decimal(valores[0])
                elif "outras dedu" in linha.lower():
                    linha_final["deducao_outras"] = _para_decimal(valores[0])
                continue
            if "AJUSTADA PARA C" in linha and "(V)" in linha:
                somando_deducoes = False
                valores = _valores_da_linha(linha)
                linha_final["rcl_ajustada"] = _para_decimal(valores[0])
                continue
            if "DESPESA TOTAL COM PESSOAL" in linha and "(VI)" in linha:
                valores = _valores_da_linha(linha)
                linha_final["despesa_total_pessoal"] = _para_decimal(valores[0])
                linha_final["percentual_dtp"] = _para_decimal(valores[1].replace("%", ""))
                continue
            if "LIMITE M" in linha and "(VII)" in linha:
                valores = _valores_da_linha(linha)
                linha_final["limite_maximo_valor"] = _para_decimal(valores[0])
                linha_final["limite_maximo_percentual"] = _para_decimal(valores[1].replace("%", ""))
                continue
            if "LIMITE PRUDENCIAL" in linha and "(VIII)" in linha:
                valores = _valores_da_linha(linha)
                linha_final["limite_prudencial_valor"] = _para_decimal(valores[0])
                linha_final["limite_prudencial_percentual"] = _para_decimal(valores[1].replace("%", ""))
                continue
            if "LIMITE DE ALERTA" in linha and "(IX)" in linha:
                valores = _valores_da_linha(linha)
                linha_final["limite_alerta_valor"] = _para_decimal(valores[0])
                linha_final["limite_alerta_percentual"] = _para_decimal(valores[1].replace("%", ""))
                continue

        for campo in ("deducao_emendas_individuais", "deducao_emendas_bancada", "deducao_agentes_saude", "deducao_outras"):
            linha_final.setdefault(campo, "0")

        if bimestre is None or exercicio is None:
            resultado.avisos.append("Período (bimestre/exercício) não identificado no cabeçalho do relatório.")
        campos_esperados = [
            "rcl", "rcl_ajustada", "despesa_total_pessoal", "percentual_dtp",
            "limite_maximo_valor", "limite_maximo_percentual",
            "limite_prudencial_valor", "limite_prudencial_percentual",
            "limite_alerta_valor", "limite_alerta_percentual",
        ]
        faltando = [c for c in campos_esperados if c not in linha_final]
        if faltando:
            resultado.avisos.append(f"Campos não encontrados na seção de apuração: {faltando}")
        else:
            linha_final["bimestre"] = bimestre
            linha_final["exercicio"] = exercicio
            resultado.linhas.append(linha_final)

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "RGF_DTP"): RGFDTPASPECParser,
}
