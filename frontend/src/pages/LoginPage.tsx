import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import { isAxiosError } from "axios";
import { useAuth } from "../auth/AuthContext";

function formatarCpf(valor: string): string {
  const digitos = valor.replace(/\D/g, "").slice(0, 11);
  const partes = [digitos.slice(0, 3), digitos.slice(3, 6), digitos.slice(6, 9)].filter(Boolean);
  let formatado = partes.join(".");
  if (digitos.length > 9) formatado += `-${digitos.slice(9, 11)}`;
  return formatado;
}

export function LoginPage() {
  const { usuario, login } = useAuth();
  const [cpf, setCpf] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await login(cpf, senha);
    } catch (err) {
      // Distinguir "servidor recusou as credenciais" de "não deu pra
      // alcançar o servidor" — tratar os dois como "CPF ou senha
      // inválidos" já confundiu o usuário mais de uma vez quando o
      // problema real era o backend estar fora do ar, não a senha.
      if (isAxiosError(err) && !err.response) {
        setErro("Não foi possível conectar ao servidor. Verifique se o backend está rodando.");
      } else {
        setErro("CPF ou senha inválidos.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        bgcolor: "grey.100",
      }}
    >
      <Paper elevation={3} sx={{ p: 4, width: 360 }}>
        <Typography variant="h5" component="h1" gutterBottom>
          CASP
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Assessoria e Consultoria Contábil
        </Typography>
        <Box
          component="form"
          onSubmit={handleSubmit}
          sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 2 }}
        >
          <TextField
            label="CPF"
            value={cpf}
            onChange={(e) => setCpf(formatarCpf(e.target.value))}
            placeholder="000.000.000-00"
            autoFocus
            required
            fullWidth
          />
          <TextField
            label="Senha"
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required
            fullWidth
          />
          {erro && <Alert severity="error">{erro}</Alert>}
          <Button type="submit" variant="contained" size="large" disabled={enviando}>
            {enviando ? "Entrando..." : "Entrar"}
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
