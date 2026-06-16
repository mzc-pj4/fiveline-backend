-- fiveline 로컬 dev DB bootstrap.
-- Each service owns its own schema in a shared instance.

CREATE SCHEMA IF NOT EXISTS user_schema;
CREATE SCHEMA IF NOT EXISTS product_schema;
CREATE SCHEMA IF NOT EXISTS order_schema;
CREATE SCHEMA IF NOT EXISTS notification_schema;
