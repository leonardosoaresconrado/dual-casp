from rest_framework import serializers

from .models import (
    RestoAPagar,
    SaldoBalancoConta,
    SaldoBalancoContaFonte,
    SaldoContaBancaria,
    SaldoContaBancariaFonte,
)


class SaldoBalancoContaFonteSerializer(serializers.ModelSerializer):
    fonte_recursos_codigo = serializers.CharField(source="fonte_recursos.codigo", read_only=True)
    fonte_recursos_nome = serializers.CharField(source="fonte_recursos.nome", read_only=True)

    class Meta:
        model = SaldoBalancoContaFonte
        fields = ["id", "fonte_recursos", "fonte_recursos_codigo", "fonte_recursos_nome", "valor", "natureza"]


class SaldoBalancoContaSerializer(serializers.ModelSerializer):
    unidade_gestora_nome = serializers.CharField(source="unidade_gestora.nome", read_only=True)
    fontes = SaldoBalancoContaFonteSerializer(many=True, read_only=True)

    class Meta:
        model = SaldoBalancoConta
        fields = [
            "id", "unidade_gestora", "unidade_gestora_nome", "data_referencia", "categoria",
            "codigo_conta", "banco", "numero_conta", "apelido", "valor", "natureza", "fontes",
            "origem_registro", "criado_por", "atualizado_por",
        ]


class SaldoContaBancariaFonteSerializer(serializers.ModelSerializer):
    fonte_recursos_codigo = serializers.CharField(source="fonte_recursos.codigo", read_only=True)
    fonte_recursos_nome = serializers.CharField(source="fonte_recursos.nome", read_only=True)

    class Meta:
        model = SaldoContaBancariaFonte
        fields = ["id", "fonte_recursos", "fonte_recursos_codigo", "fonte_recursos_nome", "valor", "natureza"]


class SaldoContaBancariaSerializer(serializers.ModelSerializer):
    unidade_gestora_nome = serializers.CharField(source="unidade_gestora.nome", read_only=True)
    fontes = SaldoContaBancariaFonteSerializer(many=True, read_only=True)

    class Meta:
        model = SaldoContaBancaria
        fields = [
            "id", "unidade_gestora", "unidade_gestora_nome", "mes_referencia", "data_referencia",
            "banco", "numero_conta", "apelido", "saldo_pre_pagamentos_previstos", "saldo_nao_comprometido", "fontes",
            "origem_registro", "criado_por", "atualizado_por",
        ]


class RestoAPagarSerializer(serializers.ModelSerializer):
    unidade_gestora_nome = serializers.CharField(source="unidade_gestora.nome", read_only=True)
    fonte_recursos_codigo = serializers.CharField(source="fonte_recursos.codigo", read_only=True)
    fonte_recursos_nome = serializers.CharField(source="fonte_recursos.nome", read_only=True)
    pago_total = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    orgao_nome = serializers.CharField(source="orgao.nome", read_only=True, default="")
    unidade_orcamentaria_nome = serializers.CharField(source="unidade_orcamentaria.nome", read_only=True, default="")
    elemento_despesa_codigo = serializers.CharField(source="elemento_despesa.codigo", read_only=True, default="")
    elemento_despesa_nome = serializers.CharField(source="elemento_despesa.nome", read_only=True, default="")

    class Meta:
        model = RestoAPagar
        fields = [
            "id", "unidade_gestora", "unidade_gestora_nome", "fonte_recursos",
            "fonte_recursos_codigo", "fonte_recursos_nome", "mes_referencia",
            "exercicio_origem", "numero_empenho", "inscricao_processada", "inscricao_nao_processada",
            "reinscricao", "cancelamento", "liquidacao", "rpp_pago", "rpnp_pago", "pago_total",
            "credor_nome", "orgao", "orgao_nome", "unidade_orcamentaria", "unidade_orcamentaria_nome",
            "elemento_despesa", "elemento_despesa_codigo", "elemento_despesa_nome",
            "classificacao_funcional_programatica", "acao_nome", "classificacao_economica_codigo",
            "origem_registro", "criado_por", "atualizado_por",
        ]
