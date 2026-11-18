"""
Interface comum para parsers de importação.

Cada sistema de origem (ASPEC hoje, outros no futuro) implementa um parser
que recebe o caminho de um arquivo e devolve uma lista de dicionários com
os dados já normalizados, prontos para serem gravados nos modelos de
domínio (RubricaOrcamentaria, LancamentoExecucaoOrcamentaria etc.).

Isso mantém o parser desacoplado do formato de origem: quando um novo
sistema for suportado, basta implementar um novo ParserBase e registrá-lo
em REGISTRY, sem alterar o restante do pipeline de importação.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ResultadoParsing:
    linhas: list[dict] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    metadados: dict = field(default_factory=dict)


class ParserBase(ABC):
    tipo_relatorio: str

    @abstractmethod
    def parse(self, caminho_arquivo: str | Path) -> ResultadoParsing:
        """Lê o arquivo e retorna as linhas normalizadas."""
        raise NotImplementedError
