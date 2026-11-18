"""
Parser para "DEMONSTRATIVO DOS RESTOS A PAGAR POR FONTE DE RECURSOS" do
ASPEC (`RP01.PDF`..`RP09.PDF`) — um PDF por mês, cobrindo TODAS as
Unidades Gestoras num único arquivo (diferente dos relatórios de saldo,
que são um PDF por UG).

Layout: uma seção por UG (nome na linha 3 de cada página, repetido em
toda página daquela UG, uma UG pode ocupar várias páginas seguidas), com
blocos por fonte dentro de cada seção:

    Fonte de recurso 15000000 -Recursos não vinculados de impostos
    2020 01090050 0,00 8.400,00 0,00 0,00 0,00 0,00 0,00
    ...
    Total da fonte 1.000.740,17 43.540,00 0,00 0,00 0,00 1.000.740,17 0,00

O prefixo "Fonte de recurso " só aparece no primeiro bloco de cada seção
de UG — blocos seguintes vêm só "<código> -<nome>"; o regex trata o
prefixo como opcional.

**A seção final "Consolidado"** (mesma posição de nome de UG, várias
páginas) é a re-agregação de todas as UGs já lidas — o parser para de
processar inteiramente qualquer página cujo nome de UG seja "Consolidado"
(nunca tratada como UG real; ver `RestoAPagar` para a validação que
confirmou isso).

Cada linha é um empenho de exercício ANTERIOR ao corrente (2020-2025 nos
arquivos vistos) — não tem relação com `Empenho` (apps.orcamento), cujos
registros começam em 2026, então "exercício" e "número do empenho" ficam
como dados próprios do resultado, não uma referência a resolver aqui.

O mês de referência vem do cabeçalho ("Mês de `<Nome>`/`<ano>`"), nunca do
nome do arquivo — mesma disciplina já usada em `aspec_empenhos.py` e
`aspec_execucao_receita.py`.
"""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .aspec import MESES
from .base import ParserBase, ResultadoParsing

RE_MES_UNICO = re.compile(r"M[êe]s de (\w+)/(\d{4})", re.IGNORECASE)
RE_FONTE = re.compile(r"^(?:Fonte de recurso\s+)?(\d{8})\s*-(.+)$")
RE_LINHA = re.compile(
    r"^(\d{4})\s+(\d+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s*$"
)

PREFIXOS_IGNORADOS = (
    "Pará", "Governo", "Prefeitura", "Camara", "Câmara", "Fundo",
    "DEMONSTRATIVO", "NúmeroInscrição", "ExercícioEmpenho", "TotaldaFonte", "Totaldafonte", "Totalgeral",
)


def _para_decimal(valor_texto: str) -> Decimal:
    try:
        return Decimal(valor_texto.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return Decimal("0")


def _ignorar(texto: str) -> bool:
    if not texto:
        return True
    sem_espacos = texto.replace(" ", "")
    if sem_espacos.startswith(PREFIXOS_IGNORADOS):
        return True
    return set(texto) <= {"-"}


class RestosAPagarASPECParser(ParserBase):
    tipo_relatorio = "RESTOS_A_PAGAR"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        import pdfplumber

        resultado = ResultadoParsing()
        mes_referencia: int | None = None
        unidade_gestora_nome: str | None = None
        bloco_atual: dict | None = None

        with pdfplumber.open(caminho_arquivo) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text() or ""
                linhas_pagina = texto_pagina.split("\n")

                if mes_referencia is None:
                    m_mes = RE_MES_UNICO.search(texto_pagina)
                    if m_mes:
                        mes_referencia = MESES.get(m_mes.group(1).upper())

                nome_ug_pagina = linhas_pagina[2].strip() if len(linhas_pagina) > 2 else None
                if nome_ug_pagina == "Consolidado":
                    continue
                if nome_ug_pagina:
                    unidade_gestora_nome = nome_ug_pagina

                for linha in linhas_pagina:
                    texto = linha.strip()
                    if _ignorar(texto):
                        continue

                    m_fonte = RE_FONTE.match(texto)
                    if m_fonte:
                        bloco_atual = {"fonte_codigo": m_fonte.group(1), "fonte_nome": m_fonte.group(2).strip()}
                        continue

                    m_linha = RE_LINHA.match(texto)
                    if m_linha and bloco_atual is not None and unidade_gestora_nome is not None:
                        exercicio, numero, insc_proc, insc_nao_proc, reinsc, cancel, liq, rpp, rpnp = m_linha.groups()
                        resultado.linhas.append({
                            "unidade_gestora_nome": unidade_gestora_nome,
                            "fonte_codigo": bloco_atual["fonte_codigo"],
                            "fonte_nome": bloco_atual["fonte_nome"],
                            "exercicio_origem": int(exercicio),
                            "numero_empenho": numero,
                            "inscricao_processada": _para_decimal(insc_proc),
                            "inscricao_nao_processada": _para_decimal(insc_nao_proc),
                            "reinscricao": _para_decimal(reinsc),
                            "cancelamento": _para_decimal(cancel),
                            "liquidacao": _para_decimal(liq),
                            "rpp_pago": _para_decimal(rpp),
                            "rpnp_pago": _para_decimal(rpnp),
                        })
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        if mes_referencia is None:
            resultado.avisos.append("Mês de referência não identificado pelo cabeçalho.")
        resultado.metadados["mes_referencia"] = mes_referencia

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "RESTOS_A_PAGAR"): RestosAPagarASPECParser,
}
