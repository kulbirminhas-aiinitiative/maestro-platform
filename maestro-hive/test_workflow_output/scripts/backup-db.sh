#!/bin/bash
set -euo pipefail

# Database backup script
# Usage: ./backup-db.sh [environment]

ENVIRONMENT=${1:-dev}
NAMESPACE="user-management"
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
S3_BUCKET="user-management-${ENVIRONMENT}-backups"

GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

configure_kubectl() {
    if [ "$ENVIRONMENT" == "prod" ]; then
        aws eks update-kubeconfig --name prod-cluster --region us-east-1
    else
        aws eks update-kubeconfig --name dev-cluster --region us-east-1
    fi
}

perform_backup() {
    log_info "Starting database backup..."

    # Get database credentials
    DB_USER=$(kubectl get secret user-mgmt-secrets -n $NAMESPACE -o jsonpath='{.data.DATABASE_USER}' | base64 -d)
    DB_PASSWORD=$(kubectl get secret user-mgmt-secrets -n $NAMESPACE -o jsonpath='{.data.DATABASE_PASSWORD}' | base64 -d)
    DB_HOST="postgres-service"
    DB_NAME="usermanagement"

    # Create backup
    kubectl exec -n $NAMESPACE deployment/postgres -- \
        pg_dump -U $DB_USER -d $DB_NAME | gzip > backup_${TIMESTAMP}.sql.gz

    log_info "Backup created: backup_${TIMESTAMP}.sql.gz"
}

upload_to_s3() {
    log_info "Uploading backup to S3..."

    aws s3 cp backup_${TIMESTAMP}.sql.gz s3://${S3_BUCKET}/

    log_info "Backup uploaded to s3://${S3_BUCKET}/backup_${TIMESTAMP}.sql.gz"
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 30 days)..."

    aws s3 ls s3://${S3_BUCKET}/ | while read -r line; do
        createDate=$(echo $line | awk {'print $1" "$2'})
        createDate=$(date -d "$createDate" +%s)
        olderThan=$(date --date "30 days ago" +%s)

        if [[ $createDate -lt $olderThan ]]; then
            fileName=$(echo $line | awk {'print $4'})
            if [[ $fileName != "" ]]; then
                aws s3 rm s3://${S3_BUCKET}/$fileName
            fi
        fi
    done

    log_info "Cleanup completed"
}

main() {
    configure_kubectl
    perform_backup
    upload_to_s3
    cleanup_old_backups

    log_info "Database backup completed successfully!"
}

main
