import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Municipio } from "../api/types";
import { useAuth } from "../auth/AuthContext";

interface ScopeContextValue {
  municipios: Municipio[];
  municipioSelecionadoId: number | null;
  setMunicipioSelecionadoId: (id: number) => void;
  carregando: boolean;
}

const ScopeContext = createContext<ScopeContextValue | undefined>(undefined);

export function ScopeProvider({ children }: { children: ReactNode }) {
  const { usuario } = useAuth();
  const [municipios, setMunicipios] = useState<Municipio[]>([]);
  const [municipioSelecionadoId, setMunicipioSelecionadoId] = useState<number | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    if (!usuario) return;
    api.get<{ results: Municipio[] }>("/municipios/", { params: { page_size: 200 } }).then(({ data }) => {
      setMunicipios(data.results);
      if (data.results.length > 0) {
        setMunicipioSelecionadoId(data.results[0].id);
      }
      setCarregando(false);
    });
  }, [usuario]);

  return (
    <ScopeContext.Provider
      value={{ municipios, municipioSelecionadoId, setMunicipioSelecionadoId, carregando }}
    >
      {children}
    </ScopeContext.Provider>
  );
}

export function useScope() {
  const ctx = useContext(ScopeContext);
  if (!ctx) throw new Error("useScope deve ser usado dentro de ScopeProvider");
  return ctx;
}
