from rest_framework import serializers

from .models import Municipio, Orgao, UnidadeGestora, UnidadeOrcamentaria


class UnidadeOrcamentariaSerializer(serializers.ModelSerializer):
    orgao_nome = serializers.CharField(source="orgao.nome", read_only=True)
    unidade_gestora_nome = serializers.CharField(source="unidade_gestora.nome", read_only=True)

    class Meta:
        model = UnidadeOrcamentaria
        fields = [
            "id", "orgao", "orgao_nome", "unidade_gestora", "unidade_gestora_nome",
            "codigo", "nome", "ativo",
        ]


class OrgaoSerializer(serializers.ModelSerializer):
    unidades_orcamentarias = UnidadeOrcamentariaSerializer(many=True, read_only=True)

    class Meta:
        model = Orgao
        fields = ["id", "municipio", "codigo", "nome", "ativo", "unidades_orcamentarias"]


class UnidadeGestoraSerializer(serializers.ModelSerializer):
    unidades_orcamentarias = UnidadeOrcamentariaSerializer(many=True, read_only=True)

    class Meta:
        model = UnidadeGestora
        fields = [
            "id", "municipio", "codigo", "nome", "poder", "cnpj", "ativo",
            "unidades_orcamentarias",
        ]


class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipio
        fields = ["id", "nome", "uf", "codigo_ibge", "ativo"]
