from rest_framework import serializers

from .models import Usuario, VinculoAcesso


class VinculoAcessoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)
    municipio_nome = serializers.CharField(source="municipio.nome", read_only=True)
    unidade_gestora_nome = serializers.CharField(
        source="unidade_gestora.nome", read_only=True, default=None
    )
    orgao_nome = serializers.CharField(source="orgao.nome", read_only=True, default=None)

    class Meta:
        model = VinculoAcesso
        fields = [
            "id", "usuario", "usuario_nome", "municipio", "municipio_nome",
            "unidade_gestora", "unidade_gestora_nome", "orgao", "orgao_nome", "papel",
        ]


class UsuarioSerializer(serializers.ModelSerializer):
    vinculos_acesso = VinculoAcessoSerializer(many=True, read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = Usuario
        fields = [
            "id", "cpf", "cpf_formatado", "nome_completo", "email", "telefone",
            "is_equipe_escritorio", "is_active", "vinculos_acesso", "password",
        ]

    def create(self, validated_data):
        senha = validated_data.pop("password", None)
        usuario = Usuario(**validated_data)
        if senha:
            usuario.set_password(senha)
        else:
            usuario.set_unusable_password()
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        senha = validated_data.pop("password", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if senha:
            instance.set_password(senha)
        instance.save()
        return instance
