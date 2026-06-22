import os

# Set at import time (before any fixture) so module-level boto3 clients can
# initialize without error. Using direct assignment to override any stale values.
# These are dummy values — no real AWS calls are made during tests.
os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-2"
os.environ["AWS_REGION"] = "ap-northeast-2"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
