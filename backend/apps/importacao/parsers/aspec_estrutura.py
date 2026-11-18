"""
Parser para a "Estrutura organizacional" exportada em PDF pelo ASPEC —
lista todo Órgão do município e, dentro de cada um, suas Unidades
Orçamentárias com a Unidade Gestora responsável por cada uma.

Importante: um Órgão pode ter unidades orçamentárias em Unidades Gestoras
diferentes (ex.: a "Secretaria Municipal de Educação" tem uma unidade na
"Fundo Municipal de Educação" e outra no FUNDEB) — por isso a Unidade
Gestora é um atributo da unidade orçamentária, não do órgão (ver
apps.municipios.models.Orgao). Esse relatório é a fonte de verdade para
esse mapeamento, e também para os nomes reais de Órgão/Unidade
Orçamentária (que os outros relatórios não têm, por isso entravam como
"(a definir)").

O cabeçalho de página ("Cód Nome do órgão" / "Cód Nome da unidade
orçamentária Tipo Unidade gestora") se repete a cada página e pode
interromper uma lista de unidades no meio — isso é inofensivo aqui porque
o parser só reseta o "órgão atual" ao encontrar uma nova linha de
cabeçalho de órgão (código + nome, sem "comum"/"reserv.cont." e sem nome
de UG), nunca ao encontrar as linhas de cabeçalho repetidas.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from .base import ParserBase, ResultadoParsing

RE_SOMENTE_SEPARADOR = re.compile(r"^[_\s]+$")
# "01 Camara Municipal comum Camara Municipal de Novo Progresso" -> unidade orç.
# O PDF às vezes gruda o nome da unidade no tipo sem espaço (ex.:
# "Adolescentecomum"), por isso o \s* (não \s+) antes do tipo.
RE_UNIDADE = re.compile(r"^(\d{2})\s+(.+?)\s*(comum|reserv\.cont\.)\s+(.+?)\s*$")
# "01 Camara Municipal de Novo Progresso" (sem tipo/UG) -> cabeçalho de órgão
RE_ORGAO = re.compile(r"^(\d{2})\s+(.+?)\s*$")

LINHAS_CABECALHO_IGNORAR = (
    "GOVERNO MUNICIPAL DE",
    "ESTRUTURA ORGANIZACIONAL",
    "CÓD NOME DO ÓRGÃO",
    "CÓD NOME DA UNIDADE",
)


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
    orgao_nome: str | None = None


class EstruturaOrganizacionalASPECParser(ParserBase):
    tipo_relatorio = "ESTRUTURA_ORGANIZACIONAL"

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
                    if texto.upper().startswith("TOTAL DE ÓRGÃOS"):
                        continue

                    m_unidade = RE_UNIDADE.match(texto)
                    if m_unidade:
                        if not ctx.orgao_codigo:
                            resultado.avisos.append(f"Unidade orçamentária sem órgão em contexto: {texto!r}")
                            continue
                        unidade_codigo, unidade_nome, tipo, ug_nome = m_unidade.groups()
                        resultado.linhas.append({
                            "orgao_codigo": ctx.orgao_codigo,
                            "orgao_nome": ctx.orgao_nome,
                            "unidade_codigo": unidade_codigo,
                            "unidade_nome": unidade_nome.strip(),
                            "tipo": tipo,
                            "ug_nome": ug_nome.strip(),
                        })
                        continue

                    m_orgao = RE_ORGAO.match(texto)
                    if m_orgao:
                        ctx.orgao_codigo, ctx.orgao_nome = m_orgao.groups()
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "ESTRUTURA_ORGANIZACIONAL"): EstruturaOrganizacionalASPECParser,
}
