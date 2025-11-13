#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'fintech_user') THEN
            CREATE USER fintech_user WITH PASSWORD 'strong_password';
        END IF;
    END
    \$\$;
    
    SELECT 'CREATE DATABASE fintech_db_test OWNER fintech_user'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'fintech_db_test')\gexec
    
    GRANT ALL PRIVILEGES ON DATABASE fintech_db_test TO fintech_user;
EOSQL