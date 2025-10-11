import { Box, Typography, Alert } from '@mui/material';

export function DatasetsPage() {
  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Datasets
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage and explore your training datasets
        </Typography>
      </Box>
      <Alert severity="info">
        Datasets view coming soon. This will display dataset catalog with profiling and lineage information.
      </Alert>
    </Box>
  );
}
