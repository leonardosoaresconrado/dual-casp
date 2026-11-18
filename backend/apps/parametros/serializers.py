from rest_framework import serializers

from .models import Parametro


class ParametroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parametro
        fields = ["id", "chave", "descricao", "valor_booleano"]
        # chave/descricao são predefinidas pelo sistema (ver models.py) —
        # só valor_booleano é editável pelo usuário via a tela de Parâmetros.
        read_only_fields = ["chave", "descricao"]
