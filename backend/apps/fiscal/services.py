"""
Popula a hierarquia oficial do Ementário da Receita (STN) decompondo o
`codigo` já existente em cada `RubricaReceita` — é uma derivação
DB-para-DB a partir do que `importar_fichas_receitas`/
`importar_execucao_receita` já gravaram, não um import de arquivo. O
nome oficial de cada nível vem depois, separadamente, de
`importar_ementario_receita()` (mais abaixo neste arquivo), que lê o
xlsx oficial da STN uma vez disponível.

Formato do código (confirmado nos dados reais, ex.:
"001.1.1.2.50.0.1.00.00.00" — bate com o exemplo de "representação
ampliada" do próprio pedido do usuário): os 7 primeiros segmentos
separados por "." são os 7 níveis oficiais (Categoria Econômica,
Origem, Espécie, Rubrica, Alínea, Subalínea, Tipo) nessa ordem; o
primeiro segmento vem com padding de zeros (ex. "001" = categoria "1")
porque duas fontes ASPEC formatam esse mesmo segmento de forma
diferente (ver `normalizar_codigo` em aspec_execucao_receita.py) — por
isso aqui ele é desempacotado (`int()` remove os zeros à esquerda).
Qualquer segmento além do 7º é desdobramento interno do sistema de
origem, não um nível oficial da STN — preservado em
`detalhamento_adicional`, nunca promovido a nível da hierarquia (ver
docstring de `RubricaReceita.detalhamento_adicional`).

Nomes de cada nível intermediário (Origem/Espécie/Rubrica/Alínea/
Subalínea/Tipo) não estão disponíveis em nenhuma fonte já importada —
só o nome da classificação completa (`RubricaReceita.nome`) existe.
Por isso todo nível criado aqui nasce com nome="(a definir)", mesma
convenção já usada em `importar_execucao_orcamentaria` para
Função/Subfunção/etc. — esperando uma tabela oficial futura (seção de
importação do Ementário) para corrigir os nomes.
"""

from dataclasses import dataclass, field

from apps.orcamento.models import CategoriaEconomica

from .models import (
    ClassificacaoReceitaAlinea,
    ClassificacaoReceitaEspecie,
    ClassificacaoReceitaOrigem,
    ClassificacaoReceitaRubrica,
    ClassificacaoReceitaSubalinea,
    ClassificacaoReceitaTipo,
    RubricaReceita,
)

NOME_PENDENTE = "(a definir)"


def decompor_codigo_receita(codigo: str) -> tuple[list[str], str] | None:
    """
    Retorna (niveis, detalhamento_adicional) onde niveis é a lista dos 7
    códigos oficiais na ordem Categoria/Origem/Espécie/Rubrica/Alínea/
    Subalínea/Tipo, ou None se o código não tiver ao menos 7 segmentos
    separados por ponto (fora do padrão esperado).

    O primeiro segmento nem sempre é só a Categoria Econômica com padding
    de zeros (ex. "001" = categoria "1") — confirmado nos dados reais que
    receitas de repasse constitucional automático (cota-parte FPM/ICMS/
    IPVA/IPI) e FUNDEB usam um prefixo de 2 dígitos não-trivial nessa
    mesma posição ("951"/"991" em vez de "001"/"002"), sempre com a
    Categoria Econômica oficial (1 ou 2) no ÚLTIMO dígito do segmento —
    por isso a categoria é sempre extraída do último caractere, nunca do
    segmento inteiro, e um prefixo não-zero vira o primeiro elemento de
    `detalhamento_adicional` em vez de ser tratado como nível oficial.
    """
    partes = codigo.split(".")
    if len(partes) < 7:
        return None
    seg0 = partes[0]
    niveis = [seg0[-1], *partes[1:7]]
    prefixo = seg0[:-1]
    extras = partes[7:]
    if prefixo.lstrip("0"):
        extras = [prefixo, *extras]
    detalhamento = ".".join(extras)
    return niveis, detalhamento


def _eh_prefixo_deducao(codigo: str) -> bool:
    """
    True quando o primeiro segmento do código (ex.: "951" em
    "951.7.1.1...") tem um prefixo não-trivial antes do dígito de
    Categoria Econômica — convenção confirmada pelo usuário: esses
    códigos ("95"/"99" observados até agora) são deduções constitucionais
    da receita corrente (cota-parte/FUNDEB), não receita nova.
    """
    seg0 = codigo.split(".", 1)[0]
    return bool(seg0[:-1].lstrip("0"))


def _encontrar_rubrica_principal(deducao: RubricaReceita) -> RubricaReceita | None:
    """
    Acha a RubricaReceita "bruta" correspondente a uma dedução: mesma
    UG/fonte/LOA e código idêntico a partir do segundo segmento (só o
    primeiro segmento difere — prefixo trivial "00" na principal, "95"/"99"
    na dedução), que não seja ela mesma uma dedução.
    """
    resto = deducao.codigo.split(".", 1)[1]
    candidatos = RubricaReceita.objects.filter(
        loa=deducao.loa, unidade_gestora=deducao.unidade_gestora, fonte_recursos=deducao.fonte_recursos,
    ).exclude(pk=deducao.pk)
    for candidata in candidatos:
        if candidata.codigo.split(".", 1)[1] != resto:
            continue
        if _eh_prefixo_deducao(candidata.codigo):
            continue
        return candidata
    return None


@dataclass
class ResultadoPopulacaoClassificacaoReceita:
    rubricas_processadas: int = 0
    rubricas_vinculadas: int = 0
    niveis_criados: int = 0
    deducoes_vinculadas: int = 0
    avisos: list[str] = field(default_factory=list)


def popular_classificacao_receita() -> ResultadoPopulacaoClassificacaoReceita:
    out = ResultadoPopulacaoClassificacaoReceita()

    for rubrica in RubricaReceita.objects.all():
        out.rubricas_processadas += 1
        decomposto = decompor_codigo_receita(rubrica.codigo)
        if decomposto is None:
            out.avisos.append(
                f"Código com menos de 7 segmentos, não decomposto: {rubrica.codigo!r} ({rubrica.nome})"
            )
            continue
        (cat_cod, origem_cod, especie_cod, rubrica_cod, alinea_cod, subalinea_cod, tipo_cod), detalhamento = (
            decomposto
        )

        categoria, criada = CategoriaEconomica.objects.get_or_create(
            codigo=cat_cod, defaults={"nome": NOME_PENDENTE}
        )
        out.niveis_criados += int(criada)
        origem, criada = ClassificacaoReceitaOrigem.objects.get_or_create(
            categoria=categoria, codigo=origem_cod, defaults={"nome": NOME_PENDENTE}
        )
        out.niveis_criados += int(criada)
        especie, criada = ClassificacaoReceitaEspecie.objects.get_or_create(
            origem=origem, codigo=especie_cod, defaults={"nome": NOME_PENDENTE}
        )
        out.niveis_criados += int(criada)
        rubrica_stn, criada = ClassificacaoReceitaRubrica.objects.get_or_create(
            especie=especie, codigo=rubrica_cod, defaults={"nome": NOME_PENDENTE}
        )
        out.niveis_criados += int(criada)
        alinea, criada = ClassificacaoReceitaAlinea.objects.get_or_create(
            rubrica=rubrica_stn, codigo=alinea_cod, defaults={"nome": NOME_PENDENTE}
        )
        out.niveis_criados += int(criada)
        subalinea, criada = ClassificacaoReceitaSubalinea.objects.get_or_create(
            alinea=alinea, codigo=subalinea_cod, defaults={"nome": NOME_PENDENTE}
        )
        out.niveis_criados += int(criada)
        tipo, criada = ClassificacaoReceitaTipo.objects.get_or_create(
            subalinea=subalinea, codigo=tipo_cod, defaults={"nome": NOME_PENDENTE}
        )
        out.niveis_criados += int(criada)

        rubrica.classificacao_tipo = tipo
        rubrica.detalhamento_adicional = detalhamento
        rubrica.eh_deducao = _eh_prefixo_deducao(rubrica.codigo)
        rubrica.rubrica_principal = _encontrar_rubrica_principal(rubrica) if rubrica.eh_deducao else None
        rubrica.save(update_fields=[
            "classificacao_tipo", "detalhamento_adicional", "eh_deducao", "rubrica_principal",
        ])
        out.rubricas_vinculadas += 1
        if rubrica.eh_deducao and rubrica.rubrica_principal:
            out.deducoes_vinculadas += 1
        elif rubrica.eh_deducao:
            out.avisos.append(
                f"Dedução sem rubrica principal correspondente: {rubrica.codigo!r} ({rubrica.nome})"
            )

    return out


# --- Importação do Ementário oficial da Natureza de Receita (STN/SOF) ---
#
# Fonte: "Ementário da Natureza de Receita 2026" (xlsx oficial, Portaria STN/MF
# nº 1.458/2025 e Portaria Conjunta STN/SOF nº 02/2026), baixado de
# cdn.tesouro.gov.br a pedido do usuário. Sheet "ENR - 2026": cada linha tem
# colunas C/O/E/D1/DD2/D3/T (os 7 dígitos da classificação, já na mesma ordem
# dos 7 níveis construídos em popular_classificacao_receita) + NR (o código de
# 8 dígitos concatenado, sem pontos) + Especificação (o nome oficial).
#
# Confirmado inspecionando o arquivo: a STN só nomeia até o nível 6
# (Subalínea) — NENHUMA linha da planilha tem o dígito T (Tipo, nosso nível 7)
# diferente de "0". "Tipo" (Principal/Dívida Ativa/etc.) é uma convenção fixa
# da contabilidade pública brasileira aplicada por cima da classificação
# oficial, não um nível que a STN nomeia por ramo — por isso TIPO_NOME abaixo
# é um pequeno mapa fixo (não vem do arquivo), nunca usado para outro nível.
# Confirmado pelos próprios dados: só os códigos 1 e 3 aparecem em
# RubricaReceita, e os nomes ASPEC já carregam "- Princ."/"- Dív.at" como
# sufixo — exatamente o que os códigos 1/3 significam.

LARGURAS_NIVEL = (1, 1, 1, 1, 2, 1, 1)  # categoria, origem, especie, rubrica, alinea, subalinea, tipo

TIPO_NOME = {
    "1": "Principal",
    "2": "Multas e Juros de Mora",
    "3": "Dívida Ativa",
    "4": "Multas e Juros de Mora da Dívida Ativa",
}


def _chave_nr(codigos: tuple[str, ...]) -> int:
    """
    Monta a chave de 8 dígitos (igual à coluna NR do Ementário) a partir de
    uma tupla parcial de códigos (do nível mais alto até o nível desejado),
    zero-preenchendo os níveis mais profundos não informados — é assim que
    o próprio Ementário nomeia um nível intermediário (ex.: NR=11120000 é o
    nome da Rubrica "Impostos sobre o Patrimônio", com Alínea/Subalínea/Tipo
    zerados).
    """
    partes = [codigo.zfill(LARGURAS_NIVEL[i]) for i, codigo in enumerate(codigos)]
    partes += ["0" * LARGURAS_NIVEL[i] for i in range(len(codigos), len(LARGURAS_NIVEL))]
    return int("".join(partes))


def ler_nomes_ementario(caminho_arquivo) -> dict[int, str]:
    import openpyxl

    wb = openpyxl.load_workbook(caminho_arquivo, data_only=True)
    ws = wb["ENR - 2026"]

    nomes: dict[int, str] = {}
    for row in ws.iter_rows(min_row=3, max_row=ws.max_row, max_col=9):
        nr, nome = row[7].value, row[8].value
        if nr is None or not nome:
            continue
        nomes[int(nr)] = str(nome).strip()
    return nomes


@dataclass
class ResultadoImportacaoEmentarioReceita:
    nomes_disponiveis: int = 0
    categorias_atualizadas: int = 0
    origens_atualizadas: int = 0
    especies_atualizadas: int = 0
    rubricas_atualizadas: int = 0
    alineas_atualizadas: int = 0
    subalineas_atualizadas: int = 0
    tipos_atualizados: int = 0
    avisos: list[str] = field(default_factory=list)


def importar_ementario_receita(caminho_arquivo) -> ResultadoImportacaoEmentarioReceita:
    """
    Preenche o nome oficial (hoje "(a definir)") de cada nível 1-6 da
    hierarquia de receita, casando pela chave NR de 8 dígitos contra a
    planilha oficial da STN. Nível 7 (Tipo) usa TIPO_NOME (ver acima), não a
    planilha. Seguro rodar de novo a qualquer momento — sempre sobrescreve
    com o nome oficial mais recente, nunca cria nem apaga nível nenhum.
    """
    nomes = ler_nomes_ementario(caminho_arquivo)
    out = ResultadoImportacaoEmentarioReceita(nomes_disponiveis=len(nomes))

    for categoria in ClassificacaoReceitaCategoria.objects.all():
        nome = nomes.get(_chave_nr((categoria.codigo,)))
        if nome:
            categoria.nome = nome
            categoria.ano_vigencia_inicial = 2026
            categoria.save(update_fields=["nome", "ano_vigencia_inicial"])
            out.categorias_atualizadas += 1

    for origem in ClassificacaoReceitaOrigem.objects.select_related("categoria"):
        nome = nomes.get(_chave_nr((origem.categoria.codigo, origem.codigo)))
        if nome:
            origem.nome = nome
            origem.ano_vigencia_inicial = 2026
            origem.save(update_fields=["nome", "ano_vigencia_inicial"])
            out.origens_atualizadas += 1

    for especie in ClassificacaoReceitaEspecie.objects.select_related("origem__categoria"):
        nome = nomes.get(
            _chave_nr((especie.origem.categoria.codigo, especie.origem.codigo, especie.codigo))
        )
        if nome:
            especie.nome = nome
            especie.ano_vigencia_inicial = 2026
            especie.save(update_fields=["nome", "ano_vigencia_inicial"])
            out.especies_atualizadas += 1

    for rubrica in ClassificacaoReceitaRubrica.objects.select_related("especie__origem__categoria"):
        nome = nomes.get(_chave_nr((
            rubrica.especie.origem.categoria.codigo, rubrica.especie.origem.codigo,
            rubrica.especie.codigo, rubrica.codigo,
        )))
        if nome:
            rubrica.nome = nome
            rubrica.ano_vigencia_inicial = 2026
            rubrica.save(update_fields=["nome", "ano_vigencia_inicial"])
            out.rubricas_atualizadas += 1

    for alinea in ClassificacaoReceitaAlinea.objects.select_related("rubrica__especie__origem__categoria"):
        rub = alinea.rubrica
        nome = nomes.get(_chave_nr((
            rub.especie.origem.categoria.codigo, rub.especie.origem.codigo,
            rub.especie.codigo, rub.codigo, alinea.codigo,
        )))
        if nome:
            alinea.nome = nome
            alinea.ano_vigencia_inicial = 2026
            alinea.save(update_fields=["nome", "ano_vigencia_inicial"])
            out.alineas_atualizadas += 1

    for subalinea in ClassificacaoReceitaSubalinea.objects.select_related(
        "alinea__rubrica__especie__origem__categoria"
    ):
        alinea = subalinea.alinea
        rub = alinea.rubrica
        nome = nomes.get(_chave_nr((
            rub.especie.origem.categoria.codigo, rub.especie.origem.codigo,
            rub.especie.codigo, rub.codigo, alinea.codigo, subalinea.codigo,
        )))
        if nome:
            subalinea.nome = nome
            subalinea.ano_vigencia_inicial = 2026
            subalinea.save(update_fields=["nome", "ano_vigencia_inicial"])
            out.subalineas_atualizadas += 1

    for tipo in ClassificacaoReceitaTipo.objects.all():
        nome = TIPO_NOME.get(tipo.codigo)
        if nome:
            tipo.nome = nome
            tipo.save(update_fields=["nome"])
            out.tipos_atualizados += 1
        else:
            out.avisos.append(f"Código de Tipo não reconhecido: {tipo.codigo!r} (id={tipo.id})")

    return out
