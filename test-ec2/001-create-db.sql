SELECT 'CREATE DATABASE ridelist'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'ridelist'
)\gexec