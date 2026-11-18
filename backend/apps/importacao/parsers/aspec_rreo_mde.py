"""
Parser para o RREO-Anexo 8 (LDB, art.72) — Demonstrativo das Receitas e
Despesas com Manutenção e Desenvolvimento do Ensino (MDE) — um PDF por
bimestre em `DADOS/FISCAL/EXECUÇÃO FISCAL/<bimestre>/`, nomeação
inconsistente entre pastas (`RREO81.PDF`, `RREO82.PDF`, `RRE8122.PDF`...)
— bimestre e exercício vêm do cabeçalho do próprio relatório, nunca do
nome do arquivo.

Este único arquivo alimenta SETE índices constitucionais distintos — MDE
(CF art.212/LDB art.72, mínimo de 25% da receita de impostos), Magistério/
FUNDEB (CF art.212-A, inciso XI, mínimo de 70% do FUNDEB em remuneração do
magistério), o mínimo de 4% do FUNDEB na criação de matrículas em ETI
(mesma linha 15, sub-item 15.2 — 15.1 é o magistério), aplicação do VAAT
(Complementação da União ao FUNDEB) em educação infantil, o mínimo de 15%
do VAAT em despesas de capital, o limite de 10% de superávit do FUNDEB não
aplicado e a reprogramação (aplicação do superávit do exercício anterior)
— todos na mesma seção "INDICADORES - Art.212-A"/"Art.25, §3º - Lei
14.113/2020" do relatório, linhas 15(.1/.2)/16/17/18/19. Por isso o parser
devolve até sete linhas em `resultado.linhas`, cada uma com `"tipo"` em
`mde`/`magisterio`/`eti_fundeb`/`vaat_educacao_infantil`/
`vaat_despesa_capital`/`fundeb_nao_aplicado`/`fundeb_reprogramacao`, e o
service (`importar_mde_e_magisterio`) grava em sete models diferentes.

Os sub-itens de receita do MDE (1.1-1.4 "Receita de Impostos", 2.1-2.7
"Receita de Transferências") e os sub-itens de origem da reprogramação
(19.1 impostos/transferências, 19.2 complementação da União) não viram
mais chaves fixas no dict — ver `mde["itens_receita"]`/
`fundeb_reprogramacao["origens"]` abaixo: cada um é uma lista de
dicts `{codigo, rotulo, grupo/origem, valor}`, persistida como linhas
filhas (`ApuracaoMDEReceitaItem`/`ApuracaoReprogramacaoFundebOrigem`) em
vez de colunas paralelas — uma linha numerada do relatório vira uma
linha filha, sem precisar de um mapa fixo nome-de-campo→sub-item.
"""

import math
import re
from decimal import Decimal
from pathlib import Path

import pdfplumber

from .aspec import MESES
from .base import ParserBase, ResultadoParsing

RE_BIMESTRE_ANO = re.compile(r"(\d)\s*[ºo]\s*bimestre\s*de\s*(\d{4})", re.IGNORECASE)
RE_MES_FINAL = re.compile(r"\(\s*\w+\s+a\s+(\w+)(?:/(\d{4}))?\s*\)", re.IGNORECASE)
RE_ANO = re.compile(r"(20\d{2})")

# código → (grupo, rótulo) dos sub-itens de receita do MDE, na ordem em
# que aparecem no relatório.
ITENS_RECEITA_MDE = {
    "1.1": ("IMPOSTOS", "IPTU"),
    "1.2": ("IMPOSTOS", "ITBI"),
    "1.3": ("IMPOSTOS", "ISS"),
    "1.4": ("IMPOSTOS", "IRRF"),
    "2.1": ("TRANSFERENCIAS", "FPM"),
    "2.2": ("TRANSFERENCIAS", "ICMS"),
    "2.3": ("TRANSFERENCIAS", "IPI"),
    "2.4": ("TRANSFERENCIAS", "ITR"),
    "2.5": ("TRANSFERENCIAS", "IPVA"),
    "2.6": ("TRANSFERENCIAS", "IOF"),
    "2.7": ("TRANSFERENCIAS", "Compensações"),
}


def _para_decimal(texto: str) -> str:
    return texto.replace(".", "").replace(",", ".").strip()


def _valores_da_linha(linha: str) -> list[str]:
    return [p.strip() for p in linha.split("|")][1:]


def _saldo_a_aplicar(nao_aplicado_exercicio_anterior: str, aplicado_ate_primeiro_quadrimestre: str) -> str:
    """
    O relatório tem uma coluna própria para isso ("VALOR SUPERÁVIT PERMIT.
    EXERC. ANT. NÃO APLICADO ATÉ PRIM.QUAD.EXE.ATUAL", a 5ª da seção) mas
    ela está sempre idêntica à coluna "NÃO APLICADO NO EXERCÍCIO ANTERIOR"
    — nunca desconta o que já foi aplicado, em nenhum bimestre/exercício
    visto (2025 e 2026). Não é um problema de parsing (o texto extraído já
    bate dígito a dígito com o PDF) — é o próprio relatório do ASPEC que
    não calcula essa coluna corretamente. Por pedido explícito do usuário,
    o saldo a aplicar é recalculado aqui como exigido (não aplicado do
    exercício anterior) menos aplicado até o 1º quadrimestre, ignorando o
    valor que o relatório imprime nessa coluna.
    """
    return str(Decimal(nao_aplicado_exercicio_anterior) - Decimal(aplicado_ate_primeiro_quadrimestre))


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


class RREOMDEASPECParser(ParserBase):
    tipo_relatorio = "RREO_MDE"

    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        resultado = ResultadoParsing()
        mde: dict = {}
        magisterio: dict = {}
        eti_fundeb: dict = {}
        vaat_ed_infantil: dict = {}
        vaat_capital: dict = {}
        fundeb_nao_aplicado: dict = {}
        fundeb_reprogramacao: dict = {}
        itens_receita_mde: list[dict] = []
        origem_impostos: dict = {}
        origem_uniao: dict = {}

        with pdfplumber.open(caminho_arquivo) as pdf:
            texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)

        linhas = texto_completo.split("\n")
        bimestre, exercicio = _periodo(linhas[:6])

        for i, linha in enumerate(linhas):
            texto = linha.strip()
            if re.match(r"^1\s*-\s*RECEITAS DE IMPOSTOS\b", texto):
                valores = _valores_da_linha(texto)
                mde["receita_impostos"] = _para_decimal(valores[-1])
                continue
            m_item = re.match(r"^([12]\.[1-7])\s*-", texto)
            if m_item and m_item.group(1) in ITENS_RECEITA_MDE:
                codigo = m_item.group(1)
                grupo, rotulo = ITENS_RECEITA_MDE[codigo]
                valor = _para_decimal(_valores_da_linha(texto)[-1])
                itens_receita_mde.append({"codigo": codigo, "grupo": grupo, "rotulo": rotulo, "valor": valor})
                continue
            if re.match(r"^2\s*-\s*RECEITA DE TRANSFER", texto):
                valores = _valores_da_linha(texto)
                mde["receita_transferencias"] = _para_decimal(valores[-1])
                continue
            if re.match(r"^3\s*-\s*TOTAL DA RECEITA RESULTANTE DE IMPOSTOS", texto):
                valores = _valores_da_linha(texto)
                mde["base_calculo"] = _para_decimal(valores[-1])
                continue
            if re.match(r"^6\s*-\s*RECEITAS RECEBIDAS DO FUNDEB\b", texto):
                valores = _valores_da_linha(texto)
                magisterio["fundeb_receita_total"] = _para_decimal(valores[-1])
                eti_fundeb["fundeb_receita_total"] = _para_decimal(valores[-1])
                continue
            if re.match(r"^20\s*-\s*TOTAL DAS DESPESAS COM A", texto):
                # "20 - TOTAL ... | DOTAÇÃO | EMPENHADA | LIQUIDADA | PAGA"
                valores = _valores_da_linha(texto)
                if len(valores) >= 4:
                    mde["despesa_mde_empenhada"] = _para_decimal(valores[1])
                    mde["despesa_mde_liquidada"] = _para_decimal(valores[2])
                    mde["despesa_mde_paga"] = _para_decimal(valores[3])
                continue
            if re.match(r"^23\s*-\s*\(\+\)\s*TOTAL DAS RECEITAS TRANSFERIDAS AO FUNDEB", texto):
                valores = _valores_da_linha(texto)
                mde["fundeb_transferido"] = _para_decimal(valores[-1])
                continue
            if re.match(r"^24\s*-\s*\(-\)\s*RECEITAS DO FUNDEB N", texto):
                valores = _valores_da_linha(texto)
                mde["excedente_fundeb_nao_aplicado"] = _para_decimal(valores[-1])
                continue
            if re.match(r"^27\s*-\s*\(-\)\s*CANCELAMENTO", texto):
                valores = _valores_da_linha(texto)
                if len(valores) >= 1 and valores[-1].strip():
                    mde["cancelamento_rp"] = _para_decimal(valores[-1])
                else:
                    # rótulo longo demais, quebra antes do "| valor" — o
                    # valor vem na linha seguinte ("= (L30.1(af)) | 0,00").
                    proxima = linhas[i + 1].strip() if i + 1 < len(linhas) else ""
                    valores_prox = _valores_da_linha(proxima)
                    if valores_prox:
                        mde["cancelamento_rp"] = _para_decimal(valores_prox[-1])
                continue
            if "APLICA" in texto and "EM MDE SOBRE A RECEITA RESULTANTE DE IMPOSTOS" in texto:
                valores = _valores_da_linha(texto)
                mde["valor_exigido"] = _para_decimal(valores[0])
                mde["valor_aplicado"] = _para_decimal(valores[1])
                mde["percentual_aplicado"] = _para_decimal(valores[2])
                continue
            if "Nimo de 70% do FUNDEB na Remunera" in texto or "nimo de 70% do FUNDEB na Remunera" in texto:
                valores = _valores_da_linha(texto)
                magisterio["valor_exigido"] = _para_decimal(valores[0])
                magisterio["valor_aplicado"] = _para_decimal(valores[1])
                magisterio["percentual_aplicado"] = _para_decimal(valores[3])
                continue
            # Linha 15.2 — mesma seção do magistério (15.1), mínimo de 4%
            # do FUNDEB na criação de matrículas em ETI. Match a partir de
            # "nimo de 4%..." (sem o "Mí" inicial) pelo mesmo motivo do
            # 15.1 acima: o "í" sai como caractere de substituição (U+FFFD)
            # na extração de texto, então casar a partir da letra seguinte
            # evita depender de como esse caractere é codificado.
            if "Nimo de 4% do FUNDEB na cria" in texto or "nimo de 4% do FUNDEB na cria" in texto:
                valores = _valores_da_linha(texto)
                eti_fundeb["valor_exigido"] = _para_decimal(valores[0])
                eti_fundeb["valor_aplicado"] = _para_decimal(valores[1])
                eti_fundeb["percentual_aplicado"] = _para_decimal(valores[3])
                continue
            # Linha 16 — mesma seção "INDICADORES - Art.212-A", logo após o
            # magistério: aplicação do VAAT (Complementação da União ao
            # FUNDEB) em educação infantil. O relatório não imprime um %
            # mínimo fixo aqui (só valor exigido/aplicado), por isso o
            # model compara os dois valores em vez de um percentual.
            if re.match(r"^16\s*-.*\(VAAT\)\s*educa", texto):
                valores = _valores_da_linha(texto)
                vaat_ed_infantil["valor_exigido"] = _para_decimal(valores[0])
                vaat_ed_infantil["valor_aplicado"] = _para_decimal(valores[1])
                vaat_ed_infantil["percentual_aplicado"] = _para_decimal(valores[3])
                continue
            # Linha 17 — mínimo de 15% do VAAT aplicado em despesas de
            # capital (Lei 14.113/2020, art.25).
            if re.match(r"^17\s*-.*VAAT em Despesas de Capital", texto):
                valores = _valores_da_linha(texto)
                vaat_capital["valor_exigido"] = _para_decimal(valores[0])
                vaat_capital["valor_aplicado"] = _para_decimal(valores[1])
                vaat_capital["percentual_aplicado"] = _para_decimal(valores[3])
                continue
            # Linha 18 — limite de 10% de superávit do FUNDEB não
            # aplicado (Lei 14.113/2020, art.25, §3º). 5 valores na
            # própria linha: máximo permitido | não aplicado | não
            # aplicado após ajuste | excedente ao máximo permitido | %.
            if re.match(r"^18\s*-", texto):
                valores = _valores_da_linha(texto)
                fundeb_nao_aplicado["valor_maximo_permitido"] = _para_decimal(valores[0])
                fundeb_nao_aplicado["valor_nao_aplicado"] = _para_decimal(valores[1])
                fundeb_nao_aplicado["valor_nao_aplicado_apos_ajuste"] = _para_decimal(valores[2])
                fundeb_nao_aplicado["valor_excedente_ao_maximo_permitido"] = _para_decimal(valores[3])
                fundeb_nao_aplicado["percentual_nao_aplicado"] = _para_decimal(valores[4])
                continue
            # Linha 19 — reprogramação do FUNDEB (aplicação do superávit
            # do exercício anterior). 5 valores na própria linha, mesma
            # ordem usada pelos sub-itens 19.1/19.2 abaixo. O 5º valor (a
            # coluna "saldo" do próprio relatório) é lido mas descartado —
            # ver `_saldo_a_aplicar`.
            if re.match(r"^19\s*-", texto):
                valores = _valores_da_linha(texto)
                fundeb_reprogramacao["valor_superavit_permitido_exercicio_anterior"] = _para_decimal(valores[0])
                fundeb_reprogramacao["valor_nao_aplicado_exercicio_anterior"] = _para_decimal(valores[1])
                fundeb_reprogramacao["valor_aplicado_ate_primeiro_quadrimestre"] = _para_decimal(valores[2])
                fundeb_reprogramacao["valor_aplicado_apos_primeiro_quadrimestre"] = _para_decimal(valores[3])
                fundeb_reprogramacao["valor_nao_aplicado_ate_primeiro_quadrimestre_atual"] = _saldo_a_aplicar(
                    fundeb_reprogramacao["valor_nao_aplicado_exercicio_anterior"],
                    fundeb_reprogramacao["valor_aplicado_ate_primeiro_quadrimestre"],
                )
                continue
            # Linhas 19.1/19.2 — mesmo quirk de quebra de linha da "27 -
            # Cancelamento" do MDE: o rótulo é longo demais e quebra
            # antes da coluna de valor, que sai sozinha na linha seguinte.
            if re.match(r"^19\.1\s*-", texto):
                valores = _valores_da_linha(texto)
                if not any(v.strip() for v in valores):
                    valores = _valores_da_linha(linhas[i + 1].strip()) if i + 1 < len(linhas) else []
                if len(valores) >= 5:
                    origem_impostos = {
                        "origem": "IMPOSTOS",
                        "valor_superavit_permitido_exercicio_anterior": _para_decimal(valores[0]),
                        "valor_nao_aplicado_exercicio_anterior": _para_decimal(valores[1]),
                        "valor_aplicado_ate_primeiro_quadrimestre": _para_decimal(valores[2]),
                        "valor_aplicado_apos_primeiro_quadrimestre": _para_decimal(valores[3]),
                        "valor_nao_aplicado_ate_primeiro_quadrimestre_atual": _saldo_a_aplicar(
                            _para_decimal(valores[1]), _para_decimal(valores[2])
                        ),
                    }
                continue
            if re.match(r"^19\.2\s*-", texto):
                valores = _valores_da_linha(texto)
                if not any(v.strip() for v in valores):
                    valores = _valores_da_linha(linhas[i + 1].strip()) if i + 1 < len(linhas) else []
                if len(valores) >= 5:
                    origem_uniao = {
                        "origem": "UNIAO",
                        "valor_superavit_permitido_exercicio_anterior": _para_decimal(valores[0]),
                        "valor_nao_aplicado_exercicio_anterior": _para_decimal(valores[1]),
                        "valor_aplicado_ate_primeiro_quadrimestre": _para_decimal(valores[2]),
                        "valor_aplicado_apos_primeiro_quadrimestre": _para_decimal(valores[3]),
                        "valor_nao_aplicado_ate_primeiro_quadrimestre_atual": _saldo_a_aplicar(
                            _para_decimal(valores[1]), _para_decimal(valores[2])
                        ),
                    }
                continue

        if "valor_exigido" in mde:
            mde["minimo_constitucional"] = mde["valor_exigido"]
        for campo in ("despesa_mde_empenhada", "despesa_mde_liquidada", "despesa_mde_paga",
                      "fundeb_transferido", "excedente_fundeb_nao_aplicado", "cancelamento_rp"):
            mde.setdefault(campo, "0")
        mde["itens_receita"] = itens_receita_mde

        fundeb_reprogramacao["origens"] = [o for o in (origem_impostos, origem_uniao) if o]

        if bimestre is None or exercicio is None:
            resultado.avisos.append("Período (bimestre/exercício) não identificado no cabeçalho do relatório.")

        campos_mde = [
            "receita_impostos", "receita_transferencias", "base_calculo", "minimo_constitucional",
            "despesa_mde_empenhada", "despesa_mde_liquidada", "despesa_mde_paga",
            "fundeb_transferido", "excedente_fundeb_nao_aplicado", "cancelamento_rp",
            "valor_exigido", "valor_aplicado", "percentual_aplicado",
        ]
        faltando_mde = [c for c in campos_mde if c not in mde]
        if faltando_mde:
            resultado.avisos.append(f"MDE: campos não encontrados na seção de apuração: {faltando_mde}")
        else:
            mde["tipo"] = "mde"
            mde["bimestre"] = bimestre
            mde["exercicio"] = exercicio
            resultado.linhas.append(mde)

        campos_magisterio = ["fundeb_receita_total", "valor_exigido", "valor_aplicado", "percentual_aplicado"]
        faltando_magisterio = [c for c in campos_magisterio if c not in magisterio]
        if faltando_magisterio:
            resultado.avisos.append(f"Magistério/FUNDEB: campos não encontrados na seção de apuração: {faltando_magisterio}")
        else:
            magisterio["tipo"] = "magisterio"
            magisterio["bimestre"] = bimestre
            magisterio["exercicio"] = exercicio
            resultado.linhas.append(magisterio)

        campos_eti_fundeb = ["fundeb_receita_total", "valor_exigido", "valor_aplicado", "percentual_aplicado"]
        faltando_eti_fundeb = [c for c in campos_eti_fundeb if c not in eti_fundeb]
        if faltando_eti_fundeb:
            resultado.avisos.append(f"FUNDEB ETI (4%): campos não encontrados na seção de apuração: {faltando_eti_fundeb}")
        else:
            eti_fundeb["tipo"] = "eti_fundeb"
            eti_fundeb["bimestre"] = bimestre
            eti_fundeb["exercicio"] = exercicio
            resultado.linhas.append(eti_fundeb)

        campos_vaat = ["valor_exigido", "valor_aplicado", "percentual_aplicado"]
        faltando_vaat_ed_infantil = [c for c in campos_vaat if c not in vaat_ed_infantil]
        if faltando_vaat_ed_infantil:
            resultado.avisos.append(
                f"VAAT Educação Infantil: campos não encontrados na seção de apuração: {faltando_vaat_ed_infantil}"
            )
        else:
            vaat_ed_infantil["tipo"] = "vaat_educacao_infantil"
            vaat_ed_infantil["bimestre"] = bimestre
            vaat_ed_infantil["exercicio"] = exercicio
            resultado.linhas.append(vaat_ed_infantil)

        faltando_vaat_capital = [c for c in campos_vaat if c not in vaat_capital]
        if faltando_vaat_capital:
            resultado.avisos.append(
                f"VAAT Despesa de Capital: campos não encontrados na seção de apuração: {faltando_vaat_capital}"
            )
        else:
            vaat_capital["tipo"] = "vaat_despesa_capital"
            vaat_capital["bimestre"] = bimestre
            vaat_capital["exercicio"] = exercicio
            resultado.linhas.append(vaat_capital)

        campos_fundeb_nao_aplicado = [
            "valor_maximo_permitido", "valor_nao_aplicado", "valor_nao_aplicado_apos_ajuste",
            "valor_excedente_ao_maximo_permitido", "percentual_nao_aplicado",
        ]
        faltando_fundeb_nao_aplicado = [c for c in campos_fundeb_nao_aplicado if c not in fundeb_nao_aplicado]
        if faltando_fundeb_nao_aplicado:
            resultado.avisos.append(
                f"FUNDEB Valor Não Aplicado: campos não encontrados na seção de apuração: {faltando_fundeb_nao_aplicado}"
            )
        else:
            fundeb_nao_aplicado["tipo"] = "fundeb_nao_aplicado"
            fundeb_nao_aplicado["bimestre"] = bimestre
            fundeb_nao_aplicado["exercicio"] = exercicio
            resultado.linhas.append(fundeb_nao_aplicado)

        campos_fundeb_reprogramacao = [
            "valor_superavit_permitido_exercicio_anterior", "valor_nao_aplicado_exercicio_anterior",
            "valor_aplicado_ate_primeiro_quadrimestre", "valor_aplicado_apos_primeiro_quadrimestre",
            "valor_nao_aplicado_ate_primeiro_quadrimestre_atual",
        ]
        faltando_fundeb_reprogramacao = [c for c in campos_fundeb_reprogramacao if c not in fundeb_reprogramacao]
        if faltando_fundeb_reprogramacao:
            resultado.avisos.append(
                f"FUNDEB Reprogramação: campos não encontrados na seção de apuração: {faltando_fundeb_reprogramacao}"
            )
        else:
            # A partir de 2026 o relatório parou de imprimir o
            # detalhamento 19.1/19.2 (origem por impostos/União) — a
            # linha 19 (combinada) continua vindo normalmente. Isso NÃO
            # pode bloquear a gravação da apuração principal: só vira um
            # aviso informativo, e `origens` fica vazia (a tabela filha
            # `ApuracaoReprogramacaoFundebOrigem` é opcional por design).
            if len(fundeb_reprogramacao["origens"]) < 2:
                resultado.avisos.append(
                    "FUNDEB Reprogramação: sub-itens 19.1/19.2 (origem por impostos/União) não encontrados "
                    "neste relatório — gravando só o total combinado (linha 19)."
                )
            fundeb_reprogramacao["tipo"] = "fundeb_reprogramacao"
            fundeb_reprogramacao["bimestre"] = bimestre
            fundeb_reprogramacao["exercicio"] = exercicio
            resultado.linhas.append(fundeb_reprogramacao)

        return resultado


REGISTRY: dict[tuple[str, str], type[ParserBase]] = {
    ("ASPEC", "RREO_MDE"): RREOMDEASPECParser,
}
