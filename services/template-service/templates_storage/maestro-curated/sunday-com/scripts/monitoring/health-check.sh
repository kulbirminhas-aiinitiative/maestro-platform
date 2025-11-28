#!/bin/bash

# Sunday.com Health Check Script
# Comprehensive health monitoring for all services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
ENVIRONMENT="${ENVIRONMENT:-local}"
TIMEOUT=10
EXIT_CODE=0

# Service URLs based on environment
if [[ "$ENVIRONMENT" == "production" ]]; then
    API_URL="https://api.sunday.com"
    WEB_URL="https://sunday.com"
    GRAFANA_URL="https://grafana.sunday.com"
elif [[ "$ENVIRONMENT" == "staging" ]]; then
    API_URL="https://staging-api.sunday.com"
    WEB_URL="https://staging.sunday.com"
    GRAFANA_URL="https://staging-grafana.sunday.com"
else
    # Local development
    API_URL="http://localhost:3000"
    WEB_URL="http://localhost:5173"
    GRAFANA_URL="http://localhost:3001"
fi

# Check HTTP endpoint
check_http() {
    local url="$1"
    local service_name="$2"
    local expected_status="${3:-200}"

    log_info "Checking $service_name at $url"

    local status_code
    status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" || echo "000")

    if [[ "$status_code" == "$expected_status" ]]; then
        log_success "$service_name is healthy (HTTP $status_code)"
        return 0
    else
        log_error "$service_name is unhealthy (HTTP $status_code)"
        EXIT_CODE=1
        return 1
    fi
}

# Check API with JSON response
check_api() {
    local url="$1"
    local service_name="$2"

    log_info "Checking $service_name API at $url"

    local response
    response=$(curl -s --max-time "$TIMEOUT" "$url" || echo '{"error": "connection_failed"}')

    local status
    status=$(echo "$response" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")

    if [[ "$status" == "ok" ]] || [[ "$status" == "healthy" ]]; then
        log_success "$service_name API is healthy"
        return 0
    else
        log_error "$service_name API is unhealthy: $status"
        EXIT_CODE=1
        return 1
    fi
}

# Check database connectivity
check_database() {
    if [[ "$ENVIRONMENT" == "local" ]]; then
        log_info "Checking PostgreSQL database"
        if docker-compose exec -T postgres pg_isready -U sunday_dev >/dev/null 2>&1; then
            log_success "PostgreSQL is healthy"
        else
            log_error "PostgreSQL is unhealthy"
            EXIT_CODE=1
        fi
    else
        # For remote environments, check via API health endpoint
        check_api "${API_URL}/health/db" "Database"
    fi
}

# Check Redis
check_redis() {
    if [[ "$ENVIRONMENT" == "local" ]]; then
        log_info "Checking Redis"
        if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
            log_success "Redis is healthy"
        else
            log_error "Redis is unhealthy"
            EXIT_CODE=1
        fi
    else
        # For remote environments, check via API health endpoint
        check_api "${API_URL}/health/redis" "Redis"
    fi
}

# Check Elasticsearch
check_elasticsearch() {
    if [[ "$ENVIRONMENT" == "local" ]]; then
        log_info "Checking Elasticsearch"
        if curl -s --max-time "$TIMEOUT" "http://localhost:9200/_cluster/health" | jq -e '.status == "green" or .status == "yellow"' >/dev/null 2>&1; then
            log_success "Elasticsearch is healthy"
        else
            log_error "Elasticsearch is unhealthy"
            EXIT_CODE=1
        fi
    else
        # For remote environments, check via API health endpoint
        check_api "${API_URL}/health/search" "Elasticsearch"
    fi
}

# Check ClickHouse
check_clickhouse() {
    if [[ "$ENVIRONMENT" == "local" ]]; then
        log_info "Checking ClickHouse"
        if curl -s --max-time "$TIMEOUT" "http://localhost:8123/ping" | grep -q "Ok"; then
            log_success "ClickHouse is healthy"
        else
            log_error "ClickHouse is unhealthy"
            EXIT_CODE=1
        fi
    else
        # For remote environments, check via API health endpoint
        check_api "${API_URL}/health/analytics" "ClickHouse"
    fi
}

# Check Kubernetes pods (for remote environments)
check_kubernetes_pods() {
    if [[ "$ENVIRONMENT" == "local" ]]; then
        return 0
    fi

    log_info "Checking Kubernetes pods"

    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl not available, skipping pod checks"
        return 0
    fi

    local namespace="sunday-${ENVIRONMENT}"
    local unhealthy_pods=0

    # Check if pods are running
    local pods
    pods=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null || echo "")

    if [[ -z "$pods" ]]; then
        log_warning "No pods found in namespace $namespace"
        return 0
    fi

    while IFS= read -r line; do
        local pod_name status ready
        pod_name=$(echo "$line" | awk '{print $1}')
        status=$(echo "$line" | awk '{print $3}')
        ready=$(echo "$line" | awk '{print $2}')

        if [[ "$status" != "Running" ]] && [[ "$status" != "Completed" ]]; then
            log_error "Pod $pod_name is not running (status: $status)"
            ((unhealthy_pods++))
        elif [[ "$ready" =~ ^0/ ]]; then
            log_error "Pod $pod_name is not ready ($ready)"
            ((unhealthy_pods++))
        else
            log_success "Pod $pod_name is healthy"
        fi
    done <<< "$pods"

    if [[ $unhealthy_pods -gt 0 ]]; then
        EXIT_CODE=1
    fi
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space"

    local usage
    usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

    if [[ $usage -gt 90 ]]; then
        log_error "Disk usage is critical: ${usage}%"
        EXIT_CODE=1
    elif [[ $usage -gt 80 ]]; then
        log_warning "Disk usage is high: ${usage}%"
    else
        log_success "Disk usage is normal: ${usage}%"
    fi
}

# Check memory usage
check_memory() {
    log_info "Checking memory usage"

    if command -v free &> /dev/null; then
        local mem_usage
        mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')

        if [[ $mem_usage -gt 90 ]]; then
            log_error "Memory usage is critical: ${mem_usage}%"
            EXIT_CODE=1
        elif [[ $mem_usage -gt 80 ]]; then
            log_warning "Memory usage is high: ${mem_usage}%"
        else
            log_success "Memory usage is normal: ${mem_usage}%"
        fi
    else
        log_warning "Cannot check memory usage (free command not available)"
    fi
}

# Check SSL certificates (for remote environments)
check_ssl_certificates() {
    if [[ "$ENVIRONMENT" == "local" ]]; then
        return 0
    fi

    log_info "Checking SSL certificates"

    local domains=("$WEB_URL" "$API_URL")

    for url in "${domains[@]}"; do
        local domain
        domain=$(echo "$url" | sed 's|https://||' | sed 's|/.*||')

        local expiry_date
        expiry_date=$(echo | openssl s_client -servername "$domain" -connect "${domain}:443" 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)

        if [[ -n "$expiry_date" ]]; then
            local expiry_epoch
            expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s 2>/dev/null)

            local current_epoch
            current_epoch=$(date +%s)

            local days_until_expiry
            days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))

            if [[ $days_until_expiry -lt 7 ]]; then
                log_error "SSL certificate for $domain expires in $days_until_expiry days"
                EXIT_CODE=1
            elif [[ $days_until_expiry -lt 30 ]]; then
                log_warning "SSL certificate for $domain expires in $days_until_expiry days"
            else
                log_success "SSL certificate for $domain is valid ($days_until_expiry days remaining)"
            fi
        else
            log_error "Could not check SSL certificate for $domain"
            EXIT_CODE=1
        fi
    done
}

# Generate health report
generate_report() {
    echo
    log_info "=== Health Check Summary ==="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $(date)"
    echo "Overall Status: $(if [[ $EXIT_CODE -eq 0 ]]; then echo "HEALTHY"; else echo "UNHEALTHY"; fi)"
    echo
}

# Send alert if unhealthy
send_alert() {
    if [[ $EXIT_CODE -ne 0 ]] && [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        local message="🚨 Health check failed for $ENVIRONMENT environment"
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK_URL" >/dev/null 2>&1 || true
    fi
}

# Main health check function
main() {
    log_info "🏥 Starting health check for $ENVIRONMENT environment"
    echo

    # Core services
    check_http "$WEB_URL" "Frontend Application"
    check_api "${API_URL}/health" "Backend API"

    # Databases and caches
    check_database
    check_redis
    check_elasticsearch
    check_clickhouse

    # Infrastructure
    check_kubernetes_pods
    check_disk_space
    check_memory

    # Security
    check_ssl_certificates

    # Monitoring
    if [[ "$ENVIRONMENT" != "local" ]]; then
        check_http "$GRAFANA_URL" "Grafana Dashboard"
    fi

    generate_report
    send_alert

    exit $EXIT_CODE
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "OPTIONS:"
            echo "  -e, --environment ENV    Environment to check (local|staging|production)"
            echo "  -t, --timeout SECONDS    Timeout for HTTP requests (default: 10)"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if jq is available
if ! command -v jq &> /dev/null; then
    log_warning "jq not available, some checks may be limited"
fi

# Run main function
main