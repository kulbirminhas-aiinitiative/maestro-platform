-- Maestro Platform - PostgreSQL Database Initialization
-- Creates separate databases for each service with proper isolation

-- ============================================================================
-- CREATE DATABASES
-- ============================================================================

-- Quality Fabric Database
CREATE DATABASE quality_fabric
    WITH
    OWNER = maestro_admin
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE quality_fabric IS 'Quality Fabric - Testing as a Service Platform';

-- Maestro V2 Database
CREATE DATABASE maestro_v2
    WITH
    OWNER = maestro_admin
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE maestro_v2 IS 'Maestro V2 - Backend Services';

-- Maestro Frontend Database
CREATE DATABASE maestro_frontend
    WITH
    OWNER = maestro_admin
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE maestro_frontend IS 'Maestro Frontend - User Interface Data';

-- Grafana Database (for Grafana's internal storage)
CREATE DATABASE grafana
    WITH
    OWNER = maestro_admin
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE grafana IS 'Grafana - Dashboards and Configuration Storage';

-- MLflow Database (for ML experiment tracking and model registry)
CREATE DATABASE mlflow
    WITH
    OWNER = maestro_admin
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

COMMENT ON DATABASE mlflow IS 'MLflow - ML Experiment Tracking and Model Registry';

-- ============================================================================
-- CREATE SERVICE USERS (One user per service)
-- ============================================================================

-- Quality Fabric user
CREATE USER quality_fabric WITH
    LOGIN
    PASSWORD 'qf_db_secure_2025'
    CONNECTION LIMIT 50;

COMMENT ON ROLE quality_fabric IS 'Quality Fabric service user';

-- Maestro V2 user
CREATE USER maestro_v2 WITH
    LOGIN
    PASSWORD 'mv2_db_secure_2025'
    CONNECTION LIMIT 50;

COMMENT ON ROLE maestro_v2 IS 'Maestro V2 service user';

-- Maestro Frontend user
CREATE USER maestro_frontend WITH
    LOGIN
    PASSWORD 'mfe_db_secure_2025'
    CONNECTION LIMIT 50;

COMMENT ON ROLE maestro_frontend IS 'Maestro Frontend service user';

-- ============================================================================
-- GRANT PRIVILEGES (Each service can ONLY access its own database)
-- ============================================================================

-- Quality Fabric permissions
GRANT ALL PRIVILEGES ON DATABASE quality_fabric TO quality_fabric;
\c quality_fabric
GRANT ALL ON SCHEMA public TO quality_fabric;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO quality_fabric;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO quality_fabric;

-- Maestro V2 permissions
\c postgres
GRANT ALL PRIVILEGES ON DATABASE maestro_v2 TO maestro_v2;
\c maestro_v2
GRANT ALL ON SCHEMA public TO maestro_v2;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO maestro_v2;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO maestro_v2;

-- Maestro Frontend permissions
\c postgres
GRANT ALL PRIVILEGES ON DATABASE maestro_frontend TO maestro_frontend;
\c maestro_frontend
GRANT ALL ON SCHEMA public TO maestro_frontend;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO maestro_frontend;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO maestro_frontend;

-- ============================================================================
-- SECURITY: REVOKE CROSS-DATABASE ACCESS
-- ============================================================================

\c postgres

-- Quality Fabric: Cannot access other databases
REVOKE CONNECT ON DATABASE maestro_v2 FROM quality_fabric;
REVOKE CONNECT ON DATABASE maestro_frontend FROM quality_fabric;

-- Maestro V2: Cannot access other databases
REVOKE CONNECT ON DATABASE quality_fabric FROM maestro_v2;
REVOKE CONNECT ON DATABASE maestro_frontend FROM maestro_v2;

-- Maestro Frontend: Cannot access other databases
REVOKE CONNECT ON DATABASE quality_fabric FROM maestro_frontend;
REVOKE CONNECT ON DATABASE maestro_v2 FROM maestro_frontend;

-- ============================================================================
-- ENABLE EXTENSIONS (If needed by services)
-- ============================================================================

\c quality_fabric
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\c maestro_v2
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\c maestro_frontend
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c postgres
SELECT 'Database initialization complete!' AS status;
