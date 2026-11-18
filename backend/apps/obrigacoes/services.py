import calendar
import re
from datetime import date, datetime, timedelta

from .models import MESES_POR_PERIODICIDADE, EscopoObrigacao, Obrigacao, TipoObrigacao

MESES_PT = [
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]
NOME_PERIODO = {
    "BIMESTRAL": "Bimestre",
    "TRIMESTRAL": "Trimestre",
    "QUADRIMESTRAL": "Quadrimestre",
    "SEMESTRAL": "Semestre",
}


def _somar_meses(data_base: date, meses: int) -> date:
    """Soma meses sem depender de python-dateutil (não é dependência do projeto)."""
    total = data_base.month - 1 + meses
    ano = data_base.year + total // 12
    mes = total % 12 + 1
    return date(ano, mes, 1)


def calcular_prazo_limite(
    data_fim_periodo: date, meses_apos: int, dia_limite: int, ajustar_dia_util: bool = False
) -> date:
    base = _somar_meses(data_fim_periodo, meses_apos)
    ultimo_dia_mes = calendar.monthrange(base.year, base.month)[1]
    prazo = date(base.year, base.month, min(dia_limite, ultimo_dia_mes))
    if ajustar_dia_util:
        # Confirmado contra o calendário real de 2026: sábado -> +2 dias
        # (segunda-feira), domingo -> +1 dia (segunda-feira). Sem calendário
        # de feriados no sistema — só este ajuste de fim de semana.
        dia_semana = prazo.weekday()  # 5=sábado, 6=domingo
        if dia_semana == 5:
            prazo += timedelta(days=2)
        elif dia_semana == 6:
            prazo += timedelta(days=1)
    return prazo


def _periodos_do_exercicio(periodicidade: str, exercicio: int):
    """(numero_competencia, rotulo, data_inicio, data_fim) de cada competência do exercício."""
    meses_periodo = MESES_POR_PERIODICIDADE[periodicidade]
    qtd = 12 // meses_periodo
    periodos = []
    for n in range(1, qtd + 1):
        data_inicio = date(exercicio, (n - 1) * meses_periodo + 1, 1)
        fim_base = _somar_meses(data_inicio, meses_periodo - 1)
        ultimo_dia = calendar.monthrange(fim_base.year, fim_base.month)[1]
        data_fim = date(fim_base.year, fim_base.month, ultimo_dia)
        if periodicidade == "MENSAL":
            rotulo = f"{MESES_PT[data_inicio.month]}/{exercicio}"
        elif periodicidade == "ANUAL":
            rotulo = f"Exercício {exercicio}"
        else:
            rotulo = f"{n}º {NOME_PERIODO[periodicidade]}/{exercicio}"
        periodos.append((n, rotulo, data_inicio, data_fim))
    return periodos


def _unidades_gestoras_alvo(tipo, municipio):
    """
    UGs para as quais gerar/importar `Obrigacao` deste Tipo neste município:
    escopo MUNICIPIO -> [None]; escopo UNIDADE_GESTORA -> as UGs listadas em
    `unidades_gestoras_restritas` (quando configurada, ex. RREO só PMNP,
    RGF só PMNP+CMNP), senão todas as UGs ativas do município.
    """
    if tipo.escopo == EscopoObrigacao.MUNICIPIO:
        return [None]
    restritas = list(tipo.unidades_gestoras_restritas.filter(municipio=municipio, ativo=True))
    if restritas:
        return restritas
    return list(municipio.unidades_gestoras.filter(ativo=True))


def gerar_obrigacoes_pendentes(municipios) -> int:
    """
    Gera (idempotente, via get_or_create) as `Obrigacao` cujo período já
    começou até hoje, para Tipos ativos com periodicidade/prazo já
    configurados — Tipos ainda com `periodicidade=None` (os recém-semeados,
    até o usuário confirmar a IN do TCM-PA) são ignorados. Varre o exercício
    atual e o anterior (cobre competências de final de ano anterior cujo
    prazo só vence já no exercício atual, ex. ANUAL).
    """
    hoje = date.today()
    tipos = TipoObrigacao.objects.filter(
        ativo=True,
        periodicidade__isnull=False,
        prazo_meses_apos_periodo__isnull=False,
        prazo_dia_limite__isnull=False,
    )
    criadas = 0
    for tipo in tipos:
        for exercicio in (hoje.year - 1, hoje.year):
            for numero, rotulo, data_inicio, data_fim in _periodos_do_exercicio(tipo.periodicidade, exercicio):
                if data_inicio > hoje:
                    continue
                prazo_limite = calcular_prazo_limite(
                    data_fim, tipo.prazo_meses_apos_periodo, tipo.prazo_dia_limite, tipo.ajustar_prazo_para_dia_util
                )
                for municipio in municipios:
                    for ug in _unidades_gestoras_alvo(tipo, municipio):
                        _, criado = Obrigacao.objects.get_or_create(
                            tipo_obrigacao=tipo,
                            municipio=municipio,
                            unidade_gestora=ug,
                            exercicio=exercicio,
                            numero_competencia=numero,
                            defaults={
                                "rotulo_competencia": rotulo,
                                "data_fim_periodo": data_fim,
                                "prazo_limite": prazo_limite,
                            },
                        )
                        if criado:
                            criadas += 1
    return criadas


MESES_PT_POR_NOME = {nome: numero for numero, nome in enumerate(MESES_PT) if nome}

_RE_BIMESTRE_QUADRIMESTRE_COM_PREFIXO = re.compile(
    r"^(RREO|RGF)\s*[–-]\s*(\d+)º\s*(BIMESTRE|QUADRIMESTRE)$", re.IGNORECASE
)
_RE_QUADRIMESTRE_SOLTO = re.compile(r"^(\d+)º\s*Quadrimestre$", re.IGNORECASE)

_NOMES_FIXOS = {
    "LDO": "LDO",
    "Balanco Geral": "Balanço Geral",
    "Balanço Geral": "Balanço Geral",
    "Arquivo Contábil - Consolidação de Saldos": "Arquivo Contábil - Consolidação de Saldos",
    "Matriz de Saldos Contábeis - Consolidação de Saldos": "Matriz de Saldos Contábeis - Consolidação de Saldos",
}


def _interpretar_competencia(exercicio: int, resto: str):
    """
    (tipo_nome, numero_competencia, rotulo_competencia) a partir do texto da
    coluna "Competência" sem o prefixo "<exercício> - ". Ver
    `importar_calendario_literal` para o formato real de entrada (calendário
    de competências exportado de uma área logada do escritório, 2026-11-16 —
    não é um PDF da ASPEC nem a consulta pública do TCM-PA).
    """
    m = _RE_BIMESTRE_QUADRIMESTRE_COM_PREFIXO.match(resto)
    if m:
        prefixo, numero_str, unidade = m.group(1).upper(), m.group(2), m.group(3).capitalize()
        numero = int(numero_str)
        return prefixo, numero, f"{numero}º {unidade}/{exercicio}"

    m = _RE_QUADRIMESTRE_SOLTO.match(resto)
    if m:
        numero = int(m.group(1))
        return "Prestação de Contas", numero, f"{numero}º Quadrimestre/{exercicio}"

    if resto in _NOMES_FIXOS:
        tipo_nome = _NOMES_FIXOS[resto]
        return tipo_nome, 1, f"{tipo_nome} {exercicio}"

    if " - " in resto:
        tipo_nome, sufixo = resto.split(" - ", 1)
        if sufixo in MESES_PT_POR_NOME:
            return tipo_nome, MESES_PT_POR_NOME[sufixo], f"{sufixo}/{exercicio}"

    # Fallback: trata a competência inteira como um tipo anual próprio —
    # sinalizado como aviso pelo chamador se o Tipo não existir no catálogo.
    return resto, 1, f"{resto} {exercicio}"


def _parse_data_inicio(texto: str) -> date:
    return datetime.strptime(texto.strip()[:10], "%Y-%m-%d").date()


def _parse_data_limite(texto: str) -> date:
    # A coluna real pode trazer um sufixo "+ N dia(s)" (contador dinâmico de
    # dias restantes até hoje, não parte da data) — fica só o primeiro token.
    token = texto.strip().split()[0]
    return datetime.strptime(token, "%d.%m.%Y").date()


def importar_calendario_literal(municipio, texto: str) -> dict:
    """
    Importa literalmente um calendário de competências/prazos colado de uma
    área logada do escritório (formato: "<exercício> - <competência>" +
    Data Início (YYYY-MM-DD) + Data Limite (DD.MM.YYYY), uma linha por
    competência, campos separados por 2+ espaços ou tab). As datas reais do
    TCM-PA não seguem uma fórmula simples de mês+dia (há ajustes de dia
    útil/feriado) — por isso são gravadas literalmente aqui, em vez de
    recalculadas por `calcular_prazo_limite`. `unidade_gestora` é replicado
    para as UGs alvo do Tipo (todas as ativas do município, ou só as
    listadas em `unidades_gestoras_restritas` quando configurada — ver
    `_unidades_gestoras_alvo`). Usa `update_or_create` (não `get_or_create`) para que uma
    reimportação corrija prazos de competências já geradas pela fórmula
    genérica — sem nunca tocar em `status`/`verificado_por`.
    """
    linhas_processadas = 0
    avisos = []
    tipos_cache = {}

    for linha_bruta in texto.splitlines():
        linha = linha_bruta.strip()
        if not linha:
            continue
        campos = re.split(r"\t+|\s{2,}", linha)
        campos = [c.strip() for c in campos if c.strip()]
        if len(campos) < 3:
            continue

        competencia_texto, data_inicio_texto, data_limite_texto = campos[0], campos[1], campos[2]
        m_exercicio = re.match(r"^(\d{4})\s*-\s*(.+)$", competencia_texto)
        if not m_exercicio:
            avisos.append(f"Linha ignorada (sem exercício reconhecível): {linha}")
            continue
        exercicio = int(m_exercicio.group(1))
        resto = m_exercicio.group(2).strip()

        tipo_nome, numero_competencia, rotulo = _interpretar_competencia(exercicio, resto)

        if tipo_nome not in tipos_cache:
            tipos_cache[tipo_nome] = TipoObrigacao.objects.filter(nome=tipo_nome).first()
        tipo = tipos_cache[tipo_nome]
        if tipo is None:
            avisos.append(f"Tipo de Obrigação \"{tipo_nome}\" não cadastrado — linha ignorada: {linha}")
            continue

        try:
            data_inicio = _parse_data_inicio(data_inicio_texto)
            prazo_limite = _parse_data_limite(data_limite_texto)
        except ValueError:
            avisos.append(f"Data inválida — linha ignorada: {linha}")
            continue
        data_fim_periodo = data_inicio - timedelta(days=1)

        for ug in _unidades_gestoras_alvo(tipo, municipio):
            Obrigacao.objects.update_or_create(
                tipo_obrigacao=tipo,
                municipio=municipio,
                unidade_gestora=ug,
                exercicio=exercicio,
                numero_competencia=numero_competencia,
                defaults={
                    "rotulo_competencia": rotulo,
                    "data_fim_periodo": data_fim_periodo,
                    "prazo_limite": prazo_limite,
                },
            )
        linhas_processadas += 1

    return {"linhas_processadas": linhas_processadas, "avisos": avisos}
