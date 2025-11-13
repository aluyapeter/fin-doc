#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create test user
    CREATE USER fintech_user WITH PASSWORD 'strong_password';
    
    -- Create test database
    CREATE DATABASE fintech_db_test OWNER fintech_user;
    
    -- Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE fintech_db_test TO fintech_user;
EOSQL
