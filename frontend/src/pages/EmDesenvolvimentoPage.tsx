import { Box, Paper, Typography } from "@mui/material";
import ConstructionIcon from "@mui/icons-material/Construction";

export function EmDesenvolvimentoPage({ titulo, descricao }: { titulo: string; descricao?: string }) {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        {titulo}
      </Typography>
      <Paper variant="outlined" sx={{ p: 6, textAlign: "center", color: "text.secondary" }}>
        <ConstructionIcon sx={{ fontSize: 48, mb: 2 }} />
        <Typography variant="body1">
          {descricao ?? "Em desenvolvimento — ainda não há dados importados nem backend para esta seção."}
        </Typography>
      </Paper>
    </Box>
  );
}
