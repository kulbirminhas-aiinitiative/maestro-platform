-- Initialize Sunday.com database

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create database for different environments
CREATE DATABASE sunday_dev;
CREATE DATABASE sunday_test;
CREATE DATABASE sunday_prod;

-- Create users with appropriate permissions
CREATE USER sunday_dev WITH PASSWORD 'dev_password123';
CREATE USER sunday_test WITH PASSWORD 'test_password123';
CREATE USER sunday_prod WITH PASSWORD 'prod_password123';

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE sunday_dev TO sunday_dev;
GRANT ALL PRIVILEGES ON DATABASE sunday_test TO sunday_test;
GRANT ALL PRIVILEGES ON DATABASE sunday_prod TO sunday_prod;

-- Connect to each database and create extensions
\c sunday_dev;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

\c sunday_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

\c sunday_prod;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";