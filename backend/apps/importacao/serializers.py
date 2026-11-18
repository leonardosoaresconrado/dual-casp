from rest_framework import serializers

from .models import Importacao


class ImportacaoSerializer(serializers.ModelSerializer):
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)
    sistema_origem_label = serializers.CharField(source="get_sistema_origem_display", read_only=True)
    tipo_relatorio_label = serializers.CharField(source="get_tipo_relatorio_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Importacao
        fields = [
            "id", "municipio", "municipio_nome", "exercicio",
            "sistema_origem", "sistema_origem_label",
            "tipo_relatorio", "tipo_relatorio_label",
            "arquivo", "status", "status_label", "mensagem_erro", "linhas_importadas",
            "usuario", "usuario_nome", "criado_em", "processado_em",
        ]
        read_only_fields = ["usuario", "status", "mensagem_erro", "linhas_importadas", "processado_em"]
