"""
Parser para "Fontes de recursos" exportado em PDF pelo ASPEC — catálogo de
código + nome + tipo (Ordinário/Vinculado) de cada fonte de recursos.

Um mesmo código de fonte é usado por qualquer Unidade Gestora do
município (não há variação de nome por UG neste catálogo) — por isso o
serviço atualiza o nome/tipo em todas as FonteRecursos já cadastradas com
aquele código, em qualquer UG.

Cada fonte também traz duas linhas de referência cruzada ("Fonte na
STN"/"Fonte no Tribunal") que este parser ignora — não há campo
correspondente em FonteRecursos hoje.
"""

import re
from pathlib import Path

from .base import ParserBase, ResultadoParsing

RE_FONTE = re.compile(r"^(\d{8})\s+(.+?)\s+(Ordin[áa]rio|Vinculado)\s*$")

TIPO_MAP = {"ordinário": "ORDINARIO", "ordinario": "ORDINARIO", "vinculado": "VINCULADO"}


class FontesRecursosASPECParser(ParserBase):
    tipo_relatorio = "FONTES_RECURSOS"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        import pdfplumber

        resultado = ResultadoParsing()

        with pdfplumber.open(caminho_arquivo) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text() or ""
                for texto in texto_pagina.split("\n"):
                    texto = texto.strip()
                    if not re.match(r"^\d{8}\s", texto):
                        continue
                    m = RE_FONTE.match(texto)
                    if not m:
                        resultado.avisos.append(f"Linha de fonte não reconhecida: {texto!r}")
                        continue
                    codigo, nome, tipo_texto = m.groups()
                    resultado.linhas.append({
                        "codigo": codigo,
                        "nome": nome.strip(),
                        "tipo": TIPO_MAP.get(tipo_texto.lower(), ""),
                    })

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "FONTES_RECURSOS"): FontesRecursosASPECParser,
}
