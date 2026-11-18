import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { useScope } from "../../scope/ScopeContext";

const OPCOES_PODER: OpcaoCampo[] = [
  { value: "EXECUTIVO", label: "Executivo" },
  { value: "LEGISLATIVO", label: "Legislativo" },
];

export function UnidadesGestorasPage() {
  const { municipioSelecionadoId } = useScope();

  if (!municipioSelecionadoId) return null;

  return (
    <CrudManager
      titulo="Unidades Gestoras"
      recurso="unidades-gestoras"
      campos={[
        { chave: "codigo", rotulo: "Código", obrigatorio: true },
        { chave: "nome", rotulo: "Nome", obrigatorio: true },
        { chave: "poder", rotulo: "Poder", tipo: "select", opcoes: OPCOES_PODER, obrigatorio: true },
        { chave: "cnpj", rotulo: "CNPJ" },
        { chave: "ativo", rotulo: "Ativo", tipo: "booleano" },
      ]}
      parametrosExtras={{ municipio: municipioSelecionadoId }}
      valoresPadrao={{ municipio: municipioSelecionadoId, poder: "EXECUTIVO", ativo: true }}
    />
  );
}
