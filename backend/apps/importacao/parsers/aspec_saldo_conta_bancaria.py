"""
Parser para "Relação de saldos - Por UG titular da conta" do ASPEC
(`DADOS/SALDO/CONTAS/CONTAS<mês>.PDF` — ex.: `CONTAS01.PDF` = mês 01). A
mesma pasta também tem um `CONSOLIDADOxx.PDF`, mas é um relatório
DIFERENTE ("Saldo das fichas do sistema financeiro", colunas "SALDO
DEVEDOR"/"SALDO CREDOR") — não é uma soma dos por-UG, é outra visão do
sistema financeiro; não usado aqui.

**Mudança de formato da fonte, 2026-11-12**: até então este relatório
saía em um arquivo por Unidade Gestora por mês
(`DADOS/SALDO/CONTAS/<mês>/<SIGLA><mês>.PDF`) e este parser assumia uma
única UG para o arquivo inteiro. O ASPEC passou a exportar **um único PDF
por mês cobrindo todas as UGs** (nome da UG na linha 3 de cada página,
repetido em toda página daquela UG) — mesma estrutura de
`aspec_restos_a_pagar.py`/`aspec_saldo_balanco.py`. Isso exigiu dois
ajustes, não só reconhecer a UG por página:

1. A UG é lida a cada página (não mais uma vez só para o arquivo
   inteiro) — senão só a primeira UG do arquivo é importada.
2. **As três camadas de resumo do fim de cada UG não terminam mais o
   arquivo** — a seção da próxima UG começa logo em seguida, com conteúdo
   real. O design antigo (`parando = True; break` ao ver qualquer um dos
   prefixos de parada) assumia que nada mais vinha depois — correto
   quando o arquivo tinha só uma UG, mas agora aborta o arquivo inteiro na
   primeira UG, descartando todo o resto ("só importou a prefeitura" era
   exatamente este sintoma). Trocado por um estado de "pulando resumo da
   UG atual" que é resetado sempre que a UG muda (não quando se vê
   qualquer marcador específico — nenhum aparece de forma confiável no
   fim do resumo, só a mudança de cabeçalho de UG é confiável).

**UG e mês vêm sempre do cabeçalho do próprio arquivo**, nunca do nome do
arquivo ou da pasta — a data impressa é o ÚLTIMO dia do mês ("31/01/2026"
para o mês 01).

Layout — uma única categoria "Banco" nos arquivos vistos (nenhum
"Depósitos"/"Consignações" como no relatório de saldo de balanço):

    BANPARA...........170.289-0 (PMNP IPVA) 0,00 0,00
    15000000 - Recursos não vinculados de impostos 0,00
    ...

A linha da conta traz DOIS valores (saldo pré-pagamentos já previstos,
saldo não comprometido), sem D/C — só as linhas de fonte têm natureza, e
só quando o valor não é zero.

Três camadas de resumo a descartar, nessa ordem, cada uma repetindo dados
já lidos **dentro da seção de uma UG** — "TOTAL DA CONTA BANCO...",
"Detalhamento da conta BANCO por fontes de recursos" (+ seu "TOTAL
detalhamento..."), e no fim "Detalhamento geral de todas as contas" +
"TOTAL GERAL DETALHAMENTO TODAS CONTAS". Um bug já pego e corrigido
durante o desenvolvimento original: pular só o resumo geral do fim e não
o "TOTAL DA CONTA BANCO"/"Detalhamento da conta BANCO" do meio dobrava os
valores por fonte (a mesma informação aparecia duas vezes) — revalidado
batendo exatamente contra o "TOTAL GERAL DETALHAMENTO TODAS CONTAS" da
Prefeitura.
"""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .base import ParserBase, ResultadoParsing

RE_DATA_REFERENCIA = re.compile(r"(\d{2}/\d{2}/\d{4})\s+-\s+em R\$")
RE_CONTA = re.compile(r"^(.+?)\.{2,}\s*([\w.\-]+)\s*\((.+?)\)\s+(-?[\d.,]+)\s+(-?[\d.,]+)\s*$")
RE_FONTE = re.compile(r"^(\d{8})\s*-\s*(.+?)\s+(-?[\d.,]+)(?:\s+([DC]))?\s*$")

PREFIXOS_PARADA = ("Detalhamento", "TOTAL DA CONTA", "TOTAL detalhamento", "TOTAL GERAL")


def _para_decimal(valor_texto: str) -> Decimal:
    try:
        return Decimal(valor_texto.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return Decimal("0")


def _ignorar(texto: str) -> bool:
    if not texto:
        return True
    sem_espacos = texto.replace(" ", "")
    if sem_espacos.startswith(("Pará", "Governo", "Prefeitura", "Camara", "Câmara", "Fundo", "DENOMINAÇÃO", "CONTÁBIL")):
        return True
    return set(texto) <= {"-"} or texto == "Banco"


class SaldoContaBancariaASPECParser(ParserBase):
    tipo_relatorio = "SALDO_CONTA_BANCARIA"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        import pdfplumber

        resultado = ResultadoParsing()
        unidade_gestora_nome: str | None = None
        data_referencia: str | None = None
        conta_atual: dict | None = None
        pulando_resumo_da_ug = False
        unidades_gestoras_vistas: set[str] = set()

        with pdfplumber.open(caminho_arquivo) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text() or ""
                linhas_pagina = texto_pagina.split("\n")

                if data_referencia is None:
                    m_data = RE_DATA_REFERENCIA.search(texto_pagina)
                    if m_data:
                        data_referencia = m_data.group(1)

                nome_ug_pagina = None
                if len(linhas_pagina) > 2 and linhas_pagina[1].strip().startswith("Governo Municipal"):
                    nome_ug_pagina = linhas_pagina[2].strip()

                if nome_ug_pagina == "Consolidado":
                    continue
                if nome_ug_pagina and nome_ug_pagina != unidade_gestora_nome:
                    # Nova seção de UG: as três camadas de resumo do fim de
                    # cada UG não terminam mais o arquivo (ver docstring do
                    # módulo) — o estado de "pulando resumo" tem que ser
                    # resetado na troca de UG, não permanecer True pra
                    # sempre como no design antigo de um-arquivo-por-UG.
                    unidade_gestora_nome = nome_ug_pagina
                    unidades_gestoras_vistas.add(nome_ug_pagina)
                    pulando_resumo_da_ug = False

                for linha in linhas_pagina:
                    texto = linha.strip()
                    if not texto:
                        continue
                    if texto.startswith(PREFIXOS_PARADA):
                        pulando_resumo_da_ug = True
                        continue
                    if pulando_resumo_da_ug:
                        continue
                    if _ignorar(texto):
                        continue

                    m_conta = RE_CONTA.match(texto)
                    if m_conta:
                        banco, numero, apelido, saldo_previsto, saldo_nao_comprometido = m_conta.groups()
                        conta_atual = {
                            "unidade_gestora_nome": unidade_gestora_nome,
                            "banco": banco, "numero_conta": numero, "apelido": apelido,
                            "saldo_pre_pagamentos_previstos": _para_decimal(saldo_previsto),
                            "saldo_nao_comprometido": _para_decimal(saldo_nao_comprometido),
                        }
                        continue

                    m_fonte = RE_FONTE.match(texto)
                    if m_fonte and conta_atual is not None:
                        fonte_codigo, fonte_nome, valor_fonte, natureza_fonte = m_fonte.groups()
                        resultado.linhas.append({
                            **conta_atual,
                            "fonte_codigo": fonte_codigo,
                            "fonte_nome": fonte_nome.strip(),
                            "valor_fonte": _para_decimal(valor_fonte),
                            "natureza_fonte": natureza_fonte or "",
                        })
                        continue

                    resultado.avisos.append(f"Linha não reconhecida: {texto!r}")

        if not unidades_gestoras_vistas:
            resultado.avisos.append("Não foi possível identificar nenhuma Unidade Gestora pelo cabeçalho.")
        mes_referencia = int(data_referencia.split("/")[1]) if data_referencia else None
        resultado.metadados.update({
            "unidades_gestoras_nomes": sorted(unidades_gestoras_vistas),
            "data_referencia": data_referencia,
            "mes_referencia": mes_referencia,
        })

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "SALDO_CONTA_BANCARIA"): SaldoContaBancariaASPECParser,
}
