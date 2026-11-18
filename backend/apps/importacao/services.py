"""
Serviços de importação: gravam no banco os resultados já normalizados dos
parsers (ver apps/importacao/parsers/).

- importar_estrutura_organizacional: a partir da "Estrutura organizacional"
  do ASPEC, cadastra Unidade Gestora/Órgão/Unidade Orçamentária com nomes
  reais (substitui os placeholders "(a definir)") e, principalmente, com a
  Unidade Gestora correta de cada unidade orçamentária — é a fonte de
  verdade para esse mapeamento e deve rodar antes de qualquer outra
  importação que crie Órgão/Unidade Orçamentária.
- seed_catalogos_loa: a partir do "Relacionamento das ações" do ASPEC,
  cadastra Função/Subfunção (catálogos nacionais) e Programa/Ação
  (catálogos da LOA) com os nomes oficiais.
- importar_execucao_orcamentaria: a partir do "Demonstrativo Resumido da
  Despesa" do ASPEC (balancete mensal em PDF), cadastra Órgão/Unidade
  Orçamentária e grava as dotações (RubricaOrcamentaria) e a execução
  mensal. Mantido por compatibilidade com o histórico já importado, mas
  não é mais o caminho usado para dados novos — ver as duas próximas.
- importar_dotacoes_loa: a partir do "Movimentos de Despesa Fixada" do
  ASPEC (a LOA com valores), cria a RubricaOrcamentaria com
  origem_dotacao=ORCAMENTO. É o caminho atual (substitui o balancete em
  PDF) para a dotação inicial de cada rubrica.
- importar_fichas_despesa: a partir da "Tabela de fichas de despesa" do
  ASPEC — que já classifica nativamente cada combinação como Orçamento/
  Crédito Suplementar/Crédito Especial —, refina origem_dotacao com essa
  granularidade e cria (com dotacao_inicial=0) as combinações previstas
  mas ainda sem valor fixado. Roda depois de importar_dotacoes_loa.
- importar_empenhos: a partir do relatório de empenhos do ASPEC (planilha,
  uma por mês), grava o detalhamento por empenho (Empenho/EmpenhoMovimento).
  Quando uma classificação não tem RubricaOrcamentaria ainda (não prevista
  na LOA), cria uma nova com origem_dotacao=CREDITO_ADICIONAL — é o
  caminho atual (substitui o balancete em PDF) para dotações que só
  aparecem durante a execução do ano.
- importar_fontes_recursos: a partir de "Fontes de recursos" do ASPEC,
  atualiza nome/tipo de toda FonteRecursos já cadastrada com aquele
  código (em qualquer UG) — substitui os placeholders "(a definir)".

Mantidos desacoplados do parser para que outros sistemas de origem, no
futuro, produzam o mesmo formato normalizado e reaproveitem esta gravação.
"""

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Max, Sum

from apps.execucao_fiscal.models import (
    ApuracaoASPS,
    ApuracaoDTP,
    ApuracaoETIFundeb,
    ApuracaoMagisterioFundeb,
    ApuracaoMDE,
    ApuracaoMDEReceitaItem,
    ApuracaoReprogramacaoFundeb,
    ApuracaoReprogramacaoFundebOrigem,
    ApuracaoVAATDespesaCapital,
    ApuracaoVAATEducacaoInfantil,
    ApuracaoValorNaoAplicadoFundeb,
)
from apps.financeiro.models import (
    RestoAPagar,
    SaldoBalancoConta,
    SaldoBalancoContaFonte,
    SaldoContaBancaria,
    SaldoContaBancariaFonte,
)
from apps.fiscal.models import LancamentoExecucaoReceita, RubricaReceita
from apps.municipios.models import Municipio, Orgao, PoderEnum, UnidadeGestora, UnidadeOrcamentaria
from apps.orcamento.models import (
    LOA,
    Acao,
    CategoriaEconomica,
    ElementoDespesa,
    Empenho,
    EmpenhoMovimento,
    Exercicio,
    FonteRecursos,
    Funcao,
    GrupoNaturezaDespesa,
    LancamentoExecucaoOrcamentaria,
    ModalidadeAplicacao,
    OrigemDotacao,
    Programa,
    RubricaOrcamentaria,
    Subelemento,
    Subfuncao,
)

from .parsers.base import ResultadoParsing


@dataclass
class ResultadoImportacaoEstrutura:
    unidades_gestoras_criadas: int = 0
    orgaos_criados: int = 0
    unidades_orcamentarias_criadas: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_estrutura_organizacional(
    resultado: ResultadoParsing, municipio: Municipio
) -> ResultadoImportacaoEstrutura:
    """
    Cadastra Unidade Gestora/Órgão/Unidade Orçamentária a partir da
    "Estrutura organizacional" do ASPEC — fonte de verdade para nomes reais
    e para qual Unidade Gestora executa cada unidade orçamentária (ver
    nota em apps.municipios.models.Orgao). Roda primeiro que tudo: as
    demais importações só fazem lookup dessa estrutura, nunca a criam.

    Reimportar é seguro e atualiza nomes/UG caso tenham mudado — esse
    relatório é sempre a referência mais atual.
    """
    out = ResultadoImportacaoEstrutura(avisos=list(resultado.avisos))

    ugs_por_nome: dict[str, UnidadeGestora] = {
        ug.nome: ug for ug in UnidadeGestora.objects.filter(municipio=municipio)
    }
    proximo_codigo = 1 + max(
        (int(c) for c in UnidadeGestora.objects.filter(municipio=municipio).values_list("codigo", flat=True)
         if c.isdigit()),
        default=0,
    )

    for linha in resultado.linhas:
        ug = ugs_por_nome.get(linha["ug_nome"])
        if ug is None:
            poder = PoderEnum.LEGISLATIVO if "camara" in linha["ug_nome"].lower() else PoderEnum.EXECUTIVO
            ug = UnidadeGestora.objects.create(
                municipio=municipio, codigo=f"{proximo_codigo:02d}", nome=linha["ug_nome"], poder=poder,
            )
            proximo_codigo += 1
            out.unidades_gestoras_criadas += 1
            ugs_por_nome[linha["ug_nome"]] = ug

        orgao, orgao_criado = Orgao.objects.update_or_create(
            municipio=municipio, codigo=linha["orgao_codigo"], defaults={"nome": linha["orgao_nome"]},
        )
        out.orgaos_criados += orgao_criado

        _, unidade_criada = UnidadeOrcamentaria.objects.update_or_create(
            orgao=orgao, codigo=linha["unidade_codigo"],
            defaults={"nome": linha["unidade_nome"], "unidade_gestora": ug},
        )
        out.unidades_orcamentarias_criadas += unidade_criada

    return out


@dataclass
class ResultadoSeedCatalogos:
    funcoes_criadas: int = 0
    subfuncoes_criadas: int = 0
    programas_criados: int = 0
    acoes_criadas: int = 0


@transaction.atomic
def seed_catalogos_loa(resultado: ResultadoParsing, loa: LOA) -> ResultadoSeedCatalogos:
    """Cadastra Função/Subfunção/Programa/Ação a partir do relacionamento de ações da LOA."""
    out = ResultadoSeedCatalogos()

    for linha in resultado.linhas:
        _, criada_f = Funcao.objects.get_or_create(
            codigo=linha.funcao_codigo, defaults={"nome": linha.funcao_nome}
        )
        out.funcoes_criadas += criada_f

        _, criada_sf = Subfuncao.objects.get_or_create(
            codigo=linha.subfuncao_codigo, defaults={"nome": linha.subfuncao_nome}
        )
        out.subfuncoes_criadas += criada_sf

        programa, criado_p = Programa.objects.get_or_create(
            loa=loa, codigo=linha.programa_codigo, defaults={"nome": linha.programa_nome}
        )
        out.programas_criados += criado_p

        _, criada_a = Acao.objects.get_or_create(
            programa=programa, codigo=linha.acao_codigo,
            defaults={"nome": linha.acao_nome, "tipo": linha.acao_tipo},
        )
        out.acoes_criadas += criada_a

    return out


@dataclass
class ResultadoImportacao:
    linhas_criadas: int = 0
    linhas_atualizadas: int = 0
    rubricas_criadas: int = 0
    orgaos_criados: int = 0
    unidades_orcamentarias_criadas: int = 0
    avisos: list[str] | None = None


def _classificacao_elemento(elemento_codigo: str) -> tuple[str, str, str, str, str]:
    """'3.1.90.04.00' -> ('3', '1', '90', '04', '00')."""
    return tuple(elemento_codigo.split("."))  # type: ignore[return-value]


@transaction.atomic
def importar_execucao_orcamentaria(
    resultado: ResultadoParsing,
    municipio: Municipio,
    numero_lei_loa_padrao: str = "(a definir)",
    importacao=None,
) -> ResultadoImportacao:
    """
    Grava no banco as linhas já parseadas de um relatório ASPEC de execução
    orçamentária (balancete). O relatório mistura unidades de várias
    Unidades Gestoras reais (ver nota em apps.municipios.models.Orgao), e a
    UG de cada linha é resolvida pela Unidade Orçamentária já cadastrada
    por `importar_estrutura_organizacional` — que precisa ter rodado antes.
    Este serviço nunca cria Órgão/Unidade Orçamentária, só os busca.

    Os catálogos de Função/Subfunção/Programa/Ação também precisam já
    existir (ver seed_catalogos_loa) — se uma combinação não for
    encontrada, a linha é reportada em avisos e ignorada.
    """
    ano = resultado.metadados.get("ano")
    mes_referencia = resultado.metadados.get("mes_referencia")
    if not ano or not mes_referencia:
        raise ValueError("Resultado de parsing sem ano/mês de referência identificados.")

    out = ResultadoImportacao(avisos=list(resultado.avisos))

    exercicio, _ = Exercicio.objects.get_or_create(
        municipio=municipio, ano=ano,
        defaults={"status": "EM_EXECUCAO"},
    )
    loa, _ = LOA.objects.get_or_create(
        exercicio=exercicio,
        defaults={
            "numero_lei": numero_lei_loa_padrao,
            "valor_total_receita_prevista": Decimal("0"),
            "valor_total_despesa_fixada": Decimal("0"),
        },
    )

    cache_unidades_orc: dict[str, UnidadeOrcamentaria] = {}
    cache_rubricas: dict[tuple, RubricaOrcamentaria] = {}

    for linha in resultado.linhas:
        codigo_unidade = linha["unidade_codigo"]  # "0201" -> órgão "02" + unidade orç. "01"
        orgao_codigo, unidade_orc_codigo = codigo_unidade[:2], codigo_unidade[2:4]

        unidade_orc = cache_unidades_orc.get(codigo_unidade)
        if unidade_orc is None:
            try:
                unidade_orc = UnidadeOrcamentaria.objects.select_related("orgao", "unidade_gestora").get(
                    orgao__municipio=municipio, orgao__codigo=orgao_codigo, codigo=unidade_orc_codigo,
                )
            except UnidadeOrcamentaria.DoesNotExist:
                out.avisos.append(
                    f"Unidade orçamentária {orgao_codigo}{unidade_orc_codigo} não encontrada — rode "
                    f"importar_estrutura_organizacional antes."
                )
                continue
            cache_unidades_orc[codigo_unidade] = unidade_orc
        orgao = unidade_orc.orgao
        unidade_gestora = unidade_orc.unidade_gestora

        try:
            funcao = Funcao.objects.get(codigo=linha["funcao"])
            subfuncao = Subfuncao.objects.get(codigo=linha["subfuncao"])
            programa = Programa.objects.get(loa=loa, codigo=linha["programa"])
            acao = Acao.objects.get(programa=programa, codigo=linha["acao"])
        except (Funcao.DoesNotExist, Subfuncao.DoesNotExist, Programa.DoesNotExist, Acao.DoesNotExist):
            out.avisos.append(
                f"Classificação não encontrada nos catálogos da LOA (rode seed_catalogos_loa antes): "
                f"função={linha['funcao']} subfunção={linha['subfuncao']} "
                f"programa={linha['programa']} ação={linha['acao']}"
            )
            continue

        cod_categoria, cod_grupo, cod_modalidade, cod_elemento, cod_subelemento = (
            _classificacao_elemento(linha["elemento_codigo"])
        )
        categoria_economica, _ = CategoriaEconomica.objects.get_or_create(
            codigo=cod_categoria, defaults={"nome": "(a definir)"}
        )
        grupo_natureza, _ = GrupoNaturezaDespesa.objects.get_or_create(
            codigo=cod_grupo, defaults={"nome": "(a definir)"}
        )
        modalidade_aplicacao, _ = ModalidadeAplicacao.objects.get_or_create(
            codigo=cod_modalidade, defaults={"nome": "(a definir)"}
        )
        elemento_despesa, _ = ElementoDespesa.objects.get_or_create(
            codigo=cod_elemento, defaults={"nome": linha["elemento_nome"]}
        )
        subelemento, _ = Subelemento.objects.get_or_create(
            elemento=elemento_despesa, codigo=cod_subelemento, defaults={"nome": linha["elemento_nome"]}
        )
        fonte_recursos, _ = FonteRecursos.objects.get_or_create(
            codigo=linha["fonte_recursos"], defaults={"nome": "(a definir)"}
        )

        chave_rubrica = (
            orgao.id, unidade_orc.id, funcao.id, subfuncao.id, programa.id, acao.id,
            categoria_economica.id, grupo_natureza.id, modalidade_aplicacao.id,
            elemento_despesa.id, subelemento.id, fonte_recursos.id,
        )
        rubrica = cache_rubricas.get(chave_rubrica)
        if rubrica is None:
            rubrica, criada = RubricaOrcamentaria.objects.get_or_create(
                loa=loa,
                unidade_gestora=unidade_gestora,
                orgao=orgao,
                unidade_orcamentaria=unidade_orc,
                funcao=funcao,
                subfuncao=subfuncao,
                programa=programa,
                acao=acao,
                categoria_economica=categoria_economica,
                grupo_natureza_despesa=grupo_natureza,
                modalidade_aplicacao=modalidade_aplicacao,
                elemento_despesa=elemento_despesa,
                subelemento=subelemento,
                fonte_recursos=fonte_recursos,
                defaults={"dotacao_inicial": linha["dotacao_inicial"]},
            )
            if criada:
                out.rubricas_criadas += 1
            cache_rubricas[chave_rubrica] = rubrica

        mes_anterior = LancamentoExecucaoOrcamentaria.objects.filter(
            rubrica=rubrica, mes_referencia__lt=mes_referencia
        ).order_by("-mes_referencia").first()

        def _delta(campo_acumulado: str) -> Decimal:
            acumulado = linha[campo_acumulado]
            anterior = getattr(mes_anterior, campo_acumulado) if mes_anterior else Decimal("0")
            return acumulado - anterior

        dotacao_atualizada = (
            linha["dotacao_inicial"] + linha["creditos_adicionais"] - linha["anulacoes"]
        )

        _, criado_lancamento = LancamentoExecucaoOrcamentaria.objects.update_or_create(
            rubrica=rubrica,
            mes_referencia=mes_referencia,
            defaults={
                "dotacao_inicial": linha["dotacao_inicial"],
                "creditos_suplementares": linha["creditos_adicionais"],
                "creditos_especiais": Decimal("0"),
                "anulacoes": linha["anulacoes"],
                "dotacao_atualizada": dotacao_atualizada,
                "empenhado_no_mes": _delta("empenhado_acumulado"),
                "empenhado_acumulado": linha["empenhado_acumulado"],
                "liquidado_no_mes": _delta("liquidado_acumulado"),
                "liquidado_acumulado": linha["liquidado_acumulado"],
                "pago_no_mes": _delta("pago_acumulado"),
                "pago_acumulado": linha["pago_acumulado"],
                "importacao": importacao,
            },
        )
        if criado_lancamento:
            out.linhas_criadas += 1
        else:
            out.linhas_atualizadas += 1

    return out


@dataclass
class ResultadoGeracaoExecucaoPorEmpenhos:
    rubricas_processadas: int = 0
    linhas_criadas: int = 0
    linhas_atualizadas: int = 0
    avisos: list[str] | None = None

    def __post_init__(self):
        if self.avisos is None:
            self.avisos = []


@transaction.atomic
def gerar_execucao_orcamentaria_por_empenhos(
    municipio: Municipio, mes_referencia: int
) -> ResultadoGeracaoExecucaoPorEmpenhos:
    """
    Gera/atualiza LancamentoExecucaoOrcamentaria de um mês agregando
    diretamente Empenho/EmpenhoMovimento por RubricaOrcamentaria, sem
    depender de balancete em PDF — fonte atual de execução de despesa a
    partir do mês em que o ASPEC deixou de fornecer balancete (nunca houve
    BR09 em diante). `empenhado/liquidado/pago_no_mes` vêm da soma dos
    EmpenhoMovimento daquele mês; os acumulados somam o acumulado do mês
    anterior já gravado (seja ele de balancete ou desta mesma função) com o
    delta do mês — mesma lógica de encadeamento mês-a-mês do balancete.

    Dotação não tem mais granularidade mensal nesta fonte (o balancete era
    quem reportava créditos/anulações por mês): nenhum crédito/anulação
    NOVO é capturado por este mês (`creditos_suplementares`/`creditos_
    especiais`/`anulacoes` ficam em zero, já que não há relatório que
    informe isso a partir daqui). `dotacao_atualizada`, porém, **encadeia
    do mês anterior** (balancete ou já gerado por esta função), mesma
    lógica dos acumulados de empenhado/liquidado/pago logo abaixo — nunca
    reseta pra `RubricaOrcamentaria.dotacao_inicial` quando já existe
    histórico. Bug real corrigido 2026-11-12 (usuário: "Dotação Atualizada
    R$250.000.000,00 está trazendo o valor da dotação inicial,
    desconsiderando os créditos adicionais e reduções"): a versão anterior
    usava `rubrica.dotacao_inicial` direto, o que **descartava** os
    R$79.095.614,42 de créditos suplementares e R$31.133.383,98 de
    anulações já acumulados até agosto (via balancete) assim que setembro
    (1º mês gerado por esta função) era processado — dotação atualizada
    "voltava" de R$297.962.230,44 pra R$250.000.000,00 de uma hora pra
    outra, uma regressão visível no relatório, não só uma limitação de
    granularidade futura.

    Gera uma linha por RubricaOrcamentaria do município, mesmo sem nenhum
    movimento no mês (delta zero), para manter o relatório completo — é o
    mesmo comportamento do balancete, que reportava toda rubrica existente.
    """
    out = ResultadoGeracaoExecucaoPorEmpenhos()

    rubricas = RubricaOrcamentaria.objects.filter(unidade_gestora__municipio=municipio)

    for rubrica in rubricas:
        out.rubricas_processadas += 1

        agregado = EmpenhoMovimento.objects.filter(
            empenho__rubrica=rubrica, mes_referencia=mes_referencia
        ).aggregate(
            empenhado=Sum("valor_empenho_no_mes"),
            liquidado=Sum("valor_liquidado_no_mes"),
            pago=Sum("valor_pago_no_mes"),
        )
        empenhado_no_mes = agregado["empenhado"] or Decimal("0")
        liquidado_no_mes = agregado["liquidado"] or Decimal("0")
        pago_no_mes = agregado["pago"] or Decimal("0")

        mes_anterior = (
            LancamentoExecucaoOrcamentaria.objects.filter(
                rubrica=rubrica, mes_referencia__lt=mes_referencia
            )
            .order_by("-mes_referencia")
            .first()
        )
        empenhado_acumulado = (
            mes_anterior.empenhado_acumulado if mes_anterior else Decimal("0")
        ) + empenhado_no_mes
        liquidado_acumulado = (
            mes_anterior.liquidado_acumulado if mes_anterior else Decimal("0")
        ) + liquidado_no_mes
        pago_acumulado = (
            mes_anterior.pago_acumulado if mes_anterior else Decimal("0")
        ) + pago_no_mes
        dotacao_atualizada = mes_anterior.dotacao_atualizada if mes_anterior else rubrica.dotacao_inicial

        _, criado = LancamentoExecucaoOrcamentaria.objects.update_or_create(
            rubrica=rubrica,
            mes_referencia=mes_referencia,
            defaults={
                "dotacao_inicial": rubrica.dotacao_inicial,
                "creditos_suplementares": Decimal("0"),
                "creditos_especiais": Decimal("0"),
                "anulacoes": Decimal("0"),
                "dotacao_atualizada": dotacao_atualizada,
                "empenhado_no_mes": empenhado_no_mes,
                "empenhado_acumulado": empenhado_acumulado,
                "liquidado_no_mes": liquidado_no_mes,
                "liquidado_acumulado": liquidado_acumulado,
                "pago_no_mes": pago_no_mes,
                "pago_acumulado": pago_acumulado,
            },
        )
        if criado:
            out.linhas_criadas += 1
        else:
            out.linhas_atualizadas += 1

    return out


@dataclass
class ResultadoImportacaoDotacoesLOA:
    rubricas_criadas: int = 0
    rubricas_atualizadas: int = 0
    orgaos_criados: int = 0
    unidades_orcamentarias_criadas: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_dotacoes_loa(
    resultado: ResultadoParsing,
    municipio: Municipio,
    numero_lei_loa_padrao: str = "(a definir)",
    importacao=None,
) -> ResultadoImportacaoDotacoesLOA:
    """
    Grava a dotação inicial por rubrica (origem_dotacao=ORCAMENTO) a partir
    do "Movimentos de Despesa Fixada" (a LOA com valores) já parseado. O
    arquivo é consolidado (mistura as Unidades Gestoras do município), então
    a UG de cada linha é resolvida pela Unidade Orçamentária já cadastrada
    por importar_estrutura_organizacional — que precisa ter rodado antes.
    Este serviço nunca cria Órgão/Unidade Orçamentária, só os busca. Os
    catálogos de Função/Subfunção/Programa/Ação também precisam já existir
    (ver seed_catalogos_loa).

    Se a rubrica já existir (ex.: criada antes pelo balancete em PDF ou por
    uma importação anterior deste mesmo relatório), sua dotacao_inicial e
    origem_dotacao são atualizadas — este relatório é a fonte de verdade
    para a dotação original.
    """
    ano = resultado.metadados.get("ano")
    if not ano:
        raise ValueError("Resultado de parsing sem ano/exercício identificado.")

    out = ResultadoImportacaoDotacoesLOA(avisos=list(resultado.avisos))

    exercicio, _ = Exercicio.objects.get_or_create(
        municipio=municipio, ano=ano, defaults={"status": "EM_EXECUCAO"}
    )
    loa, _ = LOA.objects.get_or_create(
        exercicio=exercicio,
        defaults={
            "numero_lei": numero_lei_loa_padrao,
            "valor_total_receita_prevista": Decimal("0"),
            "valor_total_despesa_fixada": Decimal("0"),
        },
    )

    cache_unidades_orc: dict[tuple, UnidadeOrcamentaria] = {}

    for linha in resultado.linhas:
        chave_unid = (linha["orgao_codigo"], linha["unidade_orc_codigo"])
        unidade_orc = cache_unidades_orc.get(chave_unid)
        if unidade_orc is None:
            try:
                unidade_orc = UnidadeOrcamentaria.objects.select_related("orgao", "unidade_gestora").get(
                    orgao__municipio=municipio, orgao__codigo=linha["orgao_codigo"],
                    codigo=linha["unidade_orc_codigo"],
                )
            except UnidadeOrcamentaria.DoesNotExist:
                out.avisos.append(
                    f"Unidade orçamentária {linha['orgao_codigo']}{linha['unidade_orc_codigo']} não "
                    f"encontrada — rode importar_estrutura_organizacional antes."
                )
                continue
            cache_unidades_orc[chave_unid] = unidade_orc
        orgao = unidade_orc.orgao
        unidade_gestora = unidade_orc.unidade_gestora

        try:
            funcao = Funcao.objects.get(codigo=linha["funcao"])
            subfuncao = Subfuncao.objects.get(codigo=linha["subfuncao"])
            programa = Programa.objects.get(loa=loa, codigo=linha["programa"])
            acao = Acao.objects.get(programa=programa, codigo=linha["acao"])
        except (Funcao.DoesNotExist, Subfuncao.DoesNotExist, Programa.DoesNotExist, Acao.DoesNotExist):
            out.avisos.append(
                f"Classificação não encontrada nos catálogos da LOA (rode seed_catalogos_loa antes): "
                f"função={linha['funcao']} subfunção={linha['subfuncao']} "
                f"programa={linha['programa']} ação={linha['acao']}"
            )
            continue

        categoria_economica, _ = CategoriaEconomica.objects.get_or_create(
            codigo=linha["categoria_economica"], defaults={"nome": "(a definir)"}
        )
        grupo_natureza, _ = GrupoNaturezaDespesa.objects.get_or_create(
            codigo=linha["grupo_natureza_despesa"], defaults={"nome": "(a definir)"}
        )
        modalidade_aplicacao, _ = ModalidadeAplicacao.objects.get_or_create(
            codigo=linha["modalidade_aplicacao"], defaults={"nome": "(a definir)"}
        )
        elemento_despesa, _ = ElementoDespesa.objects.get_or_create(
            codigo=linha["elemento_despesa"], defaults={"nome": "(a definir)"}
        )
        subelemento, _ = Subelemento.objects.get_or_create(
            elemento=elemento_despesa, codigo=linha["subelemento"], defaults={"nome": "(a definir)"}
        )
        fonte_recursos, _ = FonteRecursos.objects.get_or_create(
            codigo=linha["fonte_codigo"],
            defaults={"nome": linha["fonte_nome"]},
        )

        _, criada = RubricaOrcamentaria.objects.update_or_create(
            loa=loa,
            unidade_gestora=unidade_gestora,
            orgao=orgao,
            unidade_orcamentaria=unidade_orc,
            funcao=funcao,
            subfuncao=subfuncao,
            programa=programa,
            acao=acao,
            categoria_economica=categoria_economica,
            grupo_natureza_despesa=grupo_natureza,
            modalidade_aplicacao=modalidade_aplicacao,
            elemento_despesa=elemento_despesa,
            subelemento=subelemento,
            fonte_recursos=fonte_recursos,
            defaults={"dotacao_inicial": linha["valor"], "origem_dotacao": OrigemDotacao.ORCAMENTO},
        )
        if criada:
            out.rubricas_criadas += 1
        else:
            out.rubricas_atualizadas += 1

    return out


ORIGEM_FICHAS_MAP = {
    "ORCAMENTO": OrigemDotacao.ORCAMENTO,
    "CREDITO_SUPLEMENTAR": OrigemDotacao.CREDITO_SUPLEMENTAR,
    "CREDITO_ESPECIAL": OrigemDotacao.CREDITO_ESPECIAL,
}


@dataclass
class ResultadoImportacaoFichas:
    rubricas_criadas: int = 0
    rubricas_origem_corrigida: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_fichas_despesa(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoFichas:
    """
    A partir da "Tabela de fichas de despesa" do ASPEC — que classifica
    nativamente cada combinação como Orçamento/Crédito Suplementar/Crédito
    Especial, inclusive as que ainda não têm valor fixado —, corrige
    origem_dotacao com essa granularidade maior (ver nota em
    RubricaOrcamentaria) e cria com dotacao_inicial=0 as combinações que a
    LOA com valores ainda não cobre (um crédito suplementar/especial
    previsto mas não fixado ainda). Roda depois de importar_dotacoes_loa,
    antes de importar_aspec/importar_empenhos — assim, quando o empenho
    chegar, a rubrica (e sua origem correta) já existe.
    """
    out = ResultadoImportacaoFichas(avisos=list(resultado.avisos))

    exercicio = Exercicio.objects.filter(municipio=municipio).order_by("-ano").first()
    if exercicio is None or not hasattr(exercicio, "loa"):
        raise ValueError("Nenhum Exercício/LOA encontrado — rode importar_dotacoes_loa antes.")
    loa = exercicio.loa

    cache_unidades_orc: dict[tuple, UnidadeOrcamentaria] = {}

    for linha in resultado.linhas:
        origem = ORIGEM_FICHAS_MAP.get(linha["origem"])
        if origem is None:
            out.avisos.append(f"Origem de ficha não reconhecida: {linha['origem']!r}")
            continue

        chave_unid = (linha["orgao_codigo"], linha["unidade_orc_codigo"])
        unidade_orc = cache_unidades_orc.get(chave_unid)
        if unidade_orc is None:
            try:
                unidade_orc = UnidadeOrcamentaria.objects.select_related("orgao", "unidade_gestora").get(
                    orgao__municipio=municipio, orgao__codigo=linha["orgao_codigo"],
                    codigo=linha["unidade_orc_codigo"],
                )
            except UnidadeOrcamentaria.DoesNotExist:
                out.avisos.append(
                    f"Unidade orçamentária {linha['orgao_codigo']}{linha['unidade_orc_codigo']} não "
                    f"encontrada — rode importar_estrutura_organizacional antes."
                )
                continue
            cache_unidades_orc[chave_unid] = unidade_orc
        orgao = unidade_orc.orgao
        unidade_gestora = unidade_orc.unidade_gestora

        try:
            funcao = Funcao.objects.get(codigo=linha["funcao"])
            subfuncao = Subfuncao.objects.get(codigo=linha["subfuncao"])
            programa = Programa.objects.get(loa=loa, codigo=linha["programa"])
            acao = Acao.objects.get(programa=programa, codigo=linha["acao"])
        except (Funcao.DoesNotExist, Subfuncao.DoesNotExist, Programa.DoesNotExist, Acao.DoesNotExist):
            out.avisos.append(
                f"Classificação não encontrada nos catálogos da LOA (rode seed_catalogos_loa antes): "
                f"função={linha['funcao']} subfunção={linha['subfuncao']} "
                f"programa={linha['programa']} ação={linha['acao']}"
            )
            continue

        categoria_economica, _ = CategoriaEconomica.objects.get_or_create(
            codigo=linha["categoria_economica"], defaults={"nome": "(a definir)"}
        )
        grupo_natureza, _ = GrupoNaturezaDespesa.objects.get_or_create(
            codigo=linha["grupo_natureza_despesa"], defaults={"nome": "(a definir)"}
        )
        modalidade_aplicacao, _ = ModalidadeAplicacao.objects.get_or_create(
            codigo=linha["modalidade_aplicacao"], defaults={"nome": "(a definir)"}
        )
        elemento_despesa, _ = ElementoDespesa.objects.get_or_create(
            codigo=linha["elemento_despesa"], defaults={"nome": "(a definir)"}
        )
        subelemento, _ = Subelemento.objects.get_or_create(
            elemento=elemento_despesa, codigo=linha["subelemento"], defaults={"nome": "(a definir)"}
        )
        fonte_recursos, _ = FonteRecursos.objects.get_or_create(
            codigo=linha["fonte_codigo"], defaults={"nome": "(a definir)"}
        )

        rubrica, criada = RubricaOrcamentaria.objects.get_or_create(
            loa=loa,
            unidade_gestora=unidade_gestora,
            orgao=orgao,
            unidade_orcamentaria=unidade_orc,
            funcao=funcao,
            subfuncao=subfuncao,
            programa=programa,
            acao=acao,
            categoria_economica=categoria_economica,
            grupo_natureza_despesa=grupo_natureza,
            modalidade_aplicacao=modalidade_aplicacao,
            elemento_despesa=elemento_despesa,
            subelemento=subelemento,
            fonte_recursos=fonte_recursos,
            defaults={"dotacao_inicial": Decimal("0"), "origem_dotacao": origem},
        )
        if criada:
            out.rubricas_criadas += 1
        elif rubrica.origem_dotacao != origem:
            rubrica.origem_dotacao = origem
            rubrica.save(update_fields=["origem_dotacao"])
            out.rubricas_origem_corrigida += 1

    return out


@dataclass
class ResultadoImportacaoEmpenhos:
    empenhos_criados: int = 0
    empenhos_atualizados: int = 0
    rubricas_criadas: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_empenhos(
    resultado: ResultadoParsing,
    municipio: Municipio,
    importacao=None,
) -> ResultadoImportacaoEmpenhos:
    """
    Grava o detalhamento por empenho (Empenho/EmpenhoMovimento) a partir de
    um relatório de empenhos do ASPEC já parseado. A Unidade Gestora de
    cada linha é resolvida pela Unidade Orçamentária já cadastrada por
    importar_estrutura_organizacional — que precisa ter rodado antes —, e
    Função/Subfunção/Programa/Ação também precisam já existir (ver
    seed_catalogos_loa). Quando a RubricaOrcamentaria exata da linha não
    existe ainda (classificação não prevista na LOA importada), este
    serviço a cria com origem_dotacao=CREDITO_ADICIONAL e
    dotacao_inicial=0 — é assim que dotações não previstas na LOA entram no
    sistema, sem depender do balancete em PDF.
    """
    out = ResultadoImportacaoEmpenhos(avisos=list(resultado.avisos))

    cache_unidades_orc: dict[tuple, UnidadeOrcamentaria] = {}
    cache_rubricas: dict[tuple, RubricaOrcamentaria] = {}

    for linha in resultado.linhas:
        chave_unid = (linha["orgao_codigo"], linha["unidade_orc_codigo"])
        unidade_orc = cache_unidades_orc.get(chave_unid)
        if unidade_orc is None:
            try:
                unidade_orc = UnidadeOrcamentaria.objects.select_related("orgao", "unidade_gestora").get(
                    orgao__municipio=municipio, orgao__codigo=linha["orgao_codigo"],
                    codigo=linha["unidade_orc_codigo"],
                )
            except UnidadeOrcamentaria.DoesNotExist:
                out.avisos.append(
                    f"Empenho {linha['numero_empenho']}: unidade orçamentária "
                    f"{linha['orgao_codigo']}{linha['unidade_orc_codigo']} não encontrada — rode "
                    f"importar_estrutura_organizacional antes."
                )
                continue
            cache_unidades_orc[chave_unid] = unidade_orc
        orgao = unidade_orc.orgao
        unidade_gestora = unidade_orc.unidade_gestora

        exercicio = Exercicio.objects.filter(municipio=municipio, ano=linha["data_empenho"].year).first()
        if exercicio is None or not hasattr(exercicio, "loa"):
            out.avisos.append(
                f"Empenho {linha['numero_empenho']}: exercício/LOA {linha['data_empenho'].year} não encontrado."
            )
            continue
        loa = exercicio.loa

        chave_rubrica = (
            unidade_gestora.id, orgao.codigo, linha["unidade_orc_codigo"], linha["funcao"],
            linha["subfuncao"], linha["programa"], linha["acao"], linha["categoria_economica"],
            linha["grupo_natureza_despesa"], linha["modalidade_aplicacao"], linha["elemento_despesa"],
            linha["subelemento"], linha["fonte_codigo"],
        )
        rubrica = cache_rubricas.get(chave_rubrica)
        if rubrica is None:
            try:
                funcao = Funcao.objects.get(codigo=linha["funcao"])
                subfuncao = Subfuncao.objects.get(codigo=linha["subfuncao"])
                programa = Programa.objects.get(loa=loa, codigo=linha["programa"])
                acao = Acao.objects.get(programa=programa, codigo=linha["acao"])
            except (Funcao.DoesNotExist, Subfuncao.DoesNotExist, Programa.DoesNotExist, Acao.DoesNotExist):
                out.avisos.append(
                    f"Empenho {linha['numero_empenho']}: classificação funcional/programática não "
                    f"encontrada nos catálogos da LOA (rode seed_catalogos_loa antes): "
                    f"função={linha['funcao']} subfunção={linha['subfuncao']} "
                    f"programa={linha['programa']} ação={linha['acao']}"
                )
                continue

            categoria_economica, _ = CategoriaEconomica.objects.get_or_create(
                codigo=linha["categoria_economica"], defaults={"nome": "(a definir)"}
            )
            grupo_natureza, _ = GrupoNaturezaDespesa.objects.get_or_create(
                codigo=linha["grupo_natureza_despesa"], defaults={"nome": "(a definir)"}
            )
            modalidade_aplicacao, _ = ModalidadeAplicacao.objects.get_or_create(
                codigo=linha["modalidade_aplicacao"], defaults={"nome": "(a definir)"}
            )
            elemento_despesa, _ = ElementoDespesa.objects.get_or_create(
                codigo=linha["elemento_despesa"], defaults={"nome": "(a definir)"}
            )
            subelemento, _ = Subelemento.objects.get_or_create(
                elemento=elemento_despesa, codigo=linha["subelemento"], defaults={"nome": "(a definir)"}
            )
            fonte_recursos, _ = FonteRecursos.objects.get_or_create(
                codigo=linha["fonte_codigo"], defaults={"nome": "(a definir)"}
            )

            rubrica, rubrica_criada = RubricaOrcamentaria.objects.get_or_create(
                loa=loa,
                unidade_gestora=unidade_gestora,
                orgao=orgao,
                unidade_orcamentaria=unidade_orc,
                funcao=funcao,
                subfuncao=subfuncao,
                programa=programa,
                acao=acao,
                categoria_economica=categoria_economica,
                grupo_natureza_despesa=grupo_natureza,
                modalidade_aplicacao=modalidade_aplicacao,
                elemento_despesa=elemento_despesa,
                subelemento=subelemento,
                fonte_recursos=fonte_recursos,
                defaults={"dotacao_inicial": Decimal("0"), "origem_dotacao": OrigemDotacao.CREDITO_ADICIONAL},
            )
            if rubrica_criada:
                out.rubricas_criadas += 1
            cache_rubricas[chave_rubrica] = rubrica

        empenho, criado = Empenho.objects.update_or_create(
            unidade_gestora=unidade_gestora,
            numero=linha["numero_empenho"],
            defaults={
                "rubrica": rubrica,
                "data_empenho": linha["data_empenho"],
                "credor": linha["credor"],
                "historico": linha["historico"],
            },
        )
        if criado:
            out.empenhos_criados += 1
        else:
            out.empenhos_atualizados += 1

        # Cada linha da planilha é a movimentação DAQUELE MÊS para este
        # número de empenho (ver nota em Empenho) — não um total acumulado.
        # update_or_create por (empenho, mes_referencia) faz a reimportação
        # do mesmo mês substituir o movimento em vez de somar duas vezes.
        EmpenhoMovimento.objects.update_or_create(
            empenho=empenho,
            mes_referencia=linha["mes_referencia"],
            defaults={
                "valor_empenho_no_mes": linha["valor_empenho"],
                "valor_liquidado_no_mes": linha["valor_liquidado"],
                "valor_pago_no_mes": linha["valor_pago"],
                "importacao": importacao,
            },
        )
        empenho.recalcular_totais()

    return out


@dataclass
class ResultadoImportacaoFontes:
    fontes_atualizadas: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_fontes_recursos(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoFontes:
    """
    Atualiza nome/tipo de toda FonteRecursos já cadastrada com o código
    informado — `FonteRecursos` é um catálogo nacional (STN), sem escopo
    de UG nem de município (mesmo padrão já usado por `ElementoDespesa`/
    `ModalidadeAplicacao`/`GrupoNaturezaDespesa`/`CategoriaEconomica`), daí
    `municipio` não ser usado aqui — mantido no parâmetro só pela mesma
    assinatura `(resultado, municipio)` que todo `importar_*` deste módulo
    usa (o dispatcher chama todos genericamente). Não cria fontes novas
    (elas nascem via importar_dotacoes_loa/importar_empenhos, quando uma
    rubrica referencia um código ainda não visto).
    """
    out = ResultadoImportacaoFontes(avisos=list(resultado.avisos))

    for linha in resultado.linhas:
        atualizadas = FonteRecursos.objects.filter(
            codigo=linha["codigo"],
        ).update(nome=linha["nome"], tipo=linha["tipo"])
        out.fontes_atualizadas += atualizadas

    return out


def _resolver_fonte_por_nome(nome: str) -> tuple[FonteRecursos, bool]:
    """
    FICHAS_RECEITAS.PDF só dá o NOME da fonte (não o código, ao contrário
    das fontes do lado despesa). `FonteRecursos` é um catálogo nacional
    sem escopo de UG (ver nota em `importar_fontes_recursos`) — resolve em
    2 passos: (1) já existe uma FonteRecursos com esse nome (criada pelo
    lado despesa ou por uma importação de receita anterior); (2) nunca
    vista — cria com um código sintético ("RECxxxxx"), marcando que não
    veio do catálogo oficial.
    """
    fonte = FonteRecursos.objects.filter(nome__iexact=nome).first()
    if fonte:
        return fonte, False

    codigo_sintetico = f"REC{abs(hash(nome)) % 100000:05d}"
    fonte, criada = FonteRecursos.objects.get_or_create(
        codigo=codigo_sintetico, defaults={"nome": nome},
    )
    return fonte, criada


@dataclass
class ResultadoImportacaoFichasReceitas:
    rubricas_criadas: int = 0
    rubricas_atualizadas: int = 0
    fontes_criadas: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_fichas_receitas(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoFichasReceitas:
    """
    A partir de FICHAS_RECEITAS.PDF ("Classificação Econômica da Receita -
    Local") — a LOA de receita com valores —, cria/atualiza RubricaReceita
    (código × fonte, por Unidade Gestora arrecadadora). Único catálogo de
    receita disponível: ao contrário de despesa (LOA_DESPESAS + FICHAS.PDF
    em dois passos), este arquivo sozinho já cumpre o papel de dotação
    inicial com a granularidade final — não há um segundo refinamento.
    """
    out = ResultadoImportacaoFichasReceitas(avisos=list(resultado.avisos))

    exercicio = Exercicio.objects.filter(municipio=municipio).order_by("-ano").first()
    if exercicio is None or not hasattr(exercicio, "loa"):
        raise ValueError("Nenhum Exercício/LOA encontrado — rode importar_dotacoes_loa antes.")
    loa = exercicio.loa

    cache_ug: dict[str, UnidadeGestora] = {}

    for linha in resultado.linhas:
        ug = cache_ug.get(linha["unidade_gestora_codigo"])
        if ug is None:
            try:
                ug = UnidadeGestora.objects.get(municipio=municipio, codigo=linha["unidade_gestora_codigo"])
            except UnidadeGestora.DoesNotExist:
                out.avisos.append(f"Unidade Gestora {linha['unidade_gestora_codigo']!r} não encontrada.")
                continue
            cache_ug[linha["unidade_gestora_codigo"]] = ug

        fonte, fonte_criada = _resolver_fonte_por_nome(linha["fonte_nome"])
        if fonte_criada:
            out.fontes_criadas += 1

        rubrica, criada = RubricaReceita.objects.update_or_create(
            loa=loa, unidade_gestora=ug, codigo=linha["codigo"], fonte_recursos=fonte,
            defaults={"nome": linha["nome"], "valor_orcado": linha["valor_orcado"]},
        )
        if criada:
            out.rubricas_criadas += 1
        else:
            out.rubricas_atualizadas += 1

    return out




def _normalizar_nome(nome: str) -> str:
    """Minúsculas e sem acento — o mesmo "Camara"/"Câmara" sem-acento-no-PDF já visto em ESTRUTURA.pdf."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().lower()


def resolver_unidade_gestora_por_nome(municipio: Municipio, nome_relatorio: str | None) -> UnidadeGestora:
    """
    Resolve a Unidade Gestora pelo NOME impresso no cabeçalho do relatório
    (nunca pelo nome do arquivo — ver nota nos parsers de saldo). Comparação
    sem acento/caixa para não recriar o problema já visto com
    "Camara"/"Câmara" na importação da estrutura organizacional.
    """
    if not nome_relatorio:
        raise ValueError("Relatório sem Unidade Gestora identificável no cabeçalho — importação abortada.")
    alvo = _normalizar_nome(nome_relatorio)
    for ug in UnidadeGestora.objects.filter(municipio=municipio):
        if _normalizar_nome(ug.nome) == alvo:
            return ug
    raise ValueError(
        f"Unidade Gestora {nome_relatorio!r} (do cabeçalho do relatório) não encontrada em {municipio} — "
        f"confira se importar_estrutura já rodou e se o nome bate."
    )


@dataclass
class ResultadoImportacaoSaldoBalanco:
    contas_criadas: int = 0
    fontes_criadas: int = 0
    unidades_gestoras: list[str] | None = None
    data_referencia: str = ""
    avisos: list[str] | None = None


@transaction.atomic
def importar_saldo_balanco(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoSaldoBalanco:
    """
    A partir de "MOVIMENTOS DE SALDOS DE BALANÇO" (um único PDF cobrindo
    todas as UGs, desde 2026-11-12 — ver docstring do parser), grava
    SaldoBalancoConta/SaldoBalancoContaFonte. Data vem do cabeçalho/linhas
    do próprio relatório (`resultado.metadados`), nunca do nome do
    arquivo — valida isso antes de gravar qualquer coisa. Cada linha já
    carrega sua própria UG (`linha["unidade_gestora_nome"]`); agrupa por
    UG e reimporta cada uma independentemente — reimportar a mesma UG+data
    SUBSTITUI as contas dessa combinação (delete + recreate), já que o
    conjunto de contas de uma foto pode mudar entre reimportações; UGs não
    presentes neste arquivo não são tocadas.
    """
    data_referencia_texto = resultado.metadados.get("data_referencia")
    if not data_referencia_texto:
        raise ValueError("Data de referência não identificada no relatório — importação abortada.")
    data_referencia = datetime.strptime(data_referencia_texto, "%d/%m/%Y").date()

    linhas_por_ug: dict[str, list[dict]] = {}
    for linha in resultado.linhas:
        linhas_por_ug.setdefault(linha["unidade_gestora_nome"], []).append(linha)

    out = ResultadoImportacaoSaldoBalanco(
        avisos=list(resultado.avisos), unidades_gestoras=[], data_referencia=str(data_referencia)
    )

    for nome_ug, linhas_ug in linhas_por_ug.items():
        unidade_gestora = resolver_unidade_gestora_por_nome(municipio, nome_ug)
        out.unidades_gestoras.append(unidade_gestora.nome)

        SaldoBalancoConta.objects.filter(unidade_gestora=unidade_gestora, data_referencia=data_referencia).delete()

        cache_contas: dict[tuple[str, str], SaldoBalancoConta] = {}
        for linha in linhas_ug:
            chave_conta = (linha["categoria"], linha["codigo_conta"])
            conta = cache_contas.get(chave_conta)
            if conta is None:
                conta = SaldoBalancoConta.objects.create(
                    unidade_gestora=unidade_gestora,
                    data_referencia=data_referencia,
                    categoria=linha["categoria"],
                    codigo_conta=linha["codigo_conta"],
                    banco=linha["banco"],
                    numero_conta=linha["numero_conta"],
                    apelido=linha["apelido"],
                    valor=linha["valor_conta"],
                    natureza=linha["natureza_conta"],
                )
                cache_contas[chave_conta] = conta
                out.contas_criadas += 1

            fonte, _ = FonteRecursos.objects.get_or_create(
                codigo=linha["fonte_codigo"], defaults={"nome": linha["fonte_nome"]}
            )
            SaldoBalancoContaFonte.objects.create(
                conta=conta, fonte_recursos=fonte, valor=linha["valor_fonte"], natureza=linha["natureza_fonte"]
            )
            out.fontes_criadas += 1

    return out


@dataclass
class ResultadoImportacaoSaldoContaBancaria:
    contas_criadas: int = 0
    fontes_criadas: int = 0
    unidades_gestoras: list[str] | None = None
    mes_referencia: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_saldo_conta_bancaria(
    resultado: ResultadoParsing, municipio: Municipio
) -> ResultadoImportacaoSaldoContaBancaria:
    """
    A partir de "Relação de saldos - Por UG titular da conta" (um único
    PDF por mês cobrindo todas as UGs, desde 2026-11-12 — ver docstring do
    parser), grava SaldoContaBancaria/SaldoContaBancariaFonte. Mês vem do
    cabeçalho do próprio relatório, nunca do nome do arquivo ou da pasta —
    valida isso antes de gravar. Cada linha já carrega sua própria UG
    (`linha["unidade_gestora_nome"]`); agrupa por UG e reimporta cada uma
    independentemente — reimportar a mesma UG+mês SUBSTITUI as contas
    desse mês (delete + recreate); UGs não presentes neste arquivo não são
    tocadas.
    """
    mes_referencia = resultado.metadados.get("mes_referencia")
    data_referencia_texto = resultado.metadados.get("data_referencia")
    if not mes_referencia or not data_referencia_texto:
        raise ValueError("Mês/data de referência não identificado no cabeçalho do relatório — importação abortada.")
    data_referencia = datetime.strptime(data_referencia_texto, "%d/%m/%Y").date()

    linhas_por_ug: dict[str, list[dict]] = {}
    for linha in resultado.linhas:
        linhas_por_ug.setdefault(linha["unidade_gestora_nome"], []).append(linha)

    out = ResultadoImportacaoSaldoContaBancaria(
        avisos=list(resultado.avisos), unidades_gestoras=[], mes_referencia=mes_referencia
    )

    for nome_ug, linhas_ug in linhas_por_ug.items():
        unidade_gestora = resolver_unidade_gestora_por_nome(municipio, nome_ug)
        out.unidades_gestoras.append(unidade_gestora.nome)

        SaldoContaBancaria.objects.filter(unidade_gestora=unidade_gestora, mes_referencia=mes_referencia).delete()

        cache_contas: dict[str, SaldoContaBancaria] = {}
        for linha in linhas_ug:
            chave_conta = linha["numero_conta"] or linha["apelido"]
            conta = cache_contas.get(chave_conta)
            if conta is None:
                conta = SaldoContaBancaria.objects.create(
                    unidade_gestora=unidade_gestora,
                    mes_referencia=mes_referencia,
                    data_referencia=data_referencia,
                    banco=linha["banco"],
                    numero_conta=linha["numero_conta"],
                    apelido=linha["apelido"],
                    saldo_pre_pagamentos_previstos=linha["saldo_pre_pagamentos_previstos"],
                    saldo_nao_comprometido=linha["saldo_nao_comprometido"],
                )
                cache_contas[chave_conta] = conta
                out.contas_criadas += 1

            fonte, _ = FonteRecursos.objects.get_or_create(
                codigo=linha["fonte_codigo"], defaults={"nome": linha["fonte_nome"]}
            )
            SaldoContaBancariaFonte.objects.create(
                conta=conta, fonte_recursos=fonte, valor=linha["valor_fonte"], natureza=linha["natureza_fonte"]
            )
            out.fontes_criadas += 1

    return out


@dataclass
class ResultadoImportacaoExecucaoReceita:
    lancamentos_criados: int = 0
    lancamentos_atualizados: int = 0
    rubricas_criadas: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_execucao_receita(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoExecucaoReceita:
    """
    A partir de "Demonstrativo da receita por classificação econômica"
    (um arquivo por mês), grava LancamentoExecucaoReceita — a única fonte
    com receita arrecadada quebrada por fonte de recursos (ver docstring
    do modelo). Resolve/cria FonteRecursos pelo código real informado
    (diferente de importar_fichas_receitas, que só tinha o nome) e
    RubricaReceita por (loa, unidade_gestora, código normalizado, fonte) —
    cria com valor_orcado=0 se a combinação ainda não existir (receita
    realizada que a LOA não previu nessa fonte específica, equivalente ao
    CREDITO_ADICIONAL do lado despesa).

    Atribui tudo à Unidade Gestora "01" (Prefeitura): este relatório não
    distingue UG, e a única outra UG arrecadadora possível (Câmara) tem
    valor_orcado=0 em 100% das suas rubricas de receita — não há receita
    real para atribuir a ela.
    """
    out = ResultadoImportacaoExecucaoReceita(avisos=list(resultado.avisos))

    mes_referencia = resultado.metadados.get("mes_referencia")
    if not mes_referencia:
        out.avisos.append("Mês de referência não determinado — importação abortada.")
        return out

    exercicio = Exercicio.objects.filter(municipio=municipio).order_by("-ano").first()
    if exercicio is None or not hasattr(exercicio, "loa"):
        raise ValueError("Nenhum Exercício/LOA encontrado — rode importar_fichas_receitas antes.")
    loa = exercicio.loa

    try:
        unidade_gestora = UnidadeGestora.objects.get(municipio=municipio, codigo="01")
    except UnidadeGestora.DoesNotExist:
        raise ValueError("Unidade Gestora '01' (Prefeitura) não encontrada — rode importar_estrutura antes.")

    cache_fontes: dict[str, FonteRecursos] = {}
    cache_rubricas: dict[tuple[str, str], RubricaReceita] = {}

    for linha in resultado.linhas:
        fonte = cache_fontes.get(linha["fonte_codigo"])
        if fonte is None:
            fonte, _ = FonteRecursos.objects.get_or_create(
                codigo=linha["fonte_codigo"], defaults={"nome": "(a definir)"}
            )
            cache_fontes[linha["fonte_codigo"]] = fonte

        chave_rubrica = (linha["codigo"], linha["fonte_codigo"])
        rubrica = cache_rubricas.get(chave_rubrica)
        if rubrica is None:
            rubrica, criada = RubricaReceita.objects.get_or_create(
                loa=loa, unidade_gestora=unidade_gestora, codigo=linha["codigo"], fonte_recursos=fonte,
                defaults={"nome": linha["nome"], "valor_orcado": Decimal("0")},
            )
            if criada:
                out.rubricas_criadas += 1
            cache_rubricas[chave_rubrica] = rubrica

        _, criado = LancamentoExecucaoReceita.objects.update_or_create(
            rubrica=rubrica, mes_referencia=mes_referencia,
            defaults={
                "valor_bruto_no_mes": linha["valor_bruto"],
                "deducao_no_mes": linha["deducao"],
                "anulacao_no_mes": linha["anulacao"],
                "valor_liquido_no_mes": linha["valor_liquido"],
            },
        )
        if criado:
            out.lancamentos_criados += 1
        else:
            out.lancamentos_atualizados += 1

    return out


@dataclass
class ResultadoImportacaoRestosAPagar:
    restos_criados: int = 0
    mes_referencia: int = 0
    avisos: list[str] | None = None


@transaction.atomic
def importar_restos_a_pagar(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoRestosAPagar:
    """
    A partir de "DEMONSTRATIVO DOS RESTOS A PAGAR POR FONTE DE RECURSOS"
    (um PDF por mês, cobrindo todas as UGs), grava RestoAPagar. É um
    relatório cumulativo reimpresso por inteiro todo mês (ver docstring do
    modelo) — reimportar um mês SUBSTITUI integralmente os registros
    daquele mês (delete + bulk_create), nunca soma com meses anteriores.
    Resolve cada UG pelo nome impresso na respectiva seção do relatório
    (accent/case-insensitive, mesma `resolver_unidade_gestora_por_nome`
    usada pelos relatórios de saldo) — um nome que não bater vira aviso e
    aquela linha é pulada, não interrompe a importação inteira.
    """
    mes_referencia = resultado.metadados.get("mes_referencia")
    if not mes_referencia:
        raise ValueError("Mês de referência não identificado no cabeçalho do relatório — importação abortada.")

    out = ResultadoImportacaoRestosAPagar(avisos=list(resultado.avisos), mes_referencia=mes_referencia)

    RestoAPagar.objects.filter(unidade_gestora__municipio=municipio, mes_referencia=mes_referencia).delete()

    cache_ug: dict[str, UnidadeGestora] = {}
    cache_fonte: dict[str, FonteRecursos] = {}
    novos = []

    for linha in resultado.linhas:
        nome_ug = linha["unidade_gestora_nome"]
        ug = cache_ug.get(nome_ug)
        if ug is None:
            try:
                ug = resolver_unidade_gestora_por_nome(municipio, nome_ug)
            except ValueError as exc:
                out.avisos.append(str(exc))
                continue
            cache_ug[nome_ug] = ug

        fonte = cache_fonte.get(linha["fonte_codigo"])
        if fonte is None:
            fonte, _ = FonteRecursos.objects.get_or_create(
                codigo=linha["fonte_codigo"], defaults={"nome": linha["fonte_nome"]}
            )
            cache_fonte[linha["fonte_codigo"]] = fonte

        novos.append(RestoAPagar(
            unidade_gestora=ug, fonte_recursos=fonte, mes_referencia=mes_referencia,
            exercicio_origem=linha["exercicio_origem"], numero_empenho=linha["numero_empenho"],
            inscricao_processada=linha["inscricao_processada"],
            inscricao_nao_processada=linha["inscricao_nao_processada"],
            reinscricao=linha["reinscricao"], cancelamento=linha["cancelamento"],
            liquidacao=linha["liquidacao"], rpp_pago=linha["rpp_pago"], rpnp_pago=linha["rpnp_pago"],
        ))

    RestoAPagar.objects.bulk_create(novos, batch_size=1000)
    out.restos_criados = len(novos)

    return out


@dataclass
class ResultadoEnriquecimentoRestosAPagar:
    registros_atualizados: int = 0
    empenhos_nao_encontrados: int = 0
    avisos: list[str] | None = None


def enriquecer_restos_a_pagar_fichas(
    resultado: ResultadoParsing, municipio: Municipio
) -> ResultadoEnriquecimentoRestosAPagar:
    """
    A partir de "SALDO DAS FICHAS DE RESTOS A PAGAR" (FICHAS_RESTOS.PDF,
    foto de 02/01/2026, única — não um arquivo por mês), preenche
    credor/órgão/unidade orçamentária/elemento de despesa/classificação
    funcional-programática nos `RestoAPagar` que `importar_restos_a_pagar`
    já gravou a partir de RP01.PDF..RP09.PDF (que não trazem esses dados).

    Casa pela chave (unidade_gestora, exercício de origem, número do
    empenho) — a mesma tripla é única em ambos os relatórios (confirmado:
    zero duplicatas nas linhas parseadas deste arquivo) — e atualiza TODAS
    as linhas de `RestoAPagar` daquele empenho, em qualquer mês de
    referência já importado (o enriquecimento é a mesma foto para o
    empenho inteiro, independente do mês). Um empenho do relatório sem
    nenhum `RestoAPagar` correspondente (ainda não importado, ou já
    liquidado antes do primeiro mês importado) gera um aviso, não um erro —
    é enriquecimento, não criação.

    `orgao`/`unidade_orcamentaria`/`elemento_despesa` só são linkados
    quando o código bate com um registro já cadastrado (catálogos atuais,
    estáveis entre exercícios); quando não bate, a linha é enriquecida do
    mesmo jeito só com os campos de texto (credor/classificação/ação) e um
    aviso aponta o código que não resolveu.
    """
    out = ResultadoEnriquecimentoRestosAPagar(avisos=list(resultado.avisos))

    cache_ug: dict[str, UnidadeGestora] = {}
    cache_orgao: dict[str, Orgao | None] = {}
    cache_unidade_orc: dict[tuple[int, str, str], UnidadeOrcamentaria | None] = {}
    cache_elemento: dict[str, ElementoDespesa | None] = {}

    for linha in resultado.linhas:
        nome_ug = linha["unidade_gestora_nome"]
        ug = cache_ug.get(nome_ug)
        if ug is None:
            try:
                ug = resolver_unidade_gestora_por_nome(municipio, nome_ug)
            except ValueError as exc:
                out.avisos.append(str(exc))
                continue
            cache_ug[nome_ug] = ug

        orgao = None
        if linha["orgao_codigo"]:
            chave_orgao = linha["orgao_codigo"]
            if chave_orgao not in cache_orgao:
                cache_orgao[chave_orgao] = Orgao.objects.filter(municipio=municipio, codigo=chave_orgao).first()
                if cache_orgao[chave_orgao] is None:
                    out.avisos.append(f"Órgão {chave_orgao!r} não encontrado — empenho enriquecido sem vínculo.")
            orgao = cache_orgao[chave_orgao]

        unidade_orcamentaria = None
        if orgao is not None and linha["unidade_orc_codigo"]:
            chave_uorc = (orgao.id, ug.id, linha["unidade_orc_codigo"])
            if chave_uorc not in cache_unidade_orc:
                cache_unidade_orc[chave_uorc] = UnidadeOrcamentaria.objects.filter(
                    orgao=orgao, unidade_gestora=ug, codigo=linha["unidade_orc_codigo"]
                ).first()
                if cache_unidade_orc[chave_uorc] is None:
                    out.avisos.append(
                        f"Unidade orçamentária {linha['unidade_orc_codigo']!r} (órgão {orgao.codigo}, "
                        f"{ug.nome}) não encontrada — empenho enriquecido sem vínculo."
                    )
            unidade_orcamentaria = cache_unidade_orc[chave_uorc]

        elemento_despesa = None
        if linha["elemento_codigo"]:
            chave_elem = linha["elemento_codigo"]
            if chave_elem not in cache_elemento:
                cache_elemento[chave_elem] = ElementoDespesa.objects.filter(codigo=chave_elem).first()
                if cache_elemento[chave_elem] is None:
                    out.avisos.append(f"Elemento de despesa {chave_elem!r} não encontrado — enriquecido sem vínculo.")
            elemento_despesa = cache_elemento[chave_elem]

        classificacao = None
        if linha["funcao"] and linha["subfuncao"] and linha["programa"] and linha["acao"]:
            classificacao = f"{linha['funcao']}.{linha['subfuncao']}.{linha['programa']}.{linha['acao']}"

        atualizados = RestoAPagar.objects.filter(
            unidade_gestora=ug, exercicio_origem=linha["exercicio_origem"], numero_empenho=linha["numero_empenho"]
        ).update(
            credor_nome=linha["credor_nome"],
            orgao=orgao,
            unidade_orcamentaria=unidade_orcamentaria,
            elemento_despesa=elemento_despesa,
            classificacao_funcional_programatica=classificacao or "",
            acao_nome=linha["acao_nome"] or "",
            classificacao_economica_codigo=linha["classificacao_economica_codigo"] or "",
        )
        if atualizados == 0:
            out.empenhos_nao_encontrados += 1
            out.avisos.append(
                f"Empenho {linha['numero_empenho']}/{linha['exercicio_origem']} ({ug.nome}) do relatório de fichas "
                f"não tem RestoAPagar correspondente importado — nada para enriquecer."
            )
        else:
            out.registros_atualizados += atualizados

    return out


@dataclass
class ResultadoImportacaoApuracaoFiscal:
    gravados: int = 0
    avisos: list[str] | None = None


def importar_dtp(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoApuracaoFiscal:
    """
    A partir do RGF-Anexo 1 (seção final "APURAÇÃO DO CUMPRIMENTO DO
    LIMITE LEGAL"), grava `ApuracaoDTP`. Reimportar o mesmo (município,
    exercício, bimestre) SUBSTITUI o registro (delete + create) — mesma
    semântica de todo outro import deste projeto, o PDF é uma foto
    completa da apuração, nunca um incremento.
    """
    out = ResultadoImportacaoApuracaoFiscal(avisos=list(resultado.avisos))
    if not resultado.linhas:
        return out
    linha = resultado.linhas[0]
    ApuracaoDTP.objects.filter(
        municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
    ).delete()
    ApuracaoDTP.objects.create(
        municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
        rcl=linha["rcl"],
        deducao_emendas_individuais=linha["deducao_emendas_individuais"],
        deducao_emendas_bancada=linha["deducao_emendas_bancada"],
        deducao_agentes_saude=linha["deducao_agentes_saude"],
        deducao_outras=linha["deducao_outras"],
        rcl_ajustada=linha["rcl_ajustada"],
        despesa_total_pessoal=linha["despesa_total_pessoal"], percentual_dtp=linha["percentual_dtp"],
        limite_maximo_valor=linha["limite_maximo_valor"], limite_maximo_percentual=linha["limite_maximo_percentual"],
        limite_prudencial_valor=linha["limite_prudencial_valor"],
        limite_prudencial_percentual=linha["limite_prudencial_percentual"],
        limite_alerta_valor=linha["limite_alerta_valor"], limite_alerta_percentual=linha["limite_alerta_percentual"],
    )
    out.gravados = 1
    return out


# As 7 fontes que compõem o superávit do FUNDEB reprogramado — confirmado
# pelo usuário ("2.540XXXX 2.541XXXX 2.542XXXX 2.543XXXX 2.546XXXX") e
# batendo exatamente com o catálogo real (`FonteRecursos.codigo__startswith`
# desses 5 prefixos, nenhuma outra fonte na faixa 254x existe).
FONTES_SUPERAVIT_FUNDEB = [
    "25400000", "25401070", "25410000", "25411070", "25420000", "25430000", "25460000",
]


def _delta_execucao_fontes_superavit_fundeb(municipio: Municipio, bimestre: int, campo: str) -> Decimal | None:
    """
    Delta do campo informado (`empenhado_acumulado`/`liquidado_acumulado`)
    entre abril (fechamento do 1º quadrimestre) e o mês de fechamento do
    bimestre informado — capado no último mês de execução orçamentária já
    importado para as 7 fontes de superávit do FUNDEB, mesma lógica de
    "usar o último mês com movimento disponível" já seguida no frontend.
    `None` se o bimestre ainda não fechou o 1º quadrimestre (nada "depois"
    a reportar ainda) ou se não há execução além de abril disponível.
    """
    mes_fechamento = bimestre * 2
    if mes_fechamento <= 4:
        return None

    base = LancamentoExecucaoOrcamentaria.objects.filter(
        rubrica__unidade_gestora__municipio=municipio,
        rubrica__fonte_recursos__codigo__in=FONTES_SUPERAVIT_FUNDEB,
    )
    ultimo_mes_disponivel = base.aggregate(m=Max("mes_referencia"))["m"] or 0
    mes_alvo = min(mes_fechamento, ultimo_mes_disponivel)
    if mes_alvo <= 4:
        return None

    valor_abril = base.filter(mes_referencia=4).aggregate(v=Sum(campo))["v"] or Decimal("0")
    valor_alvo = base.filter(mes_referencia=mes_alvo).aggregate(v=Sum(campo))["v"] or Decimal("0")
    return valor_alvo - valor_abril


def _calcular_aplicado_apos_quadrimestre(municipio: Municipio, bimestre: int, valor_pdf: str) -> str:
    """
    O RREO-Anexo 8 do ASPEC nunca atualiza a coluna "Aplicado Após o 1º
    Quadrimestre" da linha 19 (Reprogramação do FUNDEB) — vem sempre
    "0,00", mesmo em bimestres fechados bem depois de abril (confirmado
    inspecionando RREO83/84/85.PDF de 2026: idênticos, todos com essa
    coluna zerada). Relatado pelo usuário: "no PDF os valores estão
    errados, o valor aplicado corresponde aos empenhos nas fontes
    2.540XXXX...2.546XXXX" — confirmado batendo exatamente: a despesa
    liquidada acumulada nessas 7 fontes até abril (mês de fechamento do 1º
    quadrimestre) é R$1.855.933,51, idêntico ao "aplicado até o 1º
    quadrimestre" que o próprio PDF já reporta corretamente — forte
    evidência de que liquidado nessas fontes É a definição certa de
    "aplicado do superávit do FUNDEB". Para bimestre <= 2 o 0,00 do PDF
    está correto e é mantido como veio.
    """
    delta = _delta_execucao_fontes_superavit_fundeb(municipio, bimestre, "liquidado_acumulado")
    return valor_pdf if delta is None else str(delta)


def _calcular_gerencial_empenhado_reprogramacao(municipio: Municipio, bimestre: int) -> tuple[str, str]:
    """
    Visão GERENCIAL (empenhado) ao lado da visão oficial (liquidado) já
    calculada acima — pedido do usuário: "fazer igual ao MDE e ter o
    cálculo gerencial informado também o valor empenhado" (MDE já expõe
    TOTAL/ÍNDICE GERENCIAL, baseado em cada fase de execução, ao lado do
    TOTAL STN). O RREO-Anexo 8 não imprime nenhuma coluna de empenhado
    pra esta linha — os dois valores aqui são 100% derivados de
    `LancamentoExecucaoOrcamentaria`, nunca do PDF. "Até o 1º quadrimestre"
    é o empenhado acumulado em abril (mesma definição de "até" já usada
    pelo par liquidado-based, direto, sem delta); "após" é o delta
    abril→fechamento do bimestre, mesma função acima.
    """
    base = LancamentoExecucaoOrcamentaria.objects.filter(
        rubrica__unidade_gestora__municipio=municipio,
        rubrica__fonte_recursos__codigo__in=FONTES_SUPERAVIT_FUNDEB,
    )
    ate_empenhado = base.filter(mes_referencia=4).aggregate(v=Sum("empenhado_acumulado"))["v"] or Decimal("0")
    delta_apos = _delta_execucao_fontes_superavit_fundeb(municipio, bimestre, "empenhado_acumulado")
    apos_empenhado = delta_apos if delta_apos is not None else Decimal("0")
    return str(ate_empenhado), str(apos_empenhado)


FONTES_PNAE_RECURSOS_PROPRIOS = ["15001001", "25001001"]


def _calcular_aplicacao_pnae_recursos_proprios(municipio: Municipio, bimestre: int) -> Decimal:
    """
    Gasto com PNAE/PEAE (merenda escolar) custeado com recursos próprios
    (fontes 15001001/25001001), nas ações marcadas
    `Acao.desconsiderar_pnae_peae=True` — pedido do usuário para descontar
    do TOTAL/ÍNDICE GERENCIAL do MDE, já que esse gasto não deveria contar
    como aplicação em MDE. Base: despesa EMPENHADA, não liquidada —
    confirmado nos dados reais de Novo Progresso/PA que a liquidada nessas
    2 fontes+ações é sempre 0 em todos os bimestres (o pouco que essas
    ações gastam em recursos próprios fica só empenhado), então usar
    liquidada deixaria este desconto sempre zerado na prática; a grande
    maioria do PNAE real é custeada pela transferência federal específica
    (fontes 15520000/25520000, de propósito fora desta lista — não é
    "recursos próprios"). Mesmo padrão de "capar no último mês disponível"
    de `_delta_execucao_fontes_superavit_fundeb()` acima, pra não zerar por
    engano quando a execução orçamentária ainda não alcançou o mês de
    fechamento do bimestre.
    """
    mes_fechamento = bimestre * 2
    base = LancamentoExecucaoOrcamentaria.objects.filter(
        rubrica__unidade_gestora__municipio=municipio,
        rubrica__fonte_recursos__codigo__in=FONTES_PNAE_RECURSOS_PROPRIOS,
        rubrica__acao__desconsiderar_pnae_peae=True,
    )
    ultimo_mes_disponivel = base.aggregate(m=Max("mes_referencia"))["m"] or 0
    mes_alvo = min(mes_fechamento, ultimo_mes_disponivel) if ultimo_mes_disponivel else mes_fechamento
    return base.filter(mes_referencia=mes_alvo).aggregate(v=Sum("empenhado_acumulado"))["v"] or Decimal("0")


SUBFUNCOES_ENSINO_MEDIO_SUPERIOR = ["362", "364"]


def _calcular_despesa_ensino_medio_superior_recursos_proprios(municipio: Municipio, bimestre: int) -> Decimal:
    """
    Despesa em recursos próprios (mesmas fontes 15001001/25001001 do PNAE
    acima) nas subfunções 362 (Ensino Médio) / 364 (Ensino Superior) —
    município deve atuar prioritariamente em fundamental/infantil (CF
    art.211 §2º), então esse gasto não deveria contar como MDE. Ao
    contrário do PNAE, não depende de nenhuma flag em `Acao` — subfunção
    já é campo direto em `RubricaOrcamentaria`, filtra sem intermediário.
    Confirmado via shell que a linha 20 do RREO ("despesa_mde_*") bate
    exatamente com toda a despesa da função 12 nessas 2 fontes, sem
    excluir nada — ou seja, o relatório oficial NÃO desconta isso por
    conta própria. Mesmo padrão de "capar no último mês disponível" do
    helper do PNAE acima.
    """
    mes_fechamento = bimestre * 2
    base = LancamentoExecucaoOrcamentaria.objects.filter(
        rubrica__unidade_gestora__municipio=municipio,
        rubrica__fonte_recursos__codigo__in=FONTES_PNAE_RECURSOS_PROPRIOS,
        rubrica__funcao__codigo="12",
        rubrica__subfuncao__codigo__in=SUBFUNCOES_ENSINO_MEDIO_SUPERIOR,
    )
    ultimo_mes_disponivel = base.aggregate(m=Max("mes_referencia"))["m"] or 0
    mes_alvo = min(mes_fechamento, ultimo_mes_disponivel) if ultimo_mes_disponivel else mes_fechamento
    return base.filter(mes_referencia=mes_alvo).aggregate(v=Sum("empenhado_acumulado"))["v"] or Decimal("0")


def importar_mde_e_magisterio(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoApuracaoFiscal:
    """
    A partir do RREO-Anexo 8, grava `ApuracaoMDE`, `ApuracaoMagisterioFundeb`,
    `ApuracaoETIFundeb`, `ApuracaoVAATEducacaoInfantil`,
    `ApuracaoVAATDespesaCapital`, `ApuracaoValorNaoAplicadoFundeb` e
    `ApuracaoReprogramacaoFundeb` — um único PDF alimenta os sete índices
    (ver docstring do parser). Mesma semântica de substituição dos demais
    imports deste módulo.
    """
    out = ResultadoImportacaoApuracaoFiscal(avisos=list(resultado.avisos))
    for linha in resultado.linhas:
        if linha["tipo"] == "mde":
            ApuracaoMDE.objects.filter(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
            ).delete()
            apuracao_mde = ApuracaoMDE.objects.create(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
                receita_impostos=linha["receita_impostos"], receita_transferencias=linha["receita_transferencias"],
                base_calculo=linha["base_calculo"], minimo_constitucional=linha["minimo_constitucional"],
                despesa_mde_empenhada=linha["despesa_mde_empenhada"],
                despesa_mde_liquidada=linha["despesa_mde_liquidada"],
                despesa_mde_paga=linha["despesa_mde_paga"],
                fundeb_transferido=linha["fundeb_transferido"],
                excedente_fundeb_nao_aplicado=linha["excedente_fundeb_nao_aplicado"],
                cancelamento_rp=linha["cancelamento_rp"],
                aplicacao_pnae_recursos_proprios=_calcular_aplicacao_pnae_recursos_proprios(
                    municipio, linha["bimestre"]
                ),
                despesa_ensino_medio_superior_recursos_proprios=_calcular_despesa_ensino_medio_superior_recursos_proprios(
                    municipio, linha["bimestre"]
                ),
                valor_exigido=linha["valor_exigido"],
                valor_aplicado=linha["valor_aplicado"], percentual_aplicado=linha["percentual_aplicado"],
            )
            ApuracaoMDEReceitaItem.objects.bulk_create(
                ApuracaoMDEReceitaItem(
                    apuracao=apuracao_mde, grupo=item["grupo"], codigo=item["codigo"],
                    rotulo=item["rotulo"], valor=item["valor"],
                )
                for item in linha["itens_receita"]
            )
            out.gravados += 1
        elif linha["tipo"] == "magisterio":
            ApuracaoMagisterioFundeb.objects.filter(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
            ).delete()
            ApuracaoMagisterioFundeb.objects.create(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
                fundeb_receita_total=linha["fundeb_receita_total"], valor_exigido=linha["valor_exigido"],
                valor_aplicado=linha["valor_aplicado"], percentual_aplicado=linha["percentual_aplicado"],
            )
            out.gravados += 1
        elif linha["tipo"] == "eti_fundeb":
            ApuracaoETIFundeb.objects.filter(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
            ).delete()
            ApuracaoETIFundeb.objects.create(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
                fundeb_receita_total=linha["fundeb_receita_total"], valor_exigido=linha["valor_exigido"],
                valor_aplicado=linha["valor_aplicado"], percentual_aplicado=linha["percentual_aplicado"],
            )
            out.gravados += 1
        elif linha["tipo"] == "vaat_educacao_infantil":
            ApuracaoVAATEducacaoInfantil.objects.filter(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
            ).delete()
            ApuracaoVAATEducacaoInfantil.objects.create(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
                valor_exigido=linha["valor_exigido"],
                valor_aplicado=linha["valor_aplicado"], percentual_aplicado=linha["percentual_aplicado"],
            )
            out.gravados += 1
        elif linha["tipo"] == "vaat_despesa_capital":
            ApuracaoVAATDespesaCapital.objects.filter(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
            ).delete()
            ApuracaoVAATDespesaCapital.objects.create(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
                valor_exigido=linha["valor_exigido"],
                valor_aplicado=linha["valor_aplicado"], percentual_aplicado=linha["percentual_aplicado"],
            )
            out.gravados += 1
        elif linha["tipo"] == "fundeb_nao_aplicado":
            ApuracaoValorNaoAplicadoFundeb.objects.filter(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
            ).delete()
            ApuracaoValorNaoAplicadoFundeb.objects.create(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
                valor_maximo_permitido=linha["valor_maximo_permitido"],
                valor_nao_aplicado=linha["valor_nao_aplicado"],
                valor_nao_aplicado_apos_ajuste=linha["valor_nao_aplicado_apos_ajuste"],
                valor_excedente_ao_maximo_permitido=linha["valor_excedente_ao_maximo_permitido"],
                percentual_nao_aplicado=linha["percentual_nao_aplicado"],
            )
            out.gravados += 1
        elif linha["tipo"] == "fundeb_reprogramacao":
            ApuracaoReprogramacaoFundeb.objects.filter(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
            ).delete()
            aplicado_ate_empenhado, aplicado_apos_empenhado = _calcular_gerencial_empenhado_reprogramacao(
                municipio, linha["bimestre"]
            )
            apuracao_reprogramacao = ApuracaoReprogramacaoFundeb.objects.create(
                municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
                valor_superavit_permitido_exercicio_anterior=linha["valor_superavit_permitido_exercicio_anterior"],
                valor_nao_aplicado_exercicio_anterior=linha["valor_nao_aplicado_exercicio_anterior"],
                valor_aplicado_ate_primeiro_quadrimestre=linha["valor_aplicado_ate_primeiro_quadrimestre"],
                valor_aplicado_apos_primeiro_quadrimestre=_calcular_aplicado_apos_quadrimestre(
                    municipio, linha["bimestre"], linha["valor_aplicado_apos_primeiro_quadrimestre"]
                ),
                valor_aplicado_ate_primeiro_quadrimestre_empenhado=aplicado_ate_empenhado,
                valor_aplicado_apos_primeiro_quadrimestre_empenhado=aplicado_apos_empenhado,
                valor_nao_aplicado_ate_primeiro_quadrimestre_atual=linha["valor_nao_aplicado_ate_primeiro_quadrimestre_atual"],
            )
            ApuracaoReprogramacaoFundebOrigem.objects.bulk_create(
                ApuracaoReprogramacaoFundebOrigem(
                    apuracao=apuracao_reprogramacao,
                    origem=origem["origem"],
                    valor_superavit_permitido_exercicio_anterior=origem["valor_superavit_permitido_exercicio_anterior"],
                    valor_nao_aplicado_exercicio_anterior=origem["valor_nao_aplicado_exercicio_anterior"],
                    valor_aplicado_ate_primeiro_quadrimestre=origem["valor_aplicado_ate_primeiro_quadrimestre"],
                    valor_aplicado_apos_primeiro_quadrimestre=origem["valor_aplicado_apos_primeiro_quadrimestre"],
                    valor_nao_aplicado_ate_primeiro_quadrimestre_atual=origem["valor_nao_aplicado_ate_primeiro_quadrimestre_atual"],
                )
                for origem in linha["origens"]
            )
            out.gravados += 1
    return out


def importar_asps(resultado: ResultadoParsing, municipio: Municipio) -> ResultadoImportacaoApuracaoFiscal:
    """
    A partir do RREO-Anexo XII (seção final de apuração do limite mínimo
    de ASPS), grava `ApuracaoASPS`. Mesma semântica de substituição dos
    demais imports deste módulo.
    """
    out = ResultadoImportacaoApuracaoFiscal(avisos=list(resultado.avisos))
    if not resultado.linhas:
        return out
    linha = resultado.linhas[0]
    ApuracaoASPS.objects.filter(
        municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"]
    ).delete()
    ApuracaoASPS.objects.create(
        municipio=municipio, exercicio=linha["exercicio"], bimestre=linha["bimestre"],
        receita_impostos_transferencias=linha["receita_impostos_transferencias"],
        base_calculo=linha["base_calculo"], minimo_constitucional=linha["minimo_constitucional"],
        despesa_asps_empenhada=linha["despesa_asps_empenhada"], despesa_asps_liquidada=linha["despesa_asps_liquidada"],
        despesa_asps_paga=linha["despesa_asps_paga"],
        percentual_aplicado=linha["percentual_aplicado"],
    )
    out.gravados = 1
    return out
