#!/bin/bash
# Maestro Health Monitor Script
# Monitors all services and sends alerts on failure
# Can be run via cron: */5 * * * * /path/to/health-monitor.sh

set -e

# Configuration
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:4300}"
BACKEND_URL="${BACKEND_URL:-http://localhost:3100}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"

# JIRA Configuration
JIRA_BASE_URL="${JIRA_BASE_URL:-https://fifth9.atlassian.net}"
JIRA_EMAIL="${JIRA_EMAIL:-}"
JIRA_API_TOKEN="${JIRA_API_TOKEN:-}"
JIRA_PROJECT_KEY="${JIRA_PROJECT_KEY:-MD}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="/var/log/maestro/health-monitor.log"
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || LOG_FILE="/tmp/maestro-health-monitor.log"

# Function to log messages
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    case "$level" in
        ERROR) echo -e "${RED}[$level]${NC} $message" ;;
        WARN)  echo -e "${YELLOW}[$level]${NC} $message" ;;
        INFO)  echo -e "${GREEN}[$level]${NC} $message" ;;
        *)     echo "[$level] $message" ;;
    esac
}

# Function to send Slack alert
send_slack_alert() {
    local message="$1"
    local color="$2"  # good, warning, danger

    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"Maestro Health Alert\",
                    \"text\": \"$message\",
                    \"footer\": \"Maestro Health Monitor\",
                    \"ts\": $(date +%s)
                }]
            }" "$SLACK_WEBHOOK_URL" > /dev/null
        log "INFO" "Slack alert sent"
    fi
}

# Function to send email alert
send_email_alert() {
    local subject="$1"
    local message="$2"

    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || true
        log "INFO" "Email alert sent to $ALERT_EMAIL"
    fi
}

# Function to create JIRA issue for alert
create_jira_issue() {
    local summary="$1"
    local description="$2"

    if [ -n "$JIRA_EMAIL" ] && [ -n "$JIRA_API_TOKEN" ]; then
        local response
        response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
            -d "{
                \"fields\": {
                    \"project\": {\"key\": \"$JIRA_PROJECT_KEY\"},
                    \"summary\": \"[ALERT] $summary\",
                    \"description\": {
                        \"type\": \"doc\",
                        \"version\": 1,
                        \"content\": [{
                            \"type\": \"paragraph\",
                            \"content\": [{
                                \"type\": \"text\",
                                \"text\": \"$description\"
                            }]
                        }]
                    },
                    \"issuetype\": {\"name\": \"Bug\"},
                    \"priority\": {\"name\": \"High\"},
                    \"labels\": [\"auto-alert\", \"health-check\", \"infrastructure\"]
                }
            }" "$JIRA_BASE_URL/rest/api/3/issue" 2>/dev/null)

        local issue_key=$(echo "$response" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)

        if [ -n "$issue_key" ]; then
            log "INFO" "JIRA issue created: $issue_key"
            echo "$issue_key"
        else
            log "WARN" "Failed to create JIRA issue: $response"
        fi
    fi
}

# Function to check service health
check_service() {
    local name="$1"
    local url="$2"
    local endpoint="${3:-/health}"

    local full_url="${url}${endpoint}"
    local response
    local http_code

    # Make request with timeout
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$full_url" 2>/dev/null || echo "000")

    if [ "$http_code" = "200" ]; then
        log "INFO" "$name is healthy (HTTP $http_code)"
        return 0
    else
        log "ERROR" "$name is unhealthy (HTTP $http_code)"
        return 1
    fi
}

# Function to check Docker container health
check_docker_container() {
    local container_name="$1"

    if ! command -v docker &> /dev/null; then
        log "WARN" "Docker not available, skipping container check for $container_name"
        return 0
    fi

    local status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "not_found")

    case "$status" in
        healthy)
            log "INFO" "Container $container_name is healthy"
            return 0
            ;;
        unhealthy)
            log "ERROR" "Container $container_name is unhealthy"
            return 1
            ;;
        starting)
            log "WARN" "Container $container_name is still starting"
            return 0
            ;;
        *)
            log "WARN" "Container $container_name status: $status"
            return 1
            ;;
    esac
}

# Main health check routine
main() {
    log "INFO" "Starting health check..."

    local failed_services=()
    local alert_message=""

    # Check HTTP endpoints
    if ! check_service "Frontend" "$FRONTEND_URL" "/health"; then
        failed_services+=("Frontend")
    fi

    if ! check_service "Backend" "$BACKEND_URL" "/health"; then
        failed_services+=("Backend")
    fi

    # Optional: Check gateway if configured
    if [ "$GATEWAY_URL" != "http://localhost:8080" ] || curl -s --connect-timeout 2 "$GATEWAY_URL" > /dev/null 2>&1; then
        if ! check_service "Gateway" "$GATEWAY_URL" "/health"; then
            failed_services+=("Gateway")
        fi
    fi

    # Check Docker containers
    check_docker_container "maestro-frontend" || failed_services+=("maestro-frontend-container")
    check_docker_container "maestro-backend" || failed_services+=("maestro-backend-container")
    check_docker_container "maestro-redis" || failed_services+=("maestro-redis-container")
    check_docker_container "maestro-postgres" || failed_services+=("maestro-postgres-container")

    # Send alerts if any services failed
    if [ ${#failed_services[@]} -gt 0 ]; then
        alert_message="🚨 Services down: ${failed_services[*]}\n\nServer: $(hostname)\nTime: $(date)"

        log "ERROR" "Health check failed! Services down: ${failed_services[*]}"

        # Send alerts
        send_slack_alert "$alert_message" "danger"
        send_email_alert "[ALERT] Maestro Services Down" "$alert_message"
        create_jira_issue "Services Down: ${failed_services[*]}" "Health check failed on $(hostname) at $(date). Services down: ${failed_services[*]}"

        exit 1
    else
        log "INFO" "All services are healthy"
        exit 0
    fi
}

# Run main function
main "$@"
