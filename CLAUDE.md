# AWS AI 기반 인프라 운영·비용 분석 및 리포트 자동화 플랫폼

## 프로젝트 개요

AWS에서 운영 중인 워크로드의 메트릭·로그·비용·구성 데이터를 통합 수집·분석하고, Amazon Bedrock Agent로 운영자에게 자연어 질의응답·자동 리포트·실시간 알림을 제공하는 운영 자동화 플랫폼.

## 도메인

샘플 이커머스 워크로드 (CloudFront → ALB → EKS → RDS PostgreSQL 흐름). 도메인 자체가 핵심이 아니라 "어떤 워크로드든 운영 자동화 가능"을 증명하는 샘플.

## 아키텍처 레이어

1. 운영 대상 워크로드(이커머스 샘플): CloudFront + S3 정적 웹 + ALB Ingress + EKS + RDS PostgreSQL + NAT GW
2. 데이터 수집·저장: CloudWatch(Metrics/Logs/Alarm), Cost Explorer/CUR, AWS Config, Resource Tagging API, Resource Checker Lambda → S3 Data Lake(raw/cleansed/aggregated) + DynamoDB
3. 시각화·AI·알림: Grafana, QuickSight, Amazon Bedrock Agent, Slack 알림, 자동 리포트
4. 자동화·배포·IaC: Terraform + GitHub Actions + OIDC

## 확정 값 (W1)

- project_name: `team4-aiops`
- AWS 계정 ID: `089955620282`
- 리전: `ap-northeast-2`
- Terraform state: S3 `team4-aiops-tfstate-089955620282` + DynamoDB `team4-aiops-tflock`
- GitHub repos (mzc-pj4 org):
  - 백엔드: `mzc-pj4/fiveline-backend`
  - 프론트엔드: `mzc-pj4/fiveline-frontend`
  - 인프라 IaC: 별도 Terraform repo
  - (legacy 첫 push: `Kjihoo/aws-aiops-platform` — 더 이상 사용 안 함)

## W1 목표 (완료)

- 백엔드/프론트 레포 초기 셋업
- Terraform IaC는 별도 repo에서 신규 구성
- 배포 목표는 EKS + RDS PostgreSQL + S3/CloudFront

## 주의 사항

- 모호한 부분은 추측하지 않고 질문
- 하드코딩 ARN/계정 ID 금지 (data source / variable 사용)
- 공통 태그 `Project`, `Environment`, `ManagedBy` 는 provider `default_tags` 로 일괄 적용
- 모듈은 추가로 `Service`, 리소스별 `Name` 부여
- CI/CD의 AWS 자격증명은 OIDC 기반 IAM Role assume 사용
- W4 데이터 수집 우선순위는 `docs/architecture.md` 참고
