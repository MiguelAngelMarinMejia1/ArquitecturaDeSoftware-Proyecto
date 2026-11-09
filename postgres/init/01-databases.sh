#!/bin/sh
# ---------------------------------------------------------------------------
# Runs once, the first time the postgres_data volume is created.
#
# One PostgreSQL server, one database and one role per owner of data:
#
#   hotelmdj       owned by $POSTGRES_USER  -> Django monolith (+ Celery worker)
#   payments       owned by payments        -> Flask payment service
#   notifications  owned by notifications   -> Flask notification service
#
#   catalog_reader can only SELECT in hotelmdj -> Flask catalog service
#
# No service can read or write another service's database. To re-run this
# script: docker compose down -v (deletes ALL data) and up again.
# ---------------------------------------------------------------------------
set -eu

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v main_user="$POSTGRES_USER" \
     -v main_db="$POSTGRES_DB" \
     -v catalog_pw="$CATALOG_DB_PASSWORD" \
     -v payments_pw="$PAYMENTS_DB_PASSWORD" \
     -v notifications_pw="$NOTIFICATIONS_DB_PASSWORD" <<'EOSQL'

-- Catalog: read-only access to the monolith's tables.
CREATE ROLE catalog_reader LOGIN PASSWORD :'catalog_pw';
GRANT CONNECT ON DATABASE :"main_db" TO catalog_reader;
GRANT USAGE ON SCHEMA public TO catalog_reader;
-- Django creates the tables later (migrate); grant on those too.
ALTER DEFAULT PRIVILEGES FOR ROLE :"main_user" IN SCHEMA public
    GRANT SELECT ON TABLES TO catalog_reader;
ALTER ROLE catalog_reader SET default_transaction_read_only = on;

-- Payments: its own database.
CREATE ROLE payments LOGIN PASSWORD :'payments_pw';
CREATE DATABASE payments OWNER payments;

-- Notifications: its own database.
CREATE ROLE notifications LOGIN PASSWORD :'notifications_pw';
CREATE DATABASE notifications OWNER notifications;

-- Nobody but the owner connects to each database.
REVOKE CONNECT ON DATABASE payments FROM PUBLIC;
REVOKE CONNECT ON DATABASE notifications FROM PUBLIC;
REVOKE CONNECT ON DATABASE :"main_db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"main_db" TO :"main_user";
EOSQL
