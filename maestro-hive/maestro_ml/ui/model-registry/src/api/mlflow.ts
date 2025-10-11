import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_MLFLOW_URL || '/api';

const mlflowClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Model {
  name: string;
  latest_version: string;
  description?: string;
  tags?: Record<string, string>;
  last_updated: string;
}

export interface Experiment {
  experiment_id: string;
  name: string;
  artifact_location: string;
  lifecycle_stage: string;
  last_update_time: string;
}

export const mlflowApi = {
  async getModels(): Promise<Model[]> {
    try {
      const response = await mlflowClient.get('/registered-models/search');

      // Transform MLflow response to our Model interface
      const models = response.data.registered_models || [];
      return models.map((model: any) => ({
        name: model.name,
        latest_version: model.latest_versions?.[0]?.version || '0',
        description: model.description,
        tags: model.tags,
        last_updated: model.last_updated_timestamp
          ? new Date(parseInt(model.last_updated_timestamp)).toISOString()
          : new Date().toISOString(),
      }));
    } catch (error) {
      console.error('Error fetching models:', error);
      // Return mock data for development
      return getMockModels();
    }
  },

  async getExperiments(): Promise<Experiment[]> {
    try {
      const response = await mlflowClient.get('/experiments/search');
      return response.data.experiments || [];
    } catch (error) {
      console.error('Error fetching experiments:', error);
      return [];
    }
  },
};

// Mock data for development/testing
function getMockModels(): Model[] {
  return [
    {
      name: 'customer-churn-predictor',
      latest_version: '3',
      description: 'Predicts customer churn probability',
      tags: { framework: 'sklearn', accuracy: '0.92' },
      last_updated: new Date().toISOString(),
    },
    {
      name: 'fraud-detection-model',
      latest_version: '5',
      description: 'Real-time fraud detection for transactions',
      tags: { framework: 'tensorflow', precision: '0.95' },
      last_updated: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      name: 'recommendation-engine',
      latest_version: '2',
      description: 'Collaborative filtering recommendation system',
      tags: { framework: 'pytorch', recall: '0.88' },
      last_updated: new Date(Date.now() - 172800000).toISOString(),
    },
    {
      name: 'sentiment-analyzer',
      latest_version: '4',
      description: 'Analyzes customer sentiment from reviews',
      tags: { framework: 'transformers', f1: '0.91' },
      last_updated: new Date(Date.now() - 259200000).toISOString(),
    },
    {
      name: 'price-optimization',
      latest_version: '1',
      description: 'Dynamic pricing optimization model',
      tags: { framework: 'xgboost', rmse: '12.5' },
      last_updated: new Date(Date.now() - 345600000).toISOString(),
    },
  ];
}

export default mlflowApi;
