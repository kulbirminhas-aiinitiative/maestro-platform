import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import { mlflowApi } from '../api/mlflow';

interface Model {
  name: string;
  latest_version: string;
  description?: string;
  tags?: Record<string, string>;
  last_updated: string;
}

export function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await mlflowApi.getModels();
      setModels(data);
    } catch (err) {
      setError('Failed to load models. Please check your connection to MLflow.');
      console.error('Error loading models:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredModels = models.filter((model) =>
    model.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Model Registry
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Browse and manage your machine learning models
        </Typography>
      </Box>

      <TextField
        fullWidth
        variant="outlined"
        placeholder="Search models..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{ mb: 3 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
      />

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {!loading && !error && filteredModels.length === 0 && (
        <Alert severity="info">
          No models found. {searchTerm && 'Try a different search term.'}
        </Alert>
      )}

      <Grid container spacing={3}>
        {filteredModels.map((model) => (
          <Grid item xs={12} sm={6} md={4} key={model.name}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="h6" gutterBottom>
                  {model.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {model.description || 'No description available'}
                </Typography>
                <Box sx={{ mb: 1 }}>
                  <Chip
                    label={`v${model.latest_version}`}
                    size="small"
                    color="primary"
                    sx={{ mr: 1 }}
                  />
                  {model.tags && Object.entries(model.tags).slice(0, 2).map(([key, value]) => (
                    <Chip
                      key={key}
                      label={`${key}: ${value}`}
                      size="small"
                      variant="outlined"
                      sx={{ mr: 1, mb: 1 }}
                    />
                  ))}
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Updated: {new Date(model.last_updated).toLocaleDateString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
