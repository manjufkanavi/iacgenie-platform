#!/bin/bash
# PostgreSQL Initialization Script
# Creates databases and users for iacgenie, lightserp, keycloak, and logtide
#
# IMPORTANT: This script MUST be updated when passwords in .env change.
# The init script is NOT sourced from .env at runtime — passwords are baked in.
# See: https://docs.docker.com/compose/compose-file/compose-file-v3/#environment
#
# Current passwords as of 2026-07-26:
#   iacgenie/lightsrp user:     POSTGRES_APP_PASSWORD (from .env)
#   keycloak user:               POSTGRES_KC_PASSWORD (from .env)
#   logtide user:                POSTGRES_LOGTIDE_PASSWORD (from .env)
#
# Usage: This script is mounted as /docker-entrypoint-initdb.d/99-init-users.sql
#        and runs once when the postgres data volume is empty.

set -euo pipefail

psql -v ON_ERROR_STOP=1 --username postgres --dbname postgres <<EOSQL

  -- Drop and recreate databases (idempotent for first boot)
  DROP DATABASE IF EXISTS iacgenie CASCADE;
  DROP DATABASE IF EXISTS keycloak CASCADE;
  DROP DATABASE IF EXISTS lightsrp CASCADE;
  DROP DATABASE IF EXISTS logtide CASCADE;

  -- Drop and recreate users
  DROP USER IF EXISTS iacgenie;
  DROP USER IF EXISTS keycloak;
  DROP USER IF EXISTS lightsrp;
  DROP USER IF EXISTS logtide;

  -- Create users with passwords from .env file
  CREATE USER iacgenie WITH PASSWORD 'CHANGE_ME_POSTGRES_APP_PASSWORD';
  CREATE USER keycloak WITH PASSWORD 'CHANGE_ME_POSTGRES_KC_PASSWORD';
  CREATE USER lightsrp WITH PASSWORD 'CHANGE_ME_POSTGRES_APP_PASSWORD';
  CREATE USER logtide WITH PASSWORD 'CHANGE_ME_POSTGRES_LOGTIDE_PASSWORD';

  -- Create databases with correct owners
  CREATE DATABASE iacgenie OWNER iacgenie;
  CREATE DATABASE keycloak OWNER keycloak;
  CREATE DATABASE lightsrp OWNER lightsrp;
  CREATE DATABASE logtide OWNER logtide;

  -- Grant privileges
  GRANT ALL PRIVILEGES ON DATABASE iacgenie TO iacgenie;
  GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
  GRANT ALL PRIVILEGES ON DATABASE lightsrp TO lightsrp;
  GRANT ALL PRIVILEGES ON DATABASE logtide TO logtide;

  -- Verify users created
  SELECT usename FROM pg_user WHERE usename != 'postgres' ORDER BY usename;
EOSQL
