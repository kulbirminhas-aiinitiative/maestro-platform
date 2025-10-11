#!/bin/bash
# Automated Database Backup Script for Maestro ML Platform
#
# Features:
# - Full PostgreSQL database backup
# - Compressed backup files
# - Retention policy (keep last 30 days)
# - S3 upload for offsite storage
# - Email notifications
# - Backup verification

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/maestro_ml}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-maestro-ml-backups}"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-ops@maestro-ml.com}"

# Database configuration (from environment or defaults)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-maestro_ml}"
DB_USER="${DB_USER:-postgres}"

# Timestamp for backup file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="maestro_ml_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "========================================"
echo "Maestro ML Database Backup"
echo "========================================"
echo "Started at: $(date)"
echo "Backup file: $BACKUP_FILE"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Pre-backup checks
echo -e "${YELLOW}Running pre-backup checks...${NC}"

# Check if PostgreSQL is accessible
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: PostgreSQL is not accessible${NC}"
    exit 1
fi

# Check available disk space (require at least 10GB)
AVAILABLE_SPACE=$(df -BG "$BACKUP_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 10 ]; then
    echo -e "${RED}ERROR: Insufficient disk space. Available: ${AVAILABLE_SPACE}GB, Required: 10GB${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pre-backup checks passed${NC}"
echo ""

# Perform backup
echo -e "${YELLOW}Creating database backup...${NC}"

# Use pg_dump with compression
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    --verbose \
    2>&1 | gzip > "$BACKUP_PATH"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo -e "${GREEN}✓ Database backup created successfully${NC}"
else
    echo -e "${RED}ERROR: Database backup failed${NC}"
    exit 1
fi

# Get backup file size
BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo "Backup size: $BACKUP_SIZE"
echo ""

# Verify backup integrity
echo -e "${YELLOW}Verifying backup integrity...${NC}"

if gunzip -t "$BACKUP_PATH" 2>/dev/null; then
    echo -e "${GREEN}✓ Backup file integrity verified${NC}"
else
    echo -e "${RED}ERROR: Backup file is corrupted${NC}"
    exit 1
fi
echo ""

# Upload to S3 (if configured)
if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
    echo -e "${YELLOW}Uploading backup to S3...${NC}"

    aws s3 cp "$BACKUP_PATH" "s3://${S3_BUCKET}/backups/$(date +%Y)/$(date +%m)/${BACKUP_FILE}" \
        --storage-class STANDARD_IA \
        --metadata "timestamp=${TIMESTAMP},database=${DB_NAME}"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Backup uploaded to S3${NC}"
    else
        echo -e "${RED}WARNING: Failed to upload backup to S3${NC}"
    fi
    echo ""
fi

# Clean up old backups
echo -e "${YELLOW}Cleaning up old backups (retention: ${RETENTION_DAYS} days)...${NC}"

# Local cleanup
find "$BACKUP_DIR" -name "maestro_ml_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
DELETED_COUNT=$(find "$BACKUP_DIR" -name "maestro_ml_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS 2>/dev/null | wc -l)
echo "Deleted $DELETED_COUNT old local backups"

# S3 cleanup (if configured)
if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
    CUTOFF_DATE=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)
    aws s3 ls "s3://${S3_BUCKET}/backups/" --recursive | \
        awk '{print $4}' | \
        while read file; do
            FILE_DATE=$(echo "$file" | grep -oP '\d{8}' | head -1)
            FILE_DATE_FORMATTED=$(echo "$FILE_DATE" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3/')
            if [[ "$FILE_DATE_FORMATTED" < "$CUTOFF_DATE" ]]; then
                aws s3 rm "s3://${S3_BUCKET}/${file}"
            fi
        done
fi

echo -e "${GREEN}✓ Old backups cleaned up${NC}"
echo ""

# Backup metadata
METADATA_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.json"
cat > "$METADATA_FILE" << EOF
{
  "timestamp": "$TIMESTAMP",
  "backup_file": "$BACKUP_FILE",
  "backup_path": "$BACKUP_PATH",
  "backup_size": "$BACKUP_SIZE",
  "database": "$DB_NAME",
  "db_host": "$DB_HOST",
  "db_port": "$DB_PORT",
  "s3_bucket": "$S3_BUCKET",
  "retention_days": $RETENTION_DAYS,
  "completed_at": "$(date -Iseconds)",
  "status": "success"
}
EOF

echo "Metadata saved to: $METADATA_FILE"
echo ""

# Send notification email (if configured)
if [ -n "$NOTIFICATION_EMAIL" ] && command -v mail &> /dev/null; then
    echo -e "${YELLOW}Sending notification email...${NC}"

    mail -s "Maestro ML Backup Completed - $TIMESTAMP" "$NOTIFICATION_EMAIL" << EOF
Database backup completed successfully.

Backup Details:
- File: $BACKUP_FILE
- Size: $BACKUP_SIZE
- Database: $DB_NAME
- Timestamp: $TIMESTAMP
- S3 Location: s3://${S3_BUCKET}/backups/$(date +%Y)/$(date +%m)/${BACKUP_FILE}

Log file: $LOG_FILE

This is an automated message from Maestro ML Backup System.
EOF

    echo -e "${GREEN}✓ Notification email sent${NC}"
fi

# Summary
echo ""
echo "========================================"
echo -e "${GREEN}Backup Completed Successfully${NC}"
echo "========================================"
echo "Backup file: $BACKUP_PATH"
echo "Backup size: $BACKUP_SIZE"
echo "Completed at: $(date)"
echo ""
echo "To restore this backup, run:"
echo "  ./restore_database.sh $BACKUP_FILE"
echo ""

exit 0
