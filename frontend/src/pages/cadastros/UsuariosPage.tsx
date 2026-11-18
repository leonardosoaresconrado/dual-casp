import { useEffect, useState } from "react";
import { Button, Dialog, DialogContent, DialogTitle } from "@mui/material";
import { api } from "../../api/client";
import { CrudManager, type OpcaoCampo } from "../../components/CrudManager";

export function UsuariosPage() {
  const [vinculosDe, setVinculosDe] = useState<{ id: number; nome: string } | null>(null);
  const [municipios, setMunicipios] = useState<OpcaoCampo[]>([]);
  const [unidadesGestoras, setUnidadesGestoras] = useState<OpcaoCampo[]>([]);
  const [orgaos, setOrgaos] = useState<OpcaoCampo[]>([]);

  useEffect(() => {
    api.get("/municipios/", { params: { page_size: 200 } }).then(({ data }) => {
      setMunicipios(
        (data.results ?? data).map((m: { id: number; nome: string; uf: string }) => ({
          value: m.id,
          label: `${m.nome}/${m.uf}`,
        }))
      );
    });
    api.get("/unidades-gestoras/", { params: { page_size: 500 } }).then(({ data }) => {
      setUnidadesGestoras(
        (data.results ?? data).map((u: { id: number; nome: string }) => ({ value: u.id, label: u.nome }))
      );
    });
    api.get("/orgaos/", { params: { page_size: 500 } }).then(({ data }) => {
      setOrgaos(
        (data.results ?? data).map((o: { id: number; codigo: string; nome: string }) => ({
          value: o.id,
          label: `${o.codigo} - ${o.nome}`,
        }))
      );
    });
  }, []);

  return (
    <>
      <CrudManager
        titulo="Usuários"
        recurso="usuarios"
        campos={[
          { chave: "cpf", rotulo: "CPF (só dígitos)", obrigatorio: true },
          { chave: "nome_completo", rotulo: "Nome completo", obrigatorio: true },
          { chave: "email", rotulo: "E-mail" },
          { chave: "telefone", rotulo: "Telefone" },
          { chave: "password", rotulo: "Senha (em branco mantém a atual / sem acesso se nunca definida)", tipo: "senha" },
          { chave: "is_equipe_escritorio", rotulo: "Equipe do escritório", tipo: "booleano" },
          { chave: "is_active", rotulo: "Ativo", tipo: "booleano" },
        ]}
        valoresPadrao={{ is_active: true, is_equipe_escritorio: false }}
        colunasExtras={[
          {
            chave: "vinculos",
            rotulo: "Vínculos de Acesso",
            render: (item) => (
              <Button
                size="small"
                onClick={() => setVinculosDe({ id: Number(item.id), nome: String(item.nome_completo) })}
              >
                Gerenciar
              </Button>
            ),
          },
        ]}
      />

      <Dialog open={vinculosDe !== null} onClose={() => setVinculosDe(null)} maxWidth="md" fullWidth>
        <DialogTitle>Vínculos de Acesso — {vinculosDe?.nome}</DialogTitle>
        <DialogContent>
          {vinculosDe && (
            <CrudManager
              titulo=""
              recurso="vinculos-acesso"
              campos={[
                { chave: "municipio", rotulo: "Município", tipo: "select", opcoes: municipios, obrigatorio: true },
                {
                  chave: "unidade_gestora",
                  rotulo: "Unidade Gestora (em branco = município inteiro)",
                  tipo: "select",
                  opcoes: unidadesGestoras,
                },
                {
                  chave: "orgao",
                  rotulo: "Órgão (em branco = toda a UG/município)",
                  tipo: "select",
                  opcoes: orgaos,
                },
                {
                  chave: "papel",
                  rotulo: "Papel",
                  tipo: "select",
                  opcoes: [
                    { value: "ADMIN", label: "Administrador" },
                    { value: "GESTOR", label: "Gestor" },
                    { value: "ANALISTA", label: "Analista" },
                    { value: "VISUALIZACAO", label: "Somente visualização" },
                  ],
                  obrigatorio: true,
                },
              ]}
              parametrosExtras={{ usuario: vinculosDe.id }}
              valoresPadrao={{ usuario: vinculosDe.id, papel: "VISUALIZACAO" }}
              dependenciasRecarregar={[municipios.length, unidadesGestoras.length, orgaos.length]}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
