-- Docker PostgreSQL initialization script
-- This file will be executed when the PostgreSQL container starts for the first time

-- Create the main database if it doesn't exist
-- (karma_app_dev will be created automatically by POSTGRES_DB env var)

-- Grant all privileges to postgres user
GRANT ALL PRIVILEGES ON DATABASE karma_app_dev TO postgres;

-- You can add initial table creation here if needed
-- The application will handle table creation via migrations

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log completion
SELECT 'Database initialization completed' as status; 