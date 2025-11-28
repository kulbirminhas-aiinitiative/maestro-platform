#!/usr/bin/env bash
#
# Maestro Deployment Notifications Script
#
# Sends notifications for deployment events: started, succeeded, failed, rolled back
# Supports Slack, Email, and JIRA updates
#
# Usage:
#   ./scripts/notify-deployment.sh started
#   ./scripts/notify-deployment.sh succeeded
#   ./scripts/notify-deployment.sh failed "Error message"
#   ./scripts/notify-deployment.sh rolled_back "Reason"
#
# Environment Variables:
#   SLACK_WEBHOOK_URL  - Slack webhook for notifications
#   ALERT_EMAIL        - Email for notifications
#   JIRA_EMAIL         - JIRA email for issue updates
#   JIRA_API_TOKEN     - JIRA API token
#   ENVIRONMENT        - Deployment environment (demo, staging, production)
#

set -euo pipefail

# Configuration
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
JIRA_BASE_URL="${JIRA_BASE_URL:-https://fifth9.atlassian.net}"
JIRA_EMAIL="${JIRA_EMAIL:-}"
JIRA_API_TOKEN="${JIRA_API_TOKEN:-}"
JIRA_PROJECT_KEY="${JIRA_PROJECT_KEY:-MD}"
ENVIRONMENT="${ENVIRONMENT:-demo}"

# Get deployment info
get_deployment_info() {
    local git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    local git_message=$(git log -1 --pretty=%B 2>/dev/null | head -1 || echo "No message")
    local deployer=$(git config user.name 2>/dev/null || whoami)
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local hostname=$(hostname)

    cat <<EOF
{
    "commit": "$git_commit",
    "branch": "$git_branch",
    "message": "$git_message",
    "deployer": "$deployer",
    "timestamp": "$timestamp",
    "hostname": "$hostname",
    "environment": "$ENVIRONMENT"
}
EOF
}

# Send Slack notification
send_slack_notification() {
    local event="$1"
    local message="${2:-}"
    local color=""
    local emoji=""
    local title=""

    case "$event" in
        started)
            color="#439FE0"
            emoji="🚀"
            title="Deployment Started"
            ;;
        succeeded)
            color="good"
            emoji="✅"
            title="Deployment Succeeded"
            ;;
        failed)
            color="danger"
            emoji="❌"
            title="Deployment Failed"
            ;;
        rolled_back)
            color="warning"
            emoji="⚠️"
            title="Deployment Rolled Back"
            ;;
        *)
            color="#808080"
            emoji="ℹ️"
            title="Deployment Update"
            ;;
    esac

    if [ -z "$SLACK_WEBHOOK_URL" ]; then
        echo "Slack webhook not configured, skipping Slack notification"
        return 0
    fi

    local info=$(get_deployment_info)
    local commit=$(echo "$info" | grep '"commit"' | cut -d'"' -f4)
    local branch=$(echo "$info" | grep '"branch"' | cut -d'"' -f4)
    local deployer=$(echo "$info" | grep '"deployer"' | cut -d'"' -f4)
    local git_message=$(echo "$info" | grep '"message"' | cut -d'"' -f4)

    local payload=$(cat <<EOF
{
    "attachments": [{
        "color": "$color",
        "title": "$emoji $title - $ENVIRONMENT",
        "fields": [
            {
                "title": "Environment",
                "value": "$ENVIRONMENT",
                "short": true
            },
            {
                "title": "Branch",
                "value": "$branch",
                "short": true
            },
            {
                "title": "Commit",
                "value": "$commit",
                "short": true
            },
            {
                "title": "Deployer",
                "value": "$deployer",
                "short": true
            },
            {
                "title": "Commit Message",
                "value": "$git_message",
                "short": false
            }
EOF
)

    # Add error message if provided
    if [ -n "$message" ]; then
        payload="$payload,
            {
                \"title\": \"Details\",
                \"value\": \"$message\",
                \"short\": false
            }"
    fi

    payload="$payload
        ],
        \"footer\": \"Maestro Deployment System\",
        \"ts\": $(date +%s)
    }]
}"

    curl -s -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" > /dev/null

    echo "✓ Slack notification sent"
}

# Send email notification
send_email_notification() {
    local event="$1"
    local message="${2:-}"

    if [ -z "$ALERT_EMAIL" ]; then
        echo "Email not configured, skipping email notification"
        return 0
    fi

    local subject="[Maestro] Deployment $event - $ENVIRONMENT"
    local info=$(get_deployment_info)

    local body="Deployment Event: $event
Environment: $ENVIRONMENT

Deployment Details:
$info

$([ -n "$message" ] && echo "Additional Info: $message")

---
Maestro Deployment System
$(date)"

    echo "$body" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || {
        echo "⚠ Failed to send email notification"
        return 1
    }

    echo "✓ Email notification sent"
}

# Create/update JIRA issue for deployment tracking
update_jira() {
    local event="$1"
    local message="${2:-}"

    if [ -z "$JIRA_EMAIL" ] || [ -z "$JIRA_API_TOKEN" ]; then
        echo "JIRA not configured, skipping JIRA update"
        return 0
    fi

    local info=$(get_deployment_info)
    local commit=$(echo "$info" | grep '"commit"' | cut -d'"' -f4)
    local branch=$(echo "$info" | grep '"branch"' | cut -d'"' -f4)
    local timestamp=$(echo "$info" | grep '"timestamp"' | cut -d'"' -f4)

    local summary="Deployment $event - $ENVIRONMENT ($commit)"
    local description="Deployment $event on $ENVIRONMENT environment.

Branch: $branch
Commit: $commit
Timestamp: $timestamp
$([ -n "$message" ] && echo "Details: $message")"

    # Create issue for failed or rolled_back events
    if [ "$event" = "failed" ] || [ "$event" = "rolled_back" ]; then
        local response
        response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
            -d "{
                \"fields\": {
                    \"project\": {\"key\": \"$JIRA_PROJECT_KEY\"},
                    \"summary\": \"[DEPLOY] $summary\",
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
                    \"labels\": [\"deployment\", \"$event\", \"$ENVIRONMENT\"]
                }
            }" "$JIRA_BASE_URL/rest/api/3/issue" 2>/dev/null)

        local issue_key=$(echo "$response" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)

        if [ -n "$issue_key" ]; then
            echo "✓ JIRA issue created: $issue_key"
        else
            echo "⚠ Failed to create JIRA issue"
        fi
    else
        echo "✓ JIRA notification (no issue created for $event event)"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 <event> [message]"
    echo ""
    echo "Events:"
    echo "  started      - Deployment started"
    echo "  succeeded    - Deployment completed successfully"
    echo "  failed       - Deployment failed"
    echo "  rolled_back  - Deployment rolled back"
    echo ""
    echo "Example:"
    echo "  $0 started"
    echo "  $0 failed \"Database migration failed\""
}

# Main
main() {
    local event="${1:-}"
    local message="${2:-}"

    if [ -z "$event" ]; then
        usage
        exit 1
    fi

    case "$event" in
        started|succeeded|failed|rolled_back)
            echo "Sending deployment notifications for: $event"
            echo ""
            send_slack_notification "$event" "$message"
            send_email_notification "$event" "$message"
            update_jira "$event" "$message"
            echo ""
            echo "All notifications sent!"
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown event: $event"
            usage
            exit 1
            ;;
    esac
}

main "$@"
