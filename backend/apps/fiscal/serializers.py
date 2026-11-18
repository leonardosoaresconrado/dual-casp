from rest_framework import serializers

from .models import (
    ClassificacaoReceitaAlinea,
    ClassificacaoReceitaEspecie,
    ClassificacaoReceitaOrigem,
    ClassificacaoReceitaRubrica,
    ClassificacaoReceitaSubalinea,
    ClassificacaoReceitaTipo,
    LancamentoExecucaoReceita,
    RubricaReceita,
)

CAMPOS_CLASSIFICACAO_OFICIAL = ["ativo", "origem_classificacao", "ano_vigencia_inicial", "criado_em", "atualizado_em"]


class ClassificacaoReceitaOrigemSerializer(serializers.ModelSerializer):
    categoria_codigo = serializers.CharField(source="categoria.codigo", read_only=True)

    class Meta:
        model = ClassificacaoReceitaOrigem
        fields = ["id", "categoria", "categoria_codigo", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class ClassificacaoReceitaEspecieSerializer(serializers.ModelSerializer):
    origem_codigo = serializers.CharField(source="origem.codigo", read_only=True)

    class Meta:
        model = ClassificacaoReceitaEspecie
        fields = ["id", "origem", "origem_codigo", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class ClassificacaoReceitaRubricaSerializer(serializers.ModelSerializer):
    especie_codigo = serializers.CharField(source="especie.codigo", read_only=True)

    class Meta:
        model = ClassificacaoReceitaRubrica
        fields = ["id", "especie", "especie_codigo", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class ClassificacaoReceitaAlineaSerializer(serializers.ModelSerializer):
    rubrica_codigo = serializers.CharField(source="rubrica.codigo", read_only=True)

    class Meta:
        model = ClassificacaoReceitaAlinea
        fields = ["id", "rubrica", "rubrica_codigo", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class ClassificacaoReceitaSubalineaSerializer(serializers.ModelSerializer):
    alinea_codigo = serializers.CharField(source="alinea.codigo", read_only=True)

    class Meta:
        model = ClassificacaoReceitaSubalinea
        fields = ["id", "alinea", "alinea_codigo", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class ClassificacaoReceitaTipoSerializer(serializers.ModelSerializer):
    subalinea_codigo = serializers.CharField(source="subalinea.codigo", read_only=True)

    class Meta:
        model = ClassificacaoReceitaTipo
        fields = ["id", "subalinea", "subalinea_codigo", "codigo", "nome", *CAMPOS_CLASSIFICACAO_OFICIAL]


class RubricaReceitaSerializer(serializers.ModelSerializer):
    unidade_gestora_nome = serializers.CharField(source="unidade_gestora.nome", read_only=True)
    fonte_recursos_codigo = serializers.CharField(source="fonte_recursos.codigo", read_only=True)
    fonte_recursos_nome = serializers.CharField(source="fonte_recursos.nome", read_only=True)
    classificacao_tipo_codigo = serializers.CharField(source="classificacao_tipo.codigo", read_only=True)
    rubrica_principal_codigo = serializers.CharField(source="rubrica_principal.codigo", read_only=True)

    class Meta:
        model = RubricaReceita
        fields = [
            "id", "loa", "unidade_gestora", "unidade_gestora_nome",
            "codigo", "nome", "fonte_recursos", "fonte_recursos_codigo", "fonte_recursos_nome",
            "valor_orcado", "classificacao_tipo", "classificacao_tipo_codigo", "detalhamento_adicional",
            "eh_deducao", "rubrica_principal", "rubrica_principal_codigo",
            "origem_registro", "criado_por", "atualizado_por",
        ]


class LancamentoExecucaoReceitaSerializer(serializers.ModelSerializer):
    rubrica_detalhe = RubricaReceitaSerializer(source="rubrica", read_only=True)

    class Meta:
        model = LancamentoExecucaoReceita
        fields = [
            "id", "rubrica", "rubrica_detalhe", "mes_referencia",
            "valor_bruto_no_mes", "deducao_no_mes", "anulacao_no_mes", "valor_liquido_no_mes",
            "origem_registro", "criado_por", "atualizado_por",
        ]
