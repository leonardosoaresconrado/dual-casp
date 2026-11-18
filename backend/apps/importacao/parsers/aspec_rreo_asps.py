"""
Parser para o RREO-Anexo XII (LC 141/2012, art.35) — Demonstrativo das
Receitas e Despesas com Ações e Serviços Públicos de Saúde (ASPS) — um
PDF por bimestre em `DADOS/FISCAL/EXECUÇÃO FISCAL/<bimestre>/`, nomeação
inconsistente entre pastas (`RREO121.PDF`, `RRE8122.PDF`, ...) — bimestre
e exercício vêm do cabeçalho do próprio relatório, nunca do nome do
arquivo.

Só a seção final de apuração do índice é extraída (receita-base, mínimo
de 15%, despesa aplicada e o percentual final) — as páginas anteriores
com o detalhamento por subfunção (Atenção Básica, Vigilância Sanitária
etc.) não são necessárias para o índice em si, mesmo nível de
granularidade usado pela planilha de controle do cliente.

A maioria das linhas úteis é tabular, delimitada por "|" (mesmo estilo
ASPEC de todos os outros relatórios deste projeto), mas a seção final de
apuração (a partir de "Despesa Mínima a ser Aplicada em ASPS") imprime
"rótulo valor" numa linha só, sem "|" — tratada separadamente.
"""

import math
import re
from pathlib import Path

import pdfplumber

from .aspec import MESES
from .base import ParserBase, ResultadoParsing

RE_BIMESTRE_ANO = re.compile(r"(\d)\s*[ºo]\s*bimestre\s*de\s*(\d{4})", re.IGNORECASE)
RE_MES_FINAL = re.compile(r"\(\s*\w+\s+a\s+(\w+)(?:/(\d{4}))?\s*\)", re.IGNORECASE)
RE_ANO = re.compile(r"(20\d{2})")
RE_NUMERO_FINAL = re.compile(r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$")


def _para_decimal(texto: str) -> str:
    return texto.replace(".", "").replace(",", ".").strip()


def _valores_da_linha(linha: str) -> list[str]:
    return [p.strip() for p in linha.split("|")][1:]


def _periodo(linhas_cabecalho: list[str]) -> tuple[int | None, int | None]:
    for linha in linhas_cabecalho:
        m = RE_BIMESTRE_ANO.search(linha)
        if m:
            return int(m.group(1)), int(m.group(2))
    for linha in linhas_cabecalho:
        m = RE_MES_FINAL.search(linha)
        if m:
            mes_num = MESES.get(m.group(1).upper())
            if not mes_num:
                continue
            anos = RE_ANO.findall(linha)
            ano = max(int(a) for a in anos) if anos else None
            return math.ceil(mes_num / 2), ano
    return None, None


class RREOASPSASPECParser(ParserBase):
    tipo_relatorio = "RREO_ASPS"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        resultado = ResultadoParsing()
        linha_final: dict = {}

        with pdfplumber.open(caminho_arquivo) as pdf:
            texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

        linhas = texto_completo.split("\n")
        bimestre, exercicio = _periodo(linhas[:6])

        minimo_ja_capturado = False
        for linha in linhas:
            if "TOTAL DAS RECEITAS RESULTANTES DE IMPOSTOS E TRANSFER" in linha and "(III)" in linha:
                valores = _valores_da_linha(linha)
                linha_final["receita_impostos_transferencias"] = _para_decimal(valores[2])
                linha_final["base_calculo"] = _para_decimal(valores[2])
                continue
            if "VALOR APLICADO EM ASPS (XVI)" in linha:
                valores = _valores_da_linha(linha)
                linha_final["despesa_asps_empenhada"] = _para_decimal(valores[0])
                linha_final["despesa_asps_liquidada"] = _para_decimal(valores[1])
                if len(valores) >= 3:
                    linha_final["despesa_asps_paga"] = _para_decimal(valores[2])
                continue
            if "Despesa M" in linha and "ser Aplicada em ASPS (XVII)" in linha and not minimo_ja_capturado:
                m = RE_NUMERO_FINAL.search(linha)
                if m:
                    linha_final["minimo_constitucional"] = _para_decimal(m.group(1))
                    minimo_ja_capturado = True
                continue
            if "PERCENTUAL DA RECEITA DE IMPOSTOS" in linha and "APLICADO EM ASPS" in linha:
                m = RE_NUMERO_FINAL.search(linha)
                if m:
                    linha_final["percentual_aplicado"] = _para_decimal(m.group(1))
                continue

        linha_final.setdefault("despesa_asps_paga", "0")

        if bimestre is None or exercicio is None:
            resultado.avisos.append("Período (bimestre/exercício) não identificado no cabeçalho do relatório.")
        campos_esperados = [
            "receita_impostos_transferencias", "base_calculo", "minimo_constitucional",
            "despesa_asps_empenhada", "despesa_asps_liquidada", "despesa_asps_paga", "percentual_aplicado",
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
    ("ASPEC", "RREO_ASPS"): RREOASPSASPECParser,
}
