"""
Parser para o relatório "Relacionamento das ações com projetos/atividades"
exportado em PDF pelo ASPEC a partir da LOA.

Dá os nomes oficiais de Função, Subfunção, Programa e Ação (Projeto/
Atividade/Operação Especial) — o cadastro completo da LOA do exercício.

Layout:
    Função... NN Nome da função
    Subfunção NNN Nome da subfunção
    Projeto...D.DDD Nome do projeto
    Programa. DDDD Nome do programa
    Atividade.D.DDD Nome da atividade
    Programa. DDDD Nome do programa
    ...
    [ ] Ação.....: DDDD - Nome (bloco secundário de referência cruzada; ignorado)
    -------------------------------------------------- (separador; fecha o bloco)
"""

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from .base import ParserBase, ResultadoParsing

RE_FUNCAO = re.compile(r"^Fun\S*\.*\s*(\d{2})\s+(.+)$")
RE_SUBFUNCAO = re.compile(r"^Subfun\S*\.*\s*(\d{3})\s+(.+)$")
RE_ACAO = re.compile(r"^(Projeto|Atividade|Opera\S*\s*Especial)\.*\s*(\d)\.(\d{3,4})\s+(.+)$")
RE_PROGRAMA = re.compile(r"^Programa\.*\s*(\d{4})\s+(.+)$")

TIPO_POR_PALAVRA = {
    "Projeto": "PROJETO",
    "Atividade": "ATIVIDADE",
}


@dataclass
class LinhaRelacionamento:
    funcao_codigo: str
    funcao_nome: str
    subfuncao_codigo: str
    subfuncao_nome: str
    acao_tipo: str
    acao_codigo: str
    acao_nome: str
    programa_codigo: str
    programa_nome: str


class RelacionamentoAcoesASPECParser(ParserBase):
    tipo_relatorio = "RELACIONAMENTO_ACOES"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        resultado = ResultadoParsing()

        funcao_codigo = funcao_nome = None
        subfuncao_codigo = subfuncao_nome = None
        pendente = None  # (tipo, codigo, nome) aguardando a linha "Programa."
        em_secao_secundaria = False

        with pdfplumber.open(caminho_arquivo) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ""
                for bruta in texto.splitlines():
                    linha = bruta.strip()
                    if not linha:
                        continue

                    if set(linha) <= {"-", " "}:
                        # separador de fim de bloco função/subfunção
                        em_secao_secundaria = False
                        pendente = None
                        continue

                    if set(linha) <= {"=", " "}:
                        # separador de cabeçalho de página (repetido a cada página);
                        # não encerra o bloco corrente, que pode continuar na página seguinte
                        continue

                    if linha.startswith(("Pará", "Par", "Governo Municipal", "Relacionamento das")):
                        continue

                    if linha.startswith("[ ]"):
                        em_secao_secundaria = True
                        continue

                    m_funcao = RE_FUNCAO.match(linha)
                    if m_funcao:
                        funcao_codigo, funcao_nome = m_funcao.groups()
                        continue

                    m_subfuncao = RE_SUBFUNCAO.match(linha)
                    if m_subfuncao:
                        subfuncao_codigo, subfuncao_nome = m_subfuncao.groups()
                        continue

                    if em_secao_secundaria:
                        continue

                    m_acao = RE_ACAO.match(linha)
                    if m_acao:
                        palavra_tipo, primeiro_digito, resto_codigo, nome = m_acao.groups()
                        tipo = TIPO_POR_PALAVRA.get(palavra_tipo, "OPERACAO_ESPECIAL")
                        pendente = (tipo, f"{primeiro_digito}{resto_codigo}", nome)
                        continue

                    m_programa = RE_PROGRAMA.match(linha)
                    if m_programa:
                        if not (pendente and funcao_codigo and subfuncao_codigo):
                            resultado.avisos.append(f"Programa sem ação/função pendente: {linha!r}")
                            continue
                        programa_codigo, programa_nome = m_programa.groups()
                        tipo, acao_codigo, acao_nome = pendente
                        resultado.linhas.append(LinhaRelacionamento(
                            funcao_codigo=funcao_codigo, funcao_nome=funcao_nome,
                            subfuncao_codigo=subfuncao_codigo, subfuncao_nome=subfuncao_nome,
                            acao_tipo=tipo, acao_codigo=acao_codigo, acao_nome=acao_nome,
                            programa_codigo=programa_codigo, programa_nome=programa_nome,
                        ))
                        pendente = None
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {linha!r}")

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "RELACIONAMENTO_ACOES"): RelacionamentoAcoesASPECParser,
}
