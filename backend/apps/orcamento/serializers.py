from rest_framework import serializers

from .models import (
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
    Programa,
    RubricaOrcamentaria,
    Subelemento,
    Subfuncao,
)


class FuncaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Funcao
        fields = ["id", "codigo", "nome"]


class SubfuncaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subfuncao
        fields = ["id", "codigo", "nome"]


CAMPOS_CLASSIFICACAO_OFICIAL = ["ativo", "origem_classificacao", "ano_vigencia_inicial", "criado_em", "atualizado_em"]


class CategoriaEconomicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaEconomica
        fields = ["id", "codigo", "nome", "natureza", *CAMPOS_CLASSIFICACAO_OFICIAL]


class GrupoNaturezaDespesaSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoNaturezaDespesa
        fields = ["id", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class ModalidadeAplicacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModalidadeAplicacao
        fields = ["id", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class SubelementoSerializer(serializers.ModelSerializer):
    elemento_codigo = serializers.CharField(source="elemento.codigo", read_only=True)

    class Meta:
        model = Subelemento
        fields = ["id", "elemento", "elemento_codigo", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class ElementoDespesaSerializer(serializers.ModelSerializer):
    subelementos = SubelementoSerializer(many=True, read_only=True)

    class Meta:
        model = ElementoDespesa
        fields = ["id", "codigo", "nome", "subelementos", *CAMPOS_CLASSIFICACAO_OFICIAL]


class FonteRecursosSerializer(serializers.ModelSerializer):
    # `natureza`/`natureza_label` são `@property`s derivadas do 1º dígito
    # do código (ver model) — não colunas reais, por isso precisam de
    # declaração explícita pro DRF saber serializar.
    natureza = serializers.CharField(read_only=True, allow_null=True)
    natureza_label = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = FonteRecursos
        fields = ["id", "codigo", "nome", "tipo", "natureza", "natureza_label"]


class AcaoSerializer(serializers.ModelSerializer):
    funcao_codigo = serializers.CharField(read_only=True, allow_null=True)
    funcao_nome = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Acao
        fields = [
            "id", "programa", "codigo", "nome", "tipo",
            "desconsiderar_pnae_peae", "funcao_codigo", "funcao_nome",
        ]


class ProgramaSerializer(serializers.ModelSerializer):
    acoes = AcaoSerializer(many=True, read_only=True)

    class Meta:
        model = Programa
        fields = ["id", "loa", "codigo", "nome", "objetivo", "acoes"]


class ExercicioSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    loa_id = serializers.SerializerMethodField()

    class Meta:
        model = Exercicio
        fields = ["id", "municipio", "municipio_nome", "ano", "status", "loa_id"]

    def get_loa_id(self, obj):
        return getattr(obj.loa, "id", None) if hasattr(obj, "loa") else None


class LOASerializer(serializers.ModelSerializer):
    class Meta:
        model = LOA
        fields = [
            "id", "exercicio", "numero_lei", "data_sancao",
            "valor_total_receita_prevista", "valor_total_despesa_fixada", "observacoes",
        ]


class RubricaOrcamentariaSerializer(serializers.ModelSerializer):
    unidade_gestora_nome = serializers.CharField(source="unidade_gestora.nome", read_only=True)
    orgao_codigo = serializers.CharField(source="orgao.codigo", read_only=True)
    orgao_nome = serializers.CharField(source="orgao.nome", read_only=True)
    unidade_orcamentaria_codigo = serializers.CharField(source="unidade_orcamentaria.codigo", read_only=True)
    unidade_orcamentaria_nome = serializers.CharField(source="unidade_orcamentaria.nome", read_only=True)
    funcao_codigo = serializers.CharField(source="funcao.codigo", read_only=True)
    funcao_nome = serializers.CharField(source="funcao.nome", read_only=True)
    subfuncao_codigo = serializers.CharField(source="subfuncao.codigo", read_only=True)
    subfuncao_nome = serializers.CharField(source="subfuncao.nome", read_only=True)
    programa_codigo = serializers.CharField(source="programa.codigo", read_only=True)
    programa_nome = serializers.CharField(source="programa.nome", read_only=True)
    acao_codigo = serializers.CharField(source="acao.codigo", read_only=True)
    acao_nome = serializers.CharField(source="acao.nome", read_only=True)
    categoria_economica_codigo = serializers.CharField(source="categoria_economica.codigo", read_only=True)
    categoria_economica_nome = serializers.CharField(source="categoria_economica.nome", read_only=True)
    grupo_natureza_despesa_codigo = serializers.CharField(source="grupo_natureza_despesa.codigo", read_only=True)
    grupo_natureza_despesa_nome = serializers.CharField(source="grupo_natureza_despesa.nome", read_only=True)
    modalidade_aplicacao_codigo = serializers.CharField(source="modalidade_aplicacao.codigo", read_only=True)
    modalidade_aplicacao_nome = serializers.CharField(source="modalidade_aplicacao.nome", read_only=True)
    elemento_despesa_codigo = serializers.CharField(source="elemento_despesa.codigo", read_only=True)
    elemento_despesa_nome = serializers.CharField(source="elemento_despesa.nome", read_only=True)
    subelemento_codigo = serializers.CharField(source="subelemento.codigo", read_only=True)
    subelemento_nome = serializers.CharField(source="subelemento.nome", read_only=True)
    fonte_recursos_codigo = serializers.CharField(source="fonte_recursos.codigo", read_only=True)
    fonte_recursos_nome = serializers.CharField(source="fonte_recursos.nome", read_only=True)
    origem_dotacao_label = serializers.CharField(source="get_origem_dotacao_display", read_only=True)

    class Meta:
        model = RubricaOrcamentaria
        fields = [
            "id", "loa", "unidade_gestora", "unidade_gestora_nome",
            "orgao", "orgao_codigo", "orgao_nome",
            "unidade_orcamentaria", "unidade_orcamentaria_codigo", "unidade_orcamentaria_nome",
            "funcao", "funcao_codigo", "funcao_nome",
            "subfuncao", "subfuncao_codigo", "subfuncao_nome",
            "programa", "programa_codigo", "programa_nome",
            "acao", "acao_codigo", "acao_nome",
            "categoria_economica", "categoria_economica_codigo", "categoria_economica_nome",
            "grupo_natureza_despesa", "grupo_natureza_despesa_codigo", "grupo_natureza_despesa_nome",
            "modalidade_aplicacao", "modalidade_aplicacao_codigo", "modalidade_aplicacao_nome",
            "elemento_despesa", "elemento_despesa_codigo", "elemento_despesa_nome",
            "subelemento", "subelemento_codigo", "subelemento_nome",
            "fonte_recursos", "fonte_recursos_codigo", "fonte_recursos_nome",
            "dotacao_inicial", "origem_dotacao", "origem_dotacao_label",
            "origem_registro", "criado_por", "atualizado_por",
        ]


class LancamentoExecucaoOrcamentariaSerializer(serializers.ModelSerializer):
    saldo_a_empenhar = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    saldo_a_liquidar = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    saldo_a_pagar = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    rubrica_detalhe = RubricaOrcamentariaSerializer(source="rubrica", read_only=True)

    class Meta:
        model = LancamentoExecucaoOrcamentaria
        fields = [
            "id", "rubrica", "rubrica_detalhe", "mes_referencia",
            "dotacao_inicial", "creditos_suplementares", "creditos_especiais", "anulacoes",
            "dotacao_atualizada", "empenhado_no_mes", "empenhado_acumulado",
            "liquidado_no_mes", "liquidado_acumulado", "pago_no_mes", "pago_acumulado",
            "saldo_a_empenhar", "saldo_a_liquidar", "saldo_a_pagar", "importacao",
            "origem_registro", "criado_por", "atualizado_por",
        ]


class EmpenhoMovimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmpenhoMovimento
        fields = [
            "id", "mes_referencia",
            "valor_empenho_no_mes", "valor_liquidado_no_mes", "valor_pago_no_mes",
        ]


class EmpenhoSerializer(serializers.ModelSerializer):
    unidade_gestora_nome = serializers.CharField(source="unidade_gestora.nome", read_only=True)
    saldo_a_liquidar = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    saldo_a_pagar = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    movimentos = EmpenhoMovimentoSerializer(many=True, read_only=True)

    class Meta:
        model = Empenho
        fields = [
            "id", "unidade_gestora", "unidade_gestora_nome", "rubrica",
            "numero", "data_empenho", "credor", "historico",
            "valor_empenho", "valor_liquidado", "valor_pago",
            "saldo_a_liquidar", "saldo_a_pagar", "movimentos",
            "origem_registro", "criado_por", "atualizado_por",
        ]
        # valor_empenho/liquidado/pago são agregados de EmpenhoMovimento
        # (ver Empenho.recalcular_totais) — nunca editáveis diretamente,
        # mesmo com CRUD liberado, senão o total destoa da soma real dos
        # movimentos.
        read_only_fields = ["valor_empenho", "valor_liquidado", "valor_pago"]
