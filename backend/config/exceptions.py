from django.db.models.deletion import ProtectedError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """
    DRF's padrão não trata `ProtectedError` (toda FK `on_delete=PROTECT`
    estourava 500 em vez de um 400 legível) — isso ficou mais provável de
    acontecer de verdade depois que os 9 "fatos" importados ganharam DELETE
    pela API (ex.: apagar uma RubricaOrcamentaria que já tem Empenho
    vinculado). Qualquer outro erro continua pelo handler padrão do DRF.
    """
    if isinstance(exc, ProtectedError):
        protegidos = ", ".join(sorted({type(obj).__name__ for obj in exc.protected_objects}))
        return Response(
            {"detail": f"Não é possível excluir: existem registros vinculados ({protegidos})."},
            status=400,
        )
    return drf_exception_handler(exc, context)
