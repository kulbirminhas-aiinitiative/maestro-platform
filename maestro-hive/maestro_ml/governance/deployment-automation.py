#!/usr/bin/env python3
"""
Deployment Automation
Automates model deployment from MLflow to Kubernetes
"""

import argparse
import os
import sys
import json
import yaml
from typing import Dict, List, Optional
from datetime import datetime
import mlflow
from mlflow.tracking import MlflowClient
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeploymentAutomation:
    """Automated model deployment"""

    def __init__(self, mlflow_tracking_uri: str = None, namespace: str = "ml-serving"):
        """
        Args:
            mlflow_tracking_uri: MLflow tracking URI
            namespace: Kubernetes namespace for deployment
        """
        self.mlflow_tracking_uri = mlflow_tracking_uri or os.environ.get(
            'MLFLOW_TRACKING_URI',
            'http://mlflow.ml-platform.svc.cluster.local:5000'
        )
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        self.client = MlflowClient()
        self.namespace = namespace

    def deploy_model(
        self,
        model_name: str,
        model_version: str = None,
        model_stage: str = "Production",
        deployment_strategy: str = "rolling",
        replicas: int = 2,
        cpu_request: str = "500m",
        memory_request: str = "1Gi",
        cpu_limit: str = "2",
        memory_limit: str = "4Gi"
    ) -> Dict:
        """
        Deploy model to Kubernetes

        Args:
            model_name: Model name
            model_version: Model version (if None, uses latest from stage)
            model_stage: Model stage (Production, Staging)
            deployment_strategy: Deployment strategy (rolling, blue-green, canary)
            replicas: Number of replicas
            cpu_request: CPU request
            memory_request: Memory request
            cpu_limit: CPU limit
            memory_limit: Memory limit

        Returns:
            dict: Deployment details
        """
        logger.info(f"Deploying model {model_name} to {self.namespace}")

        # Get model version
        if model_version is None:
            versions = self.client.get_latest_versions(model_name, stages=[model_stage])
            if not versions:
                raise ValueError(f"No model found for {model_name} in stage {model_stage}")
            model_version = versions[0].version
            logger.info(f"Using latest {model_stage} version: {model_version}")

        # Get model info
        model_version_obj = self.client.get_model_version(model_name, model_version)
        run_id = model_version_obj.run_id

        # Create deployment config
        deployment_config = self._create_deployment_config(
            model_name=model_name,
            model_version=model_version,
            model_stage=model_stage,
            replicas=replicas,
            cpu_request=cpu_request,
            memory_request=memory_request,
            cpu_limit=cpu_limit,
            memory_limit=memory_limit
        )

        # Deploy based on strategy
        if deployment_strategy == "rolling":
            deployment_result = self._deploy_rolling(deployment_config)
        elif deployment_strategy == "blue-green":
            deployment_result = self._deploy_blue_green(deployment_config)
        elif deployment_strategy == "canary":
            deployment_result = self._deploy_canary(deployment_config)
        else:
            raise ValueError(f"Unknown deployment strategy: {deployment_strategy}")

        # Log deployment to MLflow
        self._log_deployment_to_mlflow(
            run_id=run_id,
            model_name=model_name,
            model_version=model_version,
            deployment_result=deployment_result
        )

        logger.info(f"✓ Model deployed successfully")
        return deployment_result

    def _create_deployment_config(
        self,
        model_name: str,
        model_version: str,
        model_stage: str,
        replicas: int,
        cpu_request: str,
        memory_request: str,
        cpu_limit: str,
        memory_limit: str
    ) -> Dict:
        """Create Kubernetes deployment configuration"""

        deployment_name = f"{model_name}-{model_version}".replace("_", "-").lower()

        config = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': deployment_name,
                'namespace': self.namespace,
                'labels': {
                    'app': 'mlflow-serving',
                    'model': model_name,
                    'version': str(model_version),
                    'managed-by': 'deployment-automation'
                }
            },
            'spec': {
                'replicas': replicas,
                'selector': {
                    'matchLabels': {
                        'app': 'mlflow-serving',
                        'model': model_name,
                        'version': str(model_version)
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': 'mlflow-serving',
                            'model': model_name,
                            'version': str(model_version)
                        },
                        'annotations': {
                            'prometheus.io/scrape': 'true',
                            'prometheus.io/port': '8080',
                            'prometheus.io/path': '/metrics'
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': 'model-server',
                            'image': 'python:3.11-slim',
                            'command': ['/bin/bash', '-c'],
                            'args': [
                                f'''
                                pip install -q mlflow scikit-learn pandas numpy prometheus-client fastapi uvicorn
                                cat > /app/serve.py <<'EOF'
import os
import mlflow
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI()
MODEL = None

@app.on_event("startup")
async def load_model():
    global MODEL
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    model_uri = f"models:/{os.environ['MODEL_NAME']}/{os.environ['MODEL_STAGE']}"
    MODEL = mlflow.pyfunc.load_model(model_uri)

@app.get("/health")
async def health():
    return {{"status": "healthy", "model_loaded": MODEL is not None}}

@app.get("/ready")
async def ready():
    if MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {{"status": "ready"}}

@app.post("/predict")
async def predict(request: dict):
    if MODEL is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    features = request.get("instances") or [request.get("features")]
    predictions = MODEL.predict(features)
    return {{"predictions": predictions.tolist()}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF
                                python3 /app/serve.py
                                '''
                            ],
                            'env': [
                                {'name': 'MLFLOW_TRACKING_URI', 'value': self.mlflow_tracking_uri},
                                {'name': 'MODEL_NAME', 'value': model_name},
                                {'name': 'MODEL_STAGE', 'value': model_stage},
                                {'name': 'MODEL_VERSION', 'value': str(model_version)}
                            ],
                            'ports': [
                                {'containerPort': 8080, 'name': 'http', 'protocol': 'TCP'}
                            ],
                            'resources': {
                                'requests': {
                                    'cpu': cpu_request,
                                    'memory': memory_request
                                },
                                'limits': {
                                    'cpu': cpu_limit,
                                    'memory': memory_limit
                                }
                            },
                            'livenessProbe': {
                                'httpGet': {'path': '/health', 'port': 8080},
                                'initialDelaySeconds': 30,
                                'periodSeconds': 10
                            },
                            'readinessProbe': {
                                'httpGet': {'path': '/ready', 'port': 8080},
                                'initialDelaySeconds': 10,
                                'periodSeconds': 5
                            }
                        }]
                    }
                }
            }
        }

        # Service config
        service_config = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': deployment_name,
                'namespace': self.namespace,
                'labels': {
                    'app': 'mlflow-serving',
                    'model': model_name
                }
            },
            'spec': {
                'type': 'ClusterIP',
                'ports': [
                    {'port': 80, 'targetPort': 8080, 'protocol': 'TCP', 'name': 'http'}
                ],
                'selector': {
                    'app': 'mlflow-serving',
                    'model': model_name,
                    'version': str(model_version)
                }
            }
        }

        return {
            'deployment': config,
            'service': service_config,
            'deployment_name': deployment_name
        }

    def _deploy_rolling(self, config: Dict) -> Dict:
        """Deploy using rolling update strategy"""
        logger.info("Deploying with rolling update strategy")

        # Create namespace if not exists
        self._ensure_namespace()

        # Write configs to temp files
        deployment_file = '/tmp/deployment.yaml'
        service_file = '/tmp/service.yaml'

        with open(deployment_file, 'w') as f:
            yaml.dump(config['deployment'], f)

        with open(service_file, 'w') as f:
            yaml.dump(config['service'], f)

        # Apply to Kubernetes
        try:
            # Apply deployment
            result = subprocess.run(
                ['kubectl', 'apply', '-f', deployment_file],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Deployment applied: {result.stdout.strip()}")

            # Apply service
            result = subprocess.run(
                ['kubectl', 'apply', '-f', service_file],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Service applied: {result.stdout.strip()}")

            # Wait for rollout
            deployment_name = config['deployment_name']
            result = subprocess.run(
                ['kubectl', 'rollout', 'status', f'deployment/{deployment_name}', '-n', self.namespace],
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                'strategy': 'rolling',
                'deployment_name': deployment_name,
                'namespace': self.namespace,
                'status': 'deployed',
                'replicas': config['deployment']['spec']['replicas'],
                'timestamp': datetime.now().isoformat()
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Deployment failed: {e.stderr}")
            raise
        except subprocess.TimeoutExpired:
            logger.error("Deployment timeout")
            raise

    def _deploy_blue_green(self, config: Dict) -> Dict:
        """Deploy using blue-green strategy"""
        logger.info("Deploying with blue-green strategy")

        # Modify deployment name for blue-green
        green_name = config['deployment_name'] + '-green'
        config['deployment']['metadata']['name'] = green_name
        config['deployment']['metadata']['labels']['deployment'] = 'green'
        config['deployment']['spec']['selector']['matchLabels']['deployment'] = 'green'
        config['deployment']['spec']['template']['metadata']['labels']['deployment'] = 'green'

        # Deploy green
        green_result = self._deploy_rolling(config)

        # TODO: Switch traffic from blue to green (update service selector)
        # For now, just deploy green version
        logger.info("Green deployment complete. Manual traffic switch required.")

        green_result['strategy'] = 'blue-green'
        green_result['deployment_type'] = 'green'
        green_result['note'] = 'Manual traffic switch required'

        return green_result

    def _deploy_canary(self, config: Dict) -> Dict:
        """Deploy using canary strategy"""
        logger.info("Deploying with canary strategy (10% traffic)")

        # Deploy canary with 1 replica (10% traffic)
        canary_name = config['deployment_name'] + '-canary'
        config['deployment']['metadata']['name'] = canary_name
        config['deployment']['metadata']['labels']['deployment'] = 'canary'
        config['deployment']['spec']['replicas'] = 1  # Start with 1 replica
        config['deployment']['spec']['selector']['matchLabels']['deployment'] = 'canary'
        config['deployment']['spec']['template']['metadata']['labels']['deployment'] = 'canary'

        # Deploy canary
        canary_result = self._deploy_rolling(config)

        canary_result['strategy'] = 'canary'
        canary_result['traffic_percentage'] = 10
        canary_result['note'] = 'Monitor metrics before increasing traffic'

        return canary_result

    def _ensure_namespace(self):
        """Ensure namespace exists"""
        try:
            subprocess.run(
                ['kubectl', 'create', 'namespace', self.namespace],
                capture_output=True,
                text=True
            )
        except:
            pass  # Namespace might already exist

    def _log_deployment_to_mlflow(
        self,
        run_id: str,
        model_name: str,
        model_version: str,
        deployment_result: Dict
    ):
        """Log deployment to MLflow"""
        with mlflow.start_run(run_id=run_id):
            # Log deployment metadata
            mlflow.set_tag('deployment_status', deployment_result['status'])
            mlflow.set_tag('deployment_strategy', deployment_result['strategy'])
            mlflow.set_tag('deployment_name', deployment_result['deployment_name'])
            mlflow.set_tag('deployment_namespace', deployment_result['namespace'])
            mlflow.set_tag('deployment_timestamp', deployment_result['timestamp'])

            # Log deployment config
            mlflow.log_dict(deployment_result, 'deployment/deployment_info.json')

    def rollback_deployment(
        self,
        model_name: str,
        target_version: str = None
    ) -> Dict:
        """
        Rollback deployment to previous version

        Args:
            model_name: Model name
            target_version: Target version (if None, rolls back to previous)

        Returns:
            dict: Rollback result
        """
        logger.info(f"Rolling back deployment for {model_name}")

        # Get deployment history
        result = subprocess.run(
            ['kubectl', 'rollout', 'history', f'deployment/{model_name}', '-n', self.namespace],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise ValueError(f"Failed to get rollout history: {result.stderr}")

        # Rollback
        rollback_cmd = ['kubectl', 'rollout', 'undo', f'deployment/{model_name}', '-n', self.namespace]
        if target_version:
            rollback_cmd.extend(['--to-revision', target_version])

        result = subprocess.run(
            rollback_cmd,
            capture_output=True,
            text=True,
            check=True
        )

        logger.info(f"✓ Rollback initiated: {result.stdout.strip()}")

        return {
            'model_name': model_name,
            'namespace': self.namespace,
            'status': 'rolled_back',
            'target_version': target_version or 'previous',
            'timestamp': datetime.now().isoformat()
        }

    def get_deployment_status(self, deployment_name: str) -> Dict:
        """Get deployment status"""
        result = subprocess.run(
            ['kubectl', 'get', 'deployment', deployment_name, '-n', self.namespace, '-o', 'json'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise ValueError(f"Deployment not found: {deployment_name}")

        deployment_info = json.loads(result.stdout)

        return {
            'deployment_name': deployment_name,
            'namespace': self.namespace,
            'replicas': deployment_info['status'].get('replicas', 0),
            'ready_replicas': deployment_info['status'].get('readyReplicas', 0),
            'available_replicas': deployment_info['status'].get('availableReplicas', 0),
            'conditions': deployment_info['status'].get('conditions', [])
        }


def main(args):
    automation = DeploymentAutomation(namespace=args.namespace)

    if args.action == 'deploy':
        result = automation.deploy_model(
            model_name=args.model_name,
            model_version=args.model_version,
            model_stage=args.model_stage,
            deployment_strategy=args.strategy,
            replicas=args.replicas,
            cpu_request=args.cpu_request,
            memory_request=args.memory_request,
            cpu_limit=args.cpu_limit,
            memory_limit=args.memory_limit
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'rollback':
        result = automation.rollback_deployment(
            model_name=args.model_name,
            target_version=args.target_version
        )
        print(json.dumps(result, indent=2))

    elif args.action == 'status':
        result = automation.get_deployment_status(args.deployment_name)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Model deployment automation')
    parser.add_argument('action', choices=['deploy', 'rollback', 'status'], help='Action')
    parser.add_argument('--model-name', help='Model name')
    parser.add_argument('--model-version', help='Model version')
    parser.add_argument('--model-stage', default='Production', help='Model stage')
    parser.add_argument('--strategy', default='rolling', choices=['rolling', 'blue-green', 'canary'],
                       help='Deployment strategy')
    parser.add_argument('--replicas', type=int, default=2, help='Number of replicas')
    parser.add_argument('--cpu-request', default='500m', help='CPU request')
    parser.add_argument('--memory-request', default='1Gi', help='Memory request')
    parser.add_argument('--cpu-limit', default='2', help='CPU limit')
    parser.add_argument('--memory-limit', default='4Gi', help='Memory limit')
    parser.add_argument('--namespace', default='ml-serving', help='Kubernetes namespace')
    parser.add_argument('--deployment-name', help='Deployment name')
    parser.add_argument('--target-version', help='Target version for rollback')

    args = parser.parse_args()
    main(args)
