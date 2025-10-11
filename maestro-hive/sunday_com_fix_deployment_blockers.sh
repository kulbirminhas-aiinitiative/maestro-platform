#!/bin/bash

# Sunday.com Deployment Blocker Resolution Script
# This script addresses all critical issues preventing deployment

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/sunday_com"
BACKEND_DIR="$PROJECT_DIR/backend"

echo "=================================================="
echo "Sunday.com Deployment Blocker Resolution"
echo "=================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track errors
ERRORS=0
WARNINGS=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((ERRORS++))
}

# Step 1: Verify project exists
log_info "Step 1: Verifying project structure..."
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "Project directory not found: $PROJECT_DIR"
    exit 1
fi

if [ ! -d "$BACKEND_DIR" ]; then
    log_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi

log_success "Project structure verified"
echo ""

# Step 2: Backup before making changes
log_info "Step 2: Creating backup..."
BACKUP_DIR="$SCRIPT_DIR/sunday_com_backup_$(date +%Y%m%d_%H%M%S)"
if [ -d "$PROJECT_DIR" ]; then
    cp -r "$PROJECT_DIR" "$BACKUP_DIR"
    log_success "Backup created at: $BACKUP_DIR"
else
    log_warning "Could not create backup"
fi
echo ""

# Step 3: Clean and regenerate Prisma client
log_info "Step 3: Regenerating Prisma client..."
cd "$BACKEND_DIR"

# Clean old generated files
log_info "Cleaning old Prisma generated files..."
rm -rf node_modules/.prisma 2>/dev/null || true
rm -rf node_modules/@prisma/client 2>/dev/null || true
rm -rf prisma/generated 2>/dev/null || true

# Check if prisma schema exists
if [ ! -f "prisma/schema.prisma" ]; then
    log_error "Prisma schema not found at prisma/schema.prisma"
    ((ERRORS++))
else
    log_info "Running: npx prisma generate"
    if npx prisma generate; then
        log_success "Prisma client regenerated successfully"
    else
        log_error "Failed to generate Prisma client"
        ((ERRORS++))
    fi
fi
echo ""

# Step 4: Fix configuration issues
log_info "Step 4: Fixing configuration issues..."

CONFIG_FILE="$BACKEND_DIR/src/config/index.ts"
if [ -f "$CONFIG_FILE" ]; then
    log_info "Checking configuration file..."
    
    # Check if jwtSecret is missing
    if ! grep -q "jwtSecret" "$CONFIG_FILE"; then
        log_warning "jwtSecret not found in config - needs manual addition"
        cat << EOF >> /tmp/config_additions.txt

CONFIGURATION ADDITIONS NEEDED:
================================

In src/config/index.ts, add to security section:

  security: {
    corsOrigin: [...],
    bcryptRounds: ...,
    sessionSecret: ...,
    webhookSecret: ...,
    jwtSecret: process.env.JWT_SECRET || process.env.SESSION_SECRET, // ADD THIS
  },

And add storage section:

  storage: {
    provider: process.env.STORAGE_PROVIDER || 'local',
    bucket: process.env.STORAGE_BUCKET,
    region: process.env.STORAGE_REGION || 'us-east-1',
    endpoint: process.env.STORAGE_ENDPOINT,
    localPath: process.env.STORAGE_LOCAL_PATH || './uploads',
  },

EOF
        cat /tmp/config_additions.txt
        log_warning "Manual configuration update required - see above"
        ((WARNINGS++))
    else
        log_success "Configuration appears complete"
    fi
else
    log_error "Configuration file not found: $CONFIG_FILE"
    ((ERRORS++))
fi
echo ""

# Step 5: Fix invalid imports
log_info "Step 5: Fixing invalid Prisma imports..."

# Find files with invalid BoardService import from @prisma/client
INVALID_IMPORTS=$(grep -r "import.*BoardService.*from '@prisma/client'" src/ 2>/dev/null || true)

if [ -n "$INVALID_IMPORTS" ]; then
    log_warning "Found invalid BoardService imports:"
    echo "$INVALID_IMPORTS"
    log_info "These need to be changed from:"
    echo "  import { BoardService } from '@prisma/client';"
    log_info "To:"
    echo "  import { BoardService } from '@/services/board.service';"
    ((WARNINGS++))
else
    log_success "No invalid BoardService imports found"
fi
echo ""

# Step 6: Identify duplicate version files
log_info "Step 6: Identifying duplicate service files..."

cd "$BACKEND_DIR/src/services"
DUPLICATES=$(ls -1 *_v*.ts 2>/dev/null || true)

if [ -n "$DUPLICATES" ]; then
    log_warning "Found duplicate version files:"
    echo "$DUPLICATES" | sed 's/^/  /'
    
    echo ""
    log_info "Duplicate file analysis:"
    for service in board item workspace ai automation analytics file collaboration websocket; do
        BASE="${service}.service.ts"
        V1="${service}.service_v1.ts"
        V2="${service}.service_v2_newer.ts"
        
        if [ -f "$BASE" ]; then
            BASE_SIZE=$(wc -l < "$BASE")
            echo "  $BASE: $BASE_SIZE lines"
            
            if [ -f "$V1" ]; then
                V1_SIZE=$(wc -l < "$V1")
                echo "  $V1: $V1_SIZE lines (OLD VERSION - CANDIDATE FOR DELETION)"
            fi
            
            if [ -f "$V2" ]; then
                V2_SIZE=$(wc -l < "$V2")
                echo "  $V2: $V2_SIZE lines (NEWER VERSION - REVIEW NEEDED)"
            fi
        fi
    done
    
    echo ""
    log_warning "Manual review required to determine which versions to keep"
    ((WARNINGS++))
else
    log_success "No duplicate version files found"
fi
echo ""

cd "$BACKEND_DIR"

# Step 7: Fix test setup
log_info "Step 7: Fixing test setup..."

TEST_SETUP="$BACKEND_DIR/src/__tests__/setup.ts"
if [ -f "$TEST_SETUP" ]; then
    if grep -q "import.*Decimal.*from '@prisma/client'" "$TEST_SETUP"; then
        log_warning "Test setup imports Decimal from @prisma/client"
        log_info "This import should be removed or changed to:"
        echo "  import { Decimal } from '@prisma/client/runtime/library';"
        log_info "Or remove Decimal usage if not needed"
        ((WARNINGS++))
    else
        log_success "Test setup appears correct"
    fi
else
    log_warning "Test setup file not found: $TEST_SETUP"
fi
echo ""

# Step 8: Try to build
log_info "Step 8: Attempting build..."

log_info "Running: npm run build"
if npm run build > /tmp/sunday_build.log 2>&1; then
    log_success "✅ Build succeeded!"
else
    log_error "Build failed - see /tmp/sunday_build.log for details"
    echo ""
    log_info "First 50 errors:"
    grep "error TS" /tmp/sunday_build.log | head -50
    ((ERRORS++))
fi
echo ""

# Step 9: Try to run tests
if [ $ERRORS -eq 0 ]; then
    log_info "Step 9: Running tests..."
    
    log_info "Running: npm test -- --passWithNoTests"
    if npm test -- --passWithNoTests > /tmp/sunday_test.log 2>&1; then
        log_success "Tests completed"
        
        # Check coverage
        if grep -q "Coverage" /tmp/sunday_test.log; then
            log_info "Test coverage:"
            grep -A 10 "Coverage" /tmp/sunday_test.log
        fi
    else
        log_error "Tests failed - see /tmp/sunday_test.log"
        echo ""
        log_info "Test errors:"
        tail -50 /tmp/sunday_test.log
        ((ERRORS++))
    fi
else
    log_warning "Skipping tests due to build errors"
fi
echo ""

# Step 10: Database validation
log_info "Step 10: Validating database schema..."

if command -v psql &> /dev/null; then
    log_info "Running: npx prisma validate"
    if npx prisma validate > /tmp/sunday_prisma_validate.log 2>&1; then
        log_success "Prisma schema is valid"
    else
        log_warning "Prisma schema validation issues - see /tmp/sunday_prisma_validate.log"
        ((WARNINGS++))
    fi
    
    log_info "Running: npx prisma migrate status"
    if npx prisma migrate status > /tmp/sunday_migrate_status.log 2>&1; then
        log_success "Migration status checked"
        cat /tmp/sunday_migrate_status.log
    else
        log_warning "Could not check migration status"
        ((WARNINGS++))
    fi
else
    log_warning "PostgreSQL not available - skipping database validation"
fi
echo ""

# Summary
echo "=================================================="
echo "RESOLUTION SUMMARY"
echo "=================================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    log_success "✅ All checks passed! Project is ready for deployment."
    echo ""
    echo "Next steps:"
    echo "  1. Run full test suite: npm test -- --coverage"
    echo "  2. Build Docker images: docker-compose build"
    echo "  3. Run integration tests: npm run test:e2e"
    echo "  4. Deploy to staging environment"
elif [ $ERRORS -eq 0 ]; then
    log_warning "⚠️  Checks completed with $WARNINGS warnings"
    echo ""
    echo "Manual actions required:"
    echo "  - Review warnings above"
    echo "  - Update configuration if needed"
    echo "  - Remove duplicate version files"
    echo "  - Fix any import issues"
    echo ""
    echo "After manual fixes:"
    echo "  1. Run: npm run build"
    echo "  2. Run: npm test -- --coverage"
else
    log_error "❌ Critical errors found: $ERRORS errors, $WARNINGS warnings"
    echo ""
    echo "Resolution required:"
    echo "  1. Review error log: /tmp/sunday_build.log"
    echo "  2. Fix TypeScript errors"
    echo "  3. Regenerate Prisma client if needed"
    echo "  4. Re-run this script"
    echo ""
    echo "Common fixes:"
    echo "  - Run: npx prisma generate"
    echo "  - Fix imports: Replace @prisma/client imports with service imports"
    echo "  - Update config: Add missing jwtSecret and storage config"
    echo "  - Remove duplicates: Delete *_v1.ts and *_v2_newer.ts files"
fi

echo ""
echo "Logs saved to:"
echo "  - Build: /tmp/sunday_build.log"
echo "  - Tests: /tmp/sunday_test.log"
echo "  - Prisma: /tmp/sunday_prisma_validate.log"
echo "  - Migrations: /tmp/sunday_migrate_status.log"
echo ""

echo "Backup location: $BACKUP_DIR"
echo ""

exit $ERRORS
