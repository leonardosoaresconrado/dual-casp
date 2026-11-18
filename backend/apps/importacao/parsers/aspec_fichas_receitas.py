"""
Parser para "Classificação Econômica da Receita - Local" (FICHAS_RECEITAS.PDF)
exportado pelo ASPEC — a LOA de receita com valores, único catálogo de
receita disponível (cumpre para receita o papel que LOA_DESPESAS +
FICHAS.PDF cumprem juntos para despesa).

Layout por bloco (código de receita):
    <código> <nome>
    <SIGLA_UG> <valor> <nome da fonte>
    <valor> <nome da fonte>           (linhas de continuação, sem UG)
    ...

Cada linha de fonte é um valor orçado PRÓPRIO (não uma subdivisão do
valor da UG) — confirmado somando todas as linhas de fonte do documento
inteiro: bate exatamente com o rodapé "Total orçado...: R$ 250.000.000,00".
Ou seja, a mesma lógica de RubricaOrcamentaria para despesa (classificação
× fonte, cada combinação com sua própria dotação) vale aqui para receita.

Linhas de rodapé ("Total de contas...", "Total orçado...", "Total <UG>...",
"Total <código fonte> -<nome>...") são resumos/subtotais do próprio
relatório, não dados — ignoradas.

Só duas siglas de Unidade Gestora aparecem neste documento: PMNP
(Prefeitura) e CMNP (Câmara) — receita é arrecadada de forma centralizada,
diferente de despesa (que está espalhada por 8 UGs/fundos); os fundos
recebem repasses da Prefeitura, não arrecadam diretamente.
"""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .base import ParserBase, ResultadoParsing

SIGLA_UG_CODIGO = {"PMNP": "01", "CMNP": "02"}

RE_CODIGO_NOME = re.compile(r"^((?:\d+\.){6,10}\d+)\s+(.+?)\s*$")
RE_UG_VALOR_FONTE = re.compile(r"^(PMNP|CMNP)\s+(-?[\d.,]+)\s+(.+?)\s*$")
RE_VALOR_FONTE = re.compile(r"^(-?[\d.,]+)\s+(.+?)\s*$")
RE_CABECALHO_COLUNAS = re.compile(r"digo.*Valor", re.IGNORECASE)


def _para_decimal(valor_texto: str) -> Decimal:
    try:
        return Decimal(valor_texto.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return Decimal("0")


class FichasReceitasASPECParser(ParserBase):
    tipo_relatorio = "FICHAS_RECEITAS"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        import pdfplumber

        resultado = ResultadoParsing()
        bloco_atual: dict | None = None

        with pdfplumber.open(caminho_arquivo) as pdf:
            for pagina in pdf.pages:
                for linha in (pagina.extract_text() or "").split("\n"):
                    texto = linha.strip()
                    if not texto or set(texto) <= {"-"}:
                        continue
                    if texto.startswith(("Governo", "Consolidado", "Total", "Classifica")):
                        continue
                    if RE_CABECALHO_COLUNAS.search(texto):
                        continue

                    m_codigo = RE_CODIGO_NOME.match(texto)
                    if m_codigo:
                        bloco_atual = {"codigo": m_codigo.group(1), "nome": m_codigo.group(2).strip()}
                        continue

                    m_ug = RE_UG_VALOR_FONTE.match(texto)
                    if m_ug and bloco_atual is not None:
                        sigla, valor_texto, fonte_nome = m_ug.groups()
                        ug_codigo = SIGLA_UG_CODIGO.get(sigla)
                        if ug_codigo is None:
                            resultado.avisos.append(f"Sigla de Unidade Gestora não reconhecida: {sigla!r}")
                            continue
                        resultado.linhas.append({
                            "codigo": bloco_atual["codigo"],
                            "nome": bloco_atual["nome"],
                            "unidade_gestora_codigo": ug_codigo,
                            "fonte_nome": fonte_nome.strip(),
                            "valor_orcado": _para_decimal(valor_texto),
                        })
                        continue

                    m_valor = RE_VALOR_FONTE.match(texto)
                    if m_valor and bloco_atual is not None and resultado.linhas:
                        valor_texto, fonte_nome = m_valor.groups()
                        ultima = resultado.linhas[-1]
                        resultado.linhas.append({
                            "codigo": bloco_atual["codigo"],
                            "nome": bloco_atual["nome"],
                            "unidade_gestora_codigo": ultima["unidade_gestora_codigo"],
                            "fonte_nome": fonte_nome.strip(),
                            "valor_orcado": _para_decimal(valor_texto),
                        })
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "FICHAS_RECEITAS"): FichasReceitasASPECParser,
}
