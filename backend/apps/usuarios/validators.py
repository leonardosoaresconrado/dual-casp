import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def _calcular_digito(cpf_parcial: str) -> int:
    pesos = range(len(cpf_parcial) + 1, 1, -1)
    soma = sum(int(digito) * peso for digito, peso in zip(cpf_parcial, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto


def limpar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


def cpf_e_valido(cpf: str) -> bool:
    cpf = limpar_cpf(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    digito1 = _calcular_digito(cpf[:9])
    digito2 = _calcular_digito(cpf[:9] + str(digito1))
    return cpf[-2:] == f"{digito1}{digito2}"


def validar_cpf(cpf: str) -> None:
    if not cpf_e_valido(cpf):
        raise ValidationError(_("CPF inválido."), code="cpf_invalido")
