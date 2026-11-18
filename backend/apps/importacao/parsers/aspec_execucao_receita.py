"""
Parser para "Demonstrativo da receita por classificação econômica" do
ASPEC (R01.PDF..R09.PDF) — um arquivo por mês (período "dd/mm/aaaa a
dd/mm/aaaa" no cabeçalho cobre só aquele mês, não é cumulativo), com a
granularidade que falta em RECEITAS.ods: fonte de recursos por lançamento.

Layout por bloco (código de receita):
    <código> - <nome>
    <código_fonte(8 dígitos)> <nome_fonte_truncado> <complementação(4 díg)> <bruto> <dedução> <anulação> <líquido>
    ... (uma linha por fonte sob esse código)
    TOTAL DA RECEITA.. <bruto> <dedução> <anulação> <líquido>   (descartada — é só o subtotal do próprio relatório)

O nome da fonte vem truncado (largura fixa de coluna no PDF) — ignorado;
quem usa este parser resolve o nome de verdade pela FonteRecursos já
cadastrada (ou cria um placeholder), nunca por este texto cortado.

O código de receita aqui usa o primeiro segmento SEM zero à esquerda
("1.1.1.2.50..."), enquanto FICHAS_RECEITAS.PDF usa 3 dígitos
("001.1.1.2.50...") para a mesma classificação — `normalizar_codigo` aplica
o mesmo zero-padding para que os dois lados cassem no mesmo RubricaReceita.

Confrontado mês a mês contra RECEITAS.ods, o valor líquido daqui fica
sistematicamente ~0,3% acima (mesmo sinal todo mês) — ver nota em
`LancamentoExecucaoReceita`. Não é um bug de parsing (os totais batem
exatamente com o "TOTAL GERAL.." impresso em cada arquivo); as duas fontes
simplesmente medem coisas ligeiramente diferentes.
"""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .base import ParserBase, ResultadoParsing

RE_PERIODO = re.compile(r"(\d{2})/(\d{2})/(\d{4})\s+a\s+(\d{2})/(\d{2})/(\d{4})")
RE_CODIGO_NOME = re.compile(r"^(\d+(?:\.\d+)+)\s*-\s*(.+?)\s*$")
RE_FONTE_VALORES = re.compile(
    r"^(\d{8})\s+(.+?)\s+(\d{4})\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s*$"
)

PREFIXOS_IGNORADOS = (
    "Pará", "Governo", "Demonstrativo", "Consolidado", "Resumoclass",
    "CLASS.ECON", "COMPLEMENTA", "FONTEDERECURSO", "TOTALDARECEITA", "TOTALGERAL",
)


def normalizar_codigo(codigo: str) -> str:
    partes = codigo.split(".")
    partes[0] = partes[0].zfill(3)
    return ".".join(partes)


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


class ExecucaoReceitaASPECParser(ParserBase):
    tipo_relatorio = "EXECUCAO_RECEITA"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        import pdfplumber

        resultado = ResultadoParsing()
        bloco_atual: dict | None = None
        mes_referencia: int | None = None

        with pdfplumber.open(caminho_arquivo) as pdf:
            for indice_pagina, pagina in enumerate(pdf.pages):
                texto_pagina = pagina.extract_text() or ""
                if mes_referencia is None:
                    m_periodo = RE_PERIODO.search(texto_pagina)
                    if m_periodo:
                        mes_referencia = int(m_periodo.group(5))

                for linha in texto_pagina.split("\n"):
                    texto = linha.strip()
                    if _ignorar(texto):
                        continue

                    m_codigo = RE_CODIGO_NOME.match(texto)
                    if m_codigo:
                        bloco_atual = {"codigo": normalizar_codigo(m_codigo.group(1)), "nome": m_codigo.group(2).strip()}
                        continue

                    m_fonte = RE_FONTE_VALORES.match(texto)
                    if m_fonte and bloco_atual is not None:
                        fonte_codigo, _nome_truncado, _complementacao, bruto, deducao, anulacao, liquido = m_fonte.groups()
                        resultado.linhas.append({
                            "codigo": bloco_atual["codigo"],
                            "nome": bloco_atual["nome"],
                            "fonte_codigo": fonte_codigo,
                            "valor_bruto": _para_decimal(bruto),
                            "deducao": _para_decimal(deducao),
                            "anulacao": _para_decimal(anulacao),
                            "valor_liquido": _para_decimal(liquido),
                        })
                        continue

                    resultado.avisos.append(f"Linha não reconhecida (página {indice_pagina + 1}): {texto!r}")

        if mes_referencia is None:
            resultado.avisos.append("Não foi possível determinar o mês de referência pelo cabeçalho do relatório.")
        resultado.metadados["mes_referencia"] = mes_referencia

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "EXECUCAO_RECEITA"): ExecucaoReceitaASPECParser,
}
