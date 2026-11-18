from django.contrib.auth.base_user import BaseUserManager

from .validators import limpar_cpf


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _criar_usuario(self, cpf, nome_completo, password, **extra_fields):
        if not cpf:
            raise ValueError("O CPF é obrigatório.")
        cpf = limpar_cpf(cpf)
        usuario = self.model(cpf=cpf, nome_completo=nome_completo, **extra_fields)
        usuario.set_password(password)
        usuario.full_clean()
        usuario.save(using=self._db)
        return usuario

    def create_user(self, cpf, nome_completo, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._criar_usuario(cpf, nome_completo, password, **extra_fields)

    def create_superuser(self, cpf, nome_completo, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_equipe_escritorio", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário precisa ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa ter is_superuser=True.")
        return self._criar_usuario(cpf, nome_completo, password, **extra_fields)

    def get_by_natural_key(self, cpf):
        return self.get(cpf=limpar_cpf(cpf))
