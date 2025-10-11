import { Box, Typography, Alert } from '@mui/material';

export function DeploymentsPage() {
  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Deployments
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Monitor and manage model deployments
        </Typography>
      </Box>
      <Alert severity="info">
        Deployments view coming soon. This will show all active model deployments with health metrics and logs.
      </Alert>
    </Box>
  );
}
