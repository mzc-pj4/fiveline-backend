import os

# Set AWS env vars at import time (before any fixture runs)
# so module-level boto3 clients in Lambda handlers can initialize without error.
# These are dummy values — no real AWS calls are made during tests.
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-2")
os.environ.setdefault("AWS_REGION", "ap-northeast-2")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
