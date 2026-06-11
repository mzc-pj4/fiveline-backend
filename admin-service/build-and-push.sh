#!/bin/bash
set -e

ECR_IMAGE="089955620282.dkr.ecr.ap-northeast-2.amazonaws.com/fiveline/admin-service:latest"
ADMIN_FRONTEND="../../../fiveline-frontend/admin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

aws ecr get-login-password --region ap-northeast-2 --profile ljm \
  | docker login --username AWS --password-stdin 089955620282.dkr.ecr.ap-northeast-2.amazonaws.com

docker build \
  --build-context admin-frontend="$SCRIPT_DIR/$ADMIN_FRONTEND" \
  -t "$ECR_IMAGE" \
  "$SCRIPT_DIR"

docker push "$ECR_IMAGE"

kubectl rollout restart deployment admin-service -n fiveline
kubectl rollout status deployment admin-service -n fiveline --timeout=120s

echo "admin-service 배포 완료"
