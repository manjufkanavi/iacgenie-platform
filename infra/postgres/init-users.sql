-- =============================================================================
-- PostgreSQL Multi-Tenant Init Script
-- =============================================================================
-- Creates schemas for each tenant and sets up proper access control
-- =============================================================================

-- Keycloak tenant (always exists)
CREATE DATABASE IF NOT EXISTS keycloak;

-- =============================================================================
-- IacGenie Tenant
-- =============================================================================
SELECT 'CREATE DATABASE iacgenie'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'iacgenie')\gexec

-- Connect to iacgenie database and create schema
\c iacgenie

-- Set schema ownership
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO public;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO postgres;

-- =============================================================================
-- LightSerp Tenant
-- =============================================================================
SELECT 'CREATE DATABASE lightsrp'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'lightsrp')\gexec

-- Connect to lightsrp database and create schema
\c lightsrp

-- Set schema ownership
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO public;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO postgres;

-- =============================================================================
-- Keycloak Tenant
-- =============================================================================
\c keycloak

-- Set schema ownership
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO public;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO postgres;
