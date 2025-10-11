#!/bin/bash
# Quick port status check for ML platform

echo "=== ML Platform Port Status ==="
echo ""

python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status \
  --project-path "/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml"

echo ""
echo "=== Service Access URLs (when minikube running) ==="
if command -v minikube &> /dev/null && minikube status &> /dev/null; then
    MINIKUBE_IP=$(minikube ip)
    echo "MLflow:       http://$MINIKUBE_IP:30500"
    echo "Feast:        http://$MINIKUBE_IP:30501"
    echo "Airflow:      http://$MINIKUBE_IP:30502"
    echo "Prometheus:   http://$MINIKUBE_IP:30503"
    echo "Grafana:      http://$MINIKUBE_IP:30504"
    echo "MinIO Console: http://$MINIKUBE_IP:30505"
else
    echo "Minikube not running. Start with:"
    echo "  ./scripts/setup-minikube-test.sh"
fi
