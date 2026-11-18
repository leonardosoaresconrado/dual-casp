import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";
import { useScope } from "../../scope/ScopeContext";

export function LOAPage() {
  const { municipioSelecionadoId } = useScope();
  const [opcoesExercicio, setOpcoesExercicio] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    if (!municipioSelecionadoId) return;
    api
      .get("/exercicios/", { params: { municipio: municipioSelecionadoId, page_size: 50 } })
      .then(({ data }) => {
        setOpcoesExercicio(
          (data.results ?? data).map((e: { id: number; ano: number }) => ({
            value: e.id,
            label: `Exercício ${e.ano}`,
          }))
        );
      });
  }, [municipioSelecionadoId]);

  return (
    <CrudManager
      titulo="LOA - Lei Orçamentária Anual"
      recurso="loas"
      campos={[
        { chave: "exercicio", rotulo: "Exercício", tipo: "select", opcoes: opcoesExercicio, obrigatorio: true },
        { chave: "numero_lei", rotulo: "Número da Lei", obrigatorio: true },
        { chave: "data_sancao", rotulo: "Data de Sanção", tipo: "data" },
        { chave: "valor_total_receita_prevista", rotulo: "Receita Total Prevista", tipo: "decimal", obrigatorio: true },
        { chave: "valor_total_despesa_fixada", rotulo: "Despesa Total Fixada", tipo: "decimal", obrigatorio: true },
        { chave: "observacoes", rotulo: "Observações", tipo: "textarea" },
      ]}
      dependenciasRecarregar={[opcoesExercicio.length]}
    />
  );
}
