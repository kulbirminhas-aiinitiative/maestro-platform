import { Box, Typography, Alert } from '@mui/material';

export function ExperimentsPage() {
  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Experiments
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Track and compare your ML experiments
        </Typography>
      </Box>
      <Alert severity="info">
        Experiments view coming soon. This will display all MLflow experiments with metrics and parameters.
      </Alert>
    </Box>
  );
}
