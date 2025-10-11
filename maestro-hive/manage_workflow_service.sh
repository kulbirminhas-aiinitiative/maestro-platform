#!/bin/bash
# Maestro Automated Workflow Service Management Script

set -e

SERVICE_NAME="automated_workflow"
SERVICE_FILE="automated_workflow.service"
SYSTEMD_DIR="/etc/systemd/system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$1" in
    install)
        echo "🔧 Installing Maestro Automated Workflow Service..."
        sudo cp "$SCRIPT_DIR/$SERVICE_FILE" "$SYSTEMD_DIR/$SERVICE_NAME.service"
        sudo systemctl daemon-reload
        echo "✅ Service installed"
        echo ""
        echo "Next steps:"
        echo "  sudo systemctl enable $SERVICE_NAME    # Enable on boot"
        echo "  sudo systemctl start $SERVICE_NAME     # Start now"
        echo "  sudo systemctl status $SERVICE_NAME    # Check status"
        ;;

    uninstall)
        echo "🗑️  Uninstalling Maestro Automated Workflow Service..."
        sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
        sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
        sudo rm -f "$SYSTEMD_DIR/$SERVICE_NAME.service"
        sudo systemctl daemon-reload
        echo "✅ Service uninstalled"
        ;;

    start)
        echo "▶️  Starting service..."
        sudo systemctl start $SERVICE_NAME
        echo "✅ Service started"
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    stop)
        echo "⏹️  Stopping service..."
        sudo systemctl stop $SERVICE_NAME
        echo "✅ Service stopped"
        ;;

    restart)
        echo "🔄 Restarting service..."
        sudo systemctl restart $SERVICE_NAME
        echo "✅ Service restarted"
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    status)
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;

    logs)
        echo "📋 Service logs (press Ctrl+C to exit):"
        sudo journalctl -u $SERVICE_NAME -f
        ;;

    logs-recent)
        echo "📋 Recent service logs:"
        sudo journalctl -u $SERVICE_NAME -n 100 --no-pager
        ;;

    test-once)
        echo "🧪 Running workflow once (test mode)..."
        cd "$SCRIPT_DIR"
        python3 automated_template_workflow.py --mode safe --once
        ;;

    *)
        echo "Maestro Automated Workflow Service Manager"
        echo ""
        echo "Usage: $0 {install|uninstall|start|stop|restart|status|logs|logs-recent|test-once}"
        echo ""
        echo "Commands:"
        echo "  install       Install systemd service"
        echo "  uninstall     Remove systemd service"
        echo "  start         Start the service"
        echo "  stop          Stop the service"
        echo "  restart       Restart the service"
        echo "  status        Show service status"
        echo "  logs          Follow live logs (Ctrl+C to exit)"
        echo "  logs-recent   Show recent logs"
        echo "  test-once     Run workflow once for testing"
        exit 1
        ;;
esac
