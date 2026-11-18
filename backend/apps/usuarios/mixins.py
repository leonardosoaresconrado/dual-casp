from apps.orcamento.models import OrigemRegistro


class RegistroManualMixin:
    """
    Para ViewSets de "fatos" importados que ganharam CRUD manual (Empenho,
    LancamentoExecucaoOrcamentaria, RubricaReceita, etc.) — marca qualquer
    linha criada/editada pela API como MANUAL e registra quem mexeu.
    Linhas criadas pelos management commands de import nunca passam por
    aqui (chamam os services diretamente via ORM), então continuam
    IMPORTADO com criado_por/atualizado_por nulos, como esperado.
    """

    def perform_create(self, serializer):
        serializer.save(
            origem_registro=OrigemRegistro.MANUAL,
            criado_por=self.request.user,
            atualizado_por=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(atualizado_por=self.request.user)
