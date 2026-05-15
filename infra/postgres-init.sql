-- W2 dev DB bootstrap. Runs once on first postgres container start.
-- Each service owns its own schema in a shared instance.

CREATE SCHEMA IF NOT EXISTS user_schema;
CREATE SCHEMA IF NOT EXISTS product_schema;
CREATE SCHEMA IF NOT EXISTS order_schema;

-- Default search_path is set per-connection in each service via DB_SCHEMA env.
