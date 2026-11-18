from rest_framework import serializers

from .models import (
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


class ApuracaoDTPSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)
    deducoes_rcl = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = ApuracaoDTP
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "rcl",
            "deducao_emendas_individuais", "deducao_emendas_bancada", "deducao_agentes_saude", "deducao_outras",
            "deducoes_rcl", "rcl_ajustada", "despesa_total_pessoal", "percentual_dtp",
            "limite_maximo_valor", "limite_maximo_percentual",
            "limite_prudencial_valor", "limite_prudencial_percentual",
            "limite_alerta_valor", "limite_alerta_percentual",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]


class ApuracaoMDEReceitaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApuracaoMDEReceitaItem
        fields = ["id", "grupo", "codigo", "rotulo", "valor"]


class ApuracaoMDESerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)
    total_gerencial_1 = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    total_gerencial_2 = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    total_gerencial_3 = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    indice_gerencial_1 = serializers.DecimalField(max_digits=7, decimal_places=4, read_only=True, allow_null=True)
    indice_gerencial_2 = serializers.DecimalField(max_digits=7, decimal_places=4, read_only=True, allow_null=True)
    indice_gerencial_3 = serializers.DecimalField(max_digits=7, decimal_places=4, read_only=True, allow_null=True)
    total_gerencial_1_desconsiderando_pnae = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    total_gerencial_2_desconsiderando_pnae = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    total_gerencial_3_desconsiderando_pnae = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    indice_gerencial_1_desconsiderando_pnae = serializers.DecimalField(
        max_digits=7, decimal_places=4, read_only=True, allow_null=True
    )
    indice_gerencial_2_desconsiderando_pnae = serializers.DecimalField(
        max_digits=7, decimal_places=4, read_only=True, allow_null=True
    )
    indice_gerencial_3_desconsiderando_pnae = serializers.DecimalField(
        max_digits=7, decimal_places=4, read_only=True, allow_null=True
    )
    # Somente leitura aqui: os itens são criados/atualizados só pelo
    # pipeline de import (bulk_create em services.importar_mde_e_magisterio),
    # nunca diretamente pela API — editar um item manualmente seria feito
    # via um endpoint próprio de ApuracaoMDEReceitaItem, não implementado
    # ainda (mesmo padrão read-only já usado pelos filhos *Fonte).
    itens_receita = ApuracaoMDEReceitaItemSerializer(many=True, read_only=True)

    class Meta:
        model = ApuracaoMDE
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "receita_impostos", "receita_transferencias", "itens_receita",
            "base_calculo", "minimo_constitucional",
            "despesa_mde_empenhada", "despesa_mde_liquidada", "despesa_mde_paga",
            "fundeb_transferido", "excedente_fundeb_nao_aplicado", "cancelamento_rp",
            "aplicacao_pnae_recursos_proprios", "despesa_ensino_medio_superior_recursos_proprios",
            "valor_exigido", "valor_aplicado", "percentual_aplicado",
            "total_gerencial_1", "total_gerencial_2", "total_gerencial_3",
            "indice_gerencial_1", "indice_gerencial_2", "indice_gerencial_3",
            "total_gerencial_1_desconsiderando_pnae", "total_gerencial_2_desconsiderando_pnae",
            "total_gerencial_3_desconsiderando_pnae",
            "indice_gerencial_1_desconsiderando_pnae", "indice_gerencial_2_desconsiderando_pnae",
            "indice_gerencial_3_desconsiderando_pnae",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]


class ApuracaoMagisterioFundebSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApuracaoMagisterioFundeb
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "fundeb_receita_total", "valor_exigido", "valor_aplicado", "percentual_aplicado",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]


class ApuracaoETIFundebSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApuracaoETIFundeb
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "fundeb_receita_total", "valor_exigido", "valor_aplicado", "percentual_aplicado",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]


class ApuracaoASPSSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)
    percentual_gerencial = serializers.DecimalField(max_digits=7, decimal_places=4, read_only=True, allow_null=True)

    class Meta:
        model = ApuracaoASPS
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "receita_impostos_transferencias", "base_calculo", "minimo_constitucional",
            "despesa_asps_empenhada", "despesa_asps_liquidada", "despesa_asps_paga",
            "percentual_aplicado", "percentual_gerencial",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]


class ApuracaoVAATEducacaoInfantilSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApuracaoVAATEducacaoInfantil
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "valor_exigido", "valor_aplicado", "percentual_aplicado",
            "percentual_vaat_publicado", "portaria_vaat_referencia",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]


class ApuracaoVAATDespesaCapitalSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApuracaoVAATDespesaCapital
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "valor_exigido", "valor_aplicado", "percentual_aplicado",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]


class ApuracaoValorNaoAplicadoFundebSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApuracaoValorNaoAplicadoFundeb
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "valor_maximo_permitido", "valor_nao_aplicado", "valor_nao_aplicado_apos_ajuste",
            "valor_excedente_ao_maximo_permitido", "percentual_nao_aplicado",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]


class ApuracaoReprogramacaoFundebOrigemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApuracaoReprogramacaoFundebOrigem
        fields = [
            "id", "origem",
            "valor_superavit_permitido_exercicio_anterior", "valor_nao_aplicado_exercicio_anterior",
            "valor_aplicado_ate_primeiro_quadrimestre", "valor_aplicado_apos_primeiro_quadrimestre",
            "valor_nao_aplicado_ate_primeiro_quadrimestre_atual",
        ]


class ApuracaoReprogramacaoFundebSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    cumpre_limite = serializers.BooleanField(read_only=True)
    # Somente leitura — mesmo racional de `itens_receita` acima.
    origens = ApuracaoReprogramacaoFundebOrigemSerializer(many=True, read_only=True)

    class Meta:
        model = ApuracaoReprogramacaoFundeb
        fields = [
            "id", "municipio", "municipio_nome", "exercicio", "bimestre",
            "valor_superavit_permitido_exercicio_anterior", "valor_nao_aplicado_exercicio_anterior",
            "valor_aplicado_ate_primeiro_quadrimestre", "valor_aplicado_apos_primeiro_quadrimestre",
            "valor_aplicado_ate_primeiro_quadrimestre_empenhado", "valor_aplicado_apos_primeiro_quadrimestre_empenhado",
            "valor_nao_aplicado_ate_primeiro_quadrimestre_atual", "origens",
            "cumpre_limite", "origem_registro", "criado_por", "atualizado_por",
        ]
