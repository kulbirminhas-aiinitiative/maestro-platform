# Maestro Platform - Demo Environment Configuration
# Passwords loaded from environment variables for security

# These will be loaded from TF_VAR_* environment variables:
# export TF_VAR_postgres_admin_password="$(cat ../../.env.infrastructure | grep MAESTRO_POSTGRES_ADMIN_PASSWORD | cut -d'=' -f2)"
# export TF_VAR_redis_password="$(cat ../../.env.infrastructure | grep MAESTRO_REDIS_PASSWORD | cut -d'=' -f2)"
# export TF_VAR_grafana_admin_password="$(cat ../../.env.infrastructure | grep MAESTRO_GRAFANA_ADMIN_PASSWORD | cut -d'=' -f2)"

postgres_admin_user = "maestro_admin"
grafana_admin_user  = "admin"

# Ports (auto-assigned if conflicts)
postgres_port   = 25432
redis_port      = 27379
prometheus_port = 29090
grafana_port    = 23000
