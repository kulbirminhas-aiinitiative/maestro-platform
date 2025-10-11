#!/bin/bash
# Database Restore Script for Maestro ML Platform
#
# Features:
# - Restore from local or S3 backup
# - Pre-restore validation
# - Database recreation
# - Post-restore verification
# - Rollback capability
#
# Usage:
#   ./restore_database.sh <backup_file>
#   ./restore_database.sh maestro_ml_backup_20251005_120000.sql.gz
#   ./restore_database.sh s3://maestro-ml-backups/backups/2025/10/maestro_ml_backup_20251005_120000.sql.gz

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/maestro_ml}"
RESTORE_TEMP_DIR="${RESTORE_TEMP_DIR:-/tmp/maestro_ml_restore}"

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-maestro_ml}"
DB_USER="${DB_USER:-postgres}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}ERROR: No backup file specified${NC}"
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Examples:"
    echo "  $0 maestro_ml_backup_20251005_120000.sql.gz"
    echo "  $0 s3://maestro-ml-backups/backups/2025/10/maestro_ml_backup_20251005_120000.sql.gz"
    exit 1
fi

BACKUP_INPUT="$1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/restore_${TIMESTAMP}.log"

# Create temp directory
mkdir -p "$RESTORE_TEMP_DIR"

# Logging
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "========================================"
echo "Maestro ML Database Restore"
echo "========================================"
echo "Started at: $(date)"
echo "Backup source: $BACKUP_INPUT"
echo ""

# Determine backup location and download if needed
if [[ "$BACKUP_INPUT" == s3://* ]]; then
    echo -e "${YELLOW}Downloading backup from S3...${NC}"

    if ! command -v aws &> /dev/null; then
        echo -e "${RED}ERROR: AWS CLI not installed${NC}"
        exit 1
    fi

    BACKUP_FILE=$(basename "$BACKUP_INPUT")
    BACKUP_PATH="${RESTORE_TEMP_DIR}/${BACKUP_FILE}"

    aws s3 cp "$BACKUP_INPUT" "$BACKUP_PATH"

    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Failed to download backup from S3${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Backup downloaded from S3${NC}"
else
    # Local file
    if [ -f "$BACKUP_INPUT" ]; then
        BACKUP_PATH="$BACKUP_INPUT"
    elif [ -f "${BACKUP_DIR}/${BACKUP_INPUT}" ]; then
        BACKUP_PATH="${BACKUP_DIR}/${BACKUP_INPUT}"
    else
        echo -e "${RED}ERROR: Backup file not found: $BACKUP_INPUT${NC}"
        exit 1
    fi
fi

echo "Backup file: $BACKUP_PATH"
echo ""

# Pre-restore validation
echo -e "${YELLOW}Running pre-restore validation...${NC}"

# Check if backup file exists and is readable
if [ ! -r "$BACKUP_PATH" ]; then
    echo -e "${RED}ERROR: Cannot read backup file${NC}"
    exit 1
fi

# Verify backup integrity
if gunzip -t "$BACKUP_PATH" 2>/dev/null; then
    echo -e "${GREEN}✓ Backup file integrity verified${NC}"
else
    echo -e "${RED}ERROR: Backup file is corrupted${NC}"
    exit 1
fi

# Check if PostgreSQL is accessible
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: PostgreSQL is not accessible${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pre-restore validation passed${NC}"
echo ""

# Confirm restore
echo -e "${YELLOW}WARNING: This will drop and recreate the database '$DB_NAME'${NC}"
echo -e "${YELLOW}All existing data will be lost!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo ""

# Create pre-restore backup (safety measure)
echo -e "${YELLOW}Creating safety backup of current database...${NC}"

SAFETY_BACKUP="${RESTORE_TEMP_DIR}/pre_restore_backup_${TIMESTAMP}.sql.gz"

PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=plain \
    --no-owner \
    --no-acl \
    2>/dev/null | gzip > "$SAFETY_BACKUP" || true

if [ -f "$SAFETY_BACKUP" ]; then
    echo -e "${GREEN}✓ Safety backup created: $SAFETY_BACKUP${NC}"
    echo "To rollback: ./restore_database.sh $SAFETY_BACKUP"
else
    echo -e "${YELLOW}WARNING: Could not create safety backup (database may not exist)${NC}"
fi

echo ""

# Terminate existing connections
echo -e "${YELLOW}Terminating existing database connections...${NC}"

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres << EOF
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
EOF

echo -e "${GREEN}✓ Connections terminated${NC}"
echo ""

# Drop and recreate database
echo -e "${YELLOW}Dropping and recreating database...${NC}"

PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres << EOF
DROP DATABASE IF EXISTS $DB_NAME;
CREATE DATABASE $DB_NAME;
EOF

echo -e "${GREEN}✓ Database recreated${NC}"
echo ""

# Restore backup
echo -e "${YELLOW}Restoring backup...${NC}"

gunzip -c "$BACKUP_PATH" | \
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --set ON_ERROR_STOP=on \
        --quiet

if [ ${PIPESTATUS[1]} -eq 0 ]; then
    echo -e "${GREEN}✓ Backup restored successfully${NC}"
else
    echo -e "${RED}ERROR: Restore failed${NC}"
    echo ""
    echo "To rollback to previous state:"
    if [ -f "$SAFETY_BACKUP" ]; then
        echo "  ./restore_database.sh $SAFETY_BACKUP"
    else
        echo "  (no safety backup available)"
    fi
    exit 1
fi

echo ""

# Post-restore verification
echo -e "${YELLOW}Running post-restore verification...${NC}"

# Count tables
TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)

echo "Tables restored: $TABLE_COUNT"

# Check key tables exist
EXPECTED_TABLES=("projects" "artifacts" "users" "tenants")
MISSING_TABLES=()

for table in "${EXPECTED_TABLES[@]}"; do
    EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '$table');" | xargs)

    if [ "$EXISTS" = "t" ]; then
        echo "  ✓ Table '$table' exists"
    else
        echo "  ✗ Table '$table' missing"
        MISSING_TABLES+=("$table")
    fi
done

if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
    echo -e "${RED}WARNING: Some expected tables are missing${NC}"
else
    echo -e "${GREEN}✓ All expected tables present${NC}"
fi

# Run database migrations (if applicable)
if [ -f "alembic.ini" ]; then
    echo ""
    echo -e "${YELLOW}Running database migrations...${NC}"
    alembic upgrade head
    echo -e "${GREEN}✓ Migrations completed${NC}"
fi

echo ""

# Cleanup
echo -e "${YELLOW}Cleaning up temporary files...${NC}"

if [[ "$BACKUP_INPUT" == s3://* ]]; then
    rm -f "$BACKUP_PATH"
    echo "Deleted temporary backup file"
fi

# Keep safety backup
echo "Safety backup retained: $SAFETY_BACKUP"

echo -e "${GREEN}✓ Cleanup completed${NC}"
echo ""

# Summary
echo "========================================"
echo -e "${GREEN}Restore Completed Successfully${NC}"
echo "========================================"
echo "Database: $DB_NAME"
echo "Tables restored: $TABLE_COUNT"
echo "Completed at: $(date)"
echo ""
echo "Safety backup location: $SAFETY_BACKUP"
echo "Log file: $LOG_FILE"
echo ""

exit 0
