import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { useScope } from "../../scope/ScopeContext";

const STATUS: OpcaoCampo[] = [
  { value: "PLANEJAMENTO", label: "Em planejamento" },
  { value: "EM_EXECUCAO", label: "Em execução" },
  { value: "ENCERRADO", label: "Encerrado" },
];

export function ExerciciosPage() {
  const { municipioSelecionadoId } = useScope();

  if (!municipioSelecionadoId) return null;

  return (
    <CrudManager
      titulo="Exercícios"
      recurso="exercicios"
      campos={[
        { chave: "ano", rotulo: "Ano", tipo: "numero", obrigatorio: true },
        { chave: "status", rotulo: "Status", tipo: "select", opcoes: STATUS, obrigatorio: true },
      ]}
      parametrosExtras={{ municipio: municipioSelecionadoId }}
      valoresPadrao={{ municipio: municipioSelecionadoId, status: "PLANEJAMENTO" }}
    />
  );
}
