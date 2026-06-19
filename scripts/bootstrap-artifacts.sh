#!/usr/bin/env bash
# Bootstrap: Lambda zip 빌드 후 S3 artifact 버킷에 업로드
# 사용: ARTIFACTS_BUCKET=fiveline-artifacts-<account_id> bash scripts/bootstrap-artifacts.sh
# 최초 1회 실행. 이후에는 GitHub Actions가 자동으로 관리.

set -euo pipefail

BUCKET="${ARTIFACTS_BUCKET:?환경변수 ARTIFACTS_BUCKET을 설정하세요}"
REGION="${AWS_REGION:-ap-northeast-2}"

echo "Artifact 버킷: s3://${BUCKET}"

for category in ai data-pipeline observability; do
  for func_dir in lambda/$category/*/; do
    [ -d "$func_dir" ] || continue
    func=$(basename "$func_dir")
    zip_file="/tmp/${func}.zip"
    cd "$func_dir"
    zip -r "$zip_file" . -x "*.pyc" -x "__pycache__/*" > /dev/null
    cd - > /dev/null
    aws s3 cp "$zip_file" "s3://${BUCKET}/lambda/${category}/${func}.zip" --region "$REGION"
    rm "$zip_file"
    echo "  ✓ lambda/${category}/${func}.zip"
  done
done

echo "Glue 스크립트 업로드..."
aws s3 sync glue-scripts/ "s3://${BUCKET}/glue/" --region "$REGION"
echo "  ✓ glue scripts"

echo "Bootstrap 완료."
