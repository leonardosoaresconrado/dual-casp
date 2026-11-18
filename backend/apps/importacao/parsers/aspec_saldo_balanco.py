"""
Parser para "MOVIMENTOS DE SALDOS DE BALANÇO" do ASPEC
(`DADOS/SALDO/BALANÇO/SALDO_BALANCO.PDF`), foto do saldo de cada conta
bancária numa data específica.

**Mudança de formato da fonte, 2026-11-12**: até então este relatório
saía em 8 arquivos separados, um por Unidade Gestora (`BAL_<SIGLA>.PDF`),
e este parser assumia uma única UG para o arquivo inteiro. O ASPEC passou
a exportar **um único PDF cobrindo todas as UGs** (mesma UG impressa nas
primeiras 3 linhas de cada página, repetida em toda página daquela UG,
podendo ocupar várias páginas seguidas) — a mesma estrutura que
`aspec_restos_a_pagar.py` já usava. O parser foi ajustado para
reconhecer a UG **por página**, não mais uma vez só para o arquivo
inteiro — se isso não for corrigido, apenas a primeira UG do arquivo
(tipicamente a Prefeitura) é importada, o resto é descartado em
silêncio. Também não há mais uma linha de período "dd/mm/aaaa a
dd/mm/aaaa" no cabeçalho — virou "Mês de `<Nome>`/`<ano>`", igual aos
outros relatórios mensais; a data real de cada conta (sempre a mesma no
arquivo inteiro, uma foto de um único dia) já vem em cada linha de conta
e é isso que se usa agora, não mais um período do cabeçalho.

**Nunca confie no nome do arquivo para saber a UG ou a data** — segue a
mesma disciplina já adotada no resto do pipeline. Há também uma seção
final "Consolidado" (mesma posição do nome de UG, várias páginas) que é a
re-agregação de todas as UGs já lidas — pulada inteiramente, mesma
convenção de `aspec_restos_a_pagar.py` (confirmado antes, contando
ocorrências de cada sigla de UG no texto, que o antigo
"BALANCO_CONSOLIDADO.PDF" era de fato a união das UGs, não um espelho de
uma só — aqui "Consolidado" significa o que diz, ao contrário da
armadilha já vista no balancete de despesa).

**Páginas de continuação de "DETALHAMENTO...por Fontes de Recursos" às
vezes não repetem o cabeçalho de 3 linhas** (ficam só com linhas de
fonte, sem "Pará"/"Governo.../`<UG>`") — confirmado inspecionando o
arquivo real. Por isso a UG só é atualizada quando a página realmente traz
o cabeçalho completo (linha 2 começando com "Governo Municipal"); páginas
sem ele mantêm a UG da página anterior — o que já é o comportamento
correto, porque essas páginas são sempre continuação do bloco de resumo
que `pulando_resumo` já pula de qualquer forma.

Layout: cada conta pertence a uma categoria (linha isolada "Banco",
"Depósitos de diversas origens", "Consignações" — nem toda UG tem todas),
seguida de uma linha de conta e suas linhas de fonte:

    001 BB..................1.139-8 (PMNP ROG TRIBUTOS) 02/01/2026 R$ 325.305,75 D
    15000000 Recursos não vinculados de impostos R$ 316.253,04 D
    ...

Algumas contas (categorias "Depósitos.../Consignações") não têm banco/
número de conta, só um código de 3 dígitos + descrição direto.

O relatório fecha com resumos que **repetem** os dados já lidos dentro da
seção de cada UG, nunca trazem conta nova — descartados inteiramente ao
serem encontrados ("DETALHAMENTO da conta <categoria> por Fontes de
Recursos", pulado até o próximo "SUBTOTAL", retomando a leitura normal
depois; "TOTAL das contas por Fontes de Recursos", sempre o último bloco
de cada UG). Validado batendo a soma de cada (código, natureza) contra
esse resumo geral, para a UG com mais contas — bateu exatamente, nenhum
aviso.
"""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .base import ParserBase, ResultadoParsing

RE_CABECALHO_UG = re.compile(r"^(.*?)\s+M[êe]s de \w+/\d{4}\s+P[áa]gina\s*:\s*\d+\s*$")
RE_CONTA_BANCO = re.compile(
    r"^(\d{3})\s+(.+?)\.{2,}\s*([\w.\-]+)\s*\((.+?)\)\s+(\d{2}/\d{2}/\d{4})\s+R\$\s*(-?[\d.,]+)\s+([DC])\s*$"
)
RE_CONTA_SIMPLES = re.compile(r"^(\d{3})\s+(.+?)\s+(\d{2}/\d{2}/\d{4})\s+R\$\s*(-?[\d.,]+)\s+([DC])\s*$")
RE_FONTE = re.compile(r"^(\d{8})\s+(.+?)\s+R\$\s*(-?[\d.,]+)\s+([DC])\s*$")
CATEGORIAS_CONHECIDAS = {"Banco", "Depósitos de diversas origens", "Consignações"}


def _nome_ug_da_pagina(texto_pagina: str) -> str | None:
    """
    Só retorna um nome quando a página realmente traz o cabeçalho de 3
    linhas completo (linha 2 começa com "Governo Municipal") — páginas de
    continuação sem cabeçalho devolvem None, e o chamador mantém a UG da
    página anterior nesse caso.
    """
    linhas = texto_pagina.split("\n")
    if len(linhas) < 3 or not linhas[1].strip().startswith("Governo Municipal"):
        return None
    m = RE_CABECALHO_UG.match(linhas[2].strip())
    return m.group(1).strip() if m else linhas[2].strip()


def _para_decimal(valor_texto: str) -> Decimal:
    try:
        return Decimal(valor_texto.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return Decimal("0")


def _ignorar(texto: str) -> bool:
    if not texto:
        return True
    sem_espacos = texto.replace(" ", "")
    if sem_espacos.startswith(("Pará", "Governo", "Prefeitura", "Camara", "Câmara", "Fundo", "CONTA", "SUBTOTAL")):
        return True
    return set(texto) <= {"-"}


class SaldoBalancoASPECParser(ParserBase):
    tipo_relatorio = "SALDO_BALANCO"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        import pdfplumber

        resultado = ResultadoParsing()
        unidade_gestora_nome: str | None = None
        data_referencia: str | None = None
        conta_atual: dict | None = None
        categoria_atual = "Banco"
        pulando_resumo = False
        unidades_gestoras_vistas: set[str] = set()

        with pdfplumber.open(caminho_arquivo) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text() or ""

                nome_ug_pagina = _nome_ug_da_pagina(texto_pagina)
                if nome_ug_pagina == "Consolidado":
                    continue
                if nome_ug_pagina and nome_ug_pagina != unidade_gestora_nome:
                    # Nova seção de UG: "TOTAL das contas por Fontes de
                    # Recursos" (o resumo final de cada UG) nunca é seguido
                    # por um "SUBTOTAL" — era seguro assumir isso só porque,
                    # no antigo formato de um-arquivo-por-UG, nada real vinha
                    # depois dele. Agora o arquivo continua com a próxima UG,
                    # então o estado de "pulando resumo" tem que ser
                    # resetado aqui, na troca de UG, não só ao ver SUBTOTAL.
                    unidade_gestora_nome = nome_ug_pagina
                    unidades_gestoras_vistas.add(nome_ug_pagina)
                    categoria_atual = "Banco"
                    pulando_resumo = False

                for linha in texto_pagina.split("\n"):
                    texto = linha.strip()
                    if not texto:
                        continue

                    if texto.startswith("DETALHAMENTO") or texto.startswith("TOTAL das contas"):
                        pulando_resumo = True
                        continue
                    if pulando_resumo:
                        if texto.startswith("SUBTOTAL"):
                            pulando_resumo = False
                        continue
                    if texto in CATEGORIAS_CONHECIDAS:
                        categoria_atual = texto
                        continue
                    if _ignorar(texto):
                        continue

                    m_conta = RE_CONTA_BANCO.match(texto)
                    if m_conta:
                        codigo, banco, numero, apelido, data_conta, valor, natureza = m_conta.groups()
                        data_referencia = data_referencia or data_conta
                        conta_atual = {
                            "unidade_gestora_nome": unidade_gestora_nome,
                            "categoria": categoria_atual, "codigo_conta": codigo, "banco": banco,
                            "numero_conta": numero, "apelido": apelido,
                            "valor_conta": _para_decimal(valor), "natureza_conta": natureza, "teve_fonte": False,
                        }
                        continue
                    m_conta = RE_CONTA_SIMPLES.match(texto)
                    if m_conta:
                        codigo, apelido, data_conta, valor, natureza = m_conta.groups()
                        data_referencia = data_referencia or data_conta
                        conta_atual = {
                            "unidade_gestora_nome": unidade_gestora_nome,
                            "categoria": categoria_atual, "codigo_conta": codigo, "banco": "", "numero_conta": "",
                            "apelido": apelido,
                            "valor_conta": _para_decimal(valor), "natureza_conta": natureza, "teve_fonte": False,
                        }
                        continue

                    m_fonte = RE_FONTE.match(texto)
                    if m_fonte and conta_atual is not None:
                        fonte_codigo, fonte_nome, valor_fonte, natureza_fonte = m_fonte.groups()
                        conta_atual["teve_fonte"] = True
                        resultado.linhas.append({
                            **{k: v for k, v in conta_atual.items() if k != "teve_fonte"},
                            "fonte_codigo": fonte_codigo,
                            "fonte_nome": fonte_nome.strip(),
                            "valor_fonte": _para_decimal(valor_fonte),
                            "natureza_fonte": natureza_fonte,
                        })
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        if not unidades_gestoras_vistas:
            resultado.avisos.append("Não foi possível identificar nenhuma Unidade Gestora pelo cabeçalho.")
        if data_referencia is None:
            resultado.avisos.append("Data de referência não identificada em nenhuma linha de conta.")
        resultado.metadados.update({
            "unidades_gestoras_nomes": sorted(unidades_gestoras_vistas),
            "data_referencia": data_referencia,
        })

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "SALDO_BALANCO"): SaldoBalancoASPECParser,
}
