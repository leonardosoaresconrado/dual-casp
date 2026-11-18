from rest_framework import serializers

from .models import Obrigacao, TipoObrigacao


class TipoObrigacaoSerializer(serializers.ModelSerializer):
    unidades_gestoras_restritas_nomes = serializers.SerializerMethodField()

    class Meta:
        model = TipoObrigacao
        fields = [
            "id",
            "nome",
            "descricao",
            "orgao_externo",
            "escopo",
            "periodicidade",
            "prazo_meses_apos_periodo",
            "prazo_dia_limite",
            "ajustar_prazo_para_dia_util",
            "dias_antecedencia_alerta",
            "url_consulta",
            "ativo",
            "ordem",
            "unidades_gestoras_restritas_nomes",
        ]
        read_only_fields = ["unidades_gestoras_restritas_nomes"]

    def get_unidades_gestoras_restritas_nomes(self, obj):
        nomes = list(obj.unidades_gestoras_restritas.values_list("nome", flat=True))
        return ", ".join(nomes) if nomes else "Todas as UGs ativas"


class ObrigacaoSerializer(serializers.ModelSerializer):
    tipo_obrigacao_nome = serializers.CharField(source="tipo_obrigacao.nome", read_only=True)
    url_consulta = serializers.CharField(source="tipo_obrigacao.url_consulta", read_only=True)
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    # SerializerMethodField (não CharField(source="unidade_gestora.nome")) porque
    # unidade_gestora pode ser None (obrigações de escopo MUNICIPIO) — um
    # `source` com ponto quebraria com AttributeError.
    unidade_gestora_nome = serializers.SerializerMethodField()
    situacao = serializers.CharField(read_only=True)
    atrasada = serializers.BooleanField(read_only=True)
    proxima_do_prazo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Obrigacao
        fields = [
            "id",
            "tipo_obrigacao",
            "tipo_obrigacao_nome",
            "url_consulta",
            "municipio",
            "municipio_nome",
            "unidade_gestora",
            "unidade_gestora_nome",
            "exercicio",
            "numero_competencia",
            "rotulo_competencia",
            "data_fim_periodo",
            "prazo_limite",
            "status",
            "situacao",
            "atrasada",
            "proxima_do_prazo",
            "data_cumprimento",
            "protocolo",
            "observacao",
            "comprovante",
            "verificado_por",
            "verificado_em",
            "origem_registro",
            "criado_por",
            "atualizado_por",
        ]
        read_only_fields = [
            "status",
            "verificado_por",
            "verificado_em",
            "origem_registro",
            "criado_por",
            "atualizado_por",
        ]

    def get_unidade_gestora_nome(self, obj):
        return obj.unidade_gestora.nome if obj.unidade_gestora_id else None
