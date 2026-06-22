# AI Auto-Remediation

> 챗봇이 자연어 요청을 받아 Terraform 코드 변경 PR을 **자동 생성**.  
> 머지·apply는 사람이 검토 후 수동. AI 환각 사고 방지.

## 🎯 무엇을 하나

```
사용자: "오늘 미사용 EBS 정리해줘"
   ↓
LangGraph → 이 Lambda 호출
   ↓
1) 안전 검증 (whitelist, owner 태그)
2) GitHub에서 현재 .tf 파일 fetch
3) Bedrock Claude → 변경 코드 + 영향 분석 생성
4) 새 브랜치 + commit + PR 자동 생성
5) Audit DDB 기록
   ↓
챗봇 응답: "PR #45 생성! 검토 부탁드립니다 🔗 ..."
```

## 📁 파일 구조

```
ai-remediation/
├── handler.py            메인 흐름 (Lambda entry point)
├── validator.py          안전 검증 (whitelist + owner tag)
├── github_client.py      GitHub API 클라이언트 (urllib, 의존성 X)
├── terraform_editor.py   Bedrock 프롬프트 + JSON 파싱
├── requirements.txt      의존성 없음 (boto3 Lambda 기본 내장)
├── test_local.py         로컬 테스트 스크립트
└── README.md             이 문서
```

## 🛡️ 안전 설계 (7중 방어)

| | 장치 | 동작 |
|---|---|---|
| 1 | Action whitelist | `delete` / `tag` / `modify` 만 허용 |
| 2 | 위험 자원 패턴 | `*-prod-*`, `i-prod*` 등 자동 차단 |
| 3 | Owner 태그 검증 | `Owner=jihoo` 또는 태그 없는 거만 |
| 4 | AWS 자원 존재 확인 | 환각 ID 차단 (describe API 호출) |
| 5 | MOCK_MODE 환경변수 | 초기 배포 시 실제 PR 생성 X |
| 6 | PR 본문 자동 경고 | "AI 자동 생성, 머지 전 검토 필수" 명시 |
| 7 | 자동 머지 절대 X | 사람만 머지 가능 (GitHub branch protection) |

## ⚙️ 환경 변수

| 이름 | 설명 | 기본값 |
|---|---|---|
| `GITHUB_TOKEN_SECRET` | GitHub PAT 의 Secrets Manager ARN | 필수 |
| `GITHUB_REPO` | `owner/repo` | `Kjihoo/aws-aiops-platform` |
| `GITHUB_BASE_BRANCH` | PR 머지 대상 | `feat/jihoo-data-pipeline` |
| `TERRAFORM_PATH_PREFIX` | Terraform 코드 경로 | `terraform/jihoo` |
| `AUDIT_TABLE` | Audit DDB 테이블 | 필수 |
| `BEDROCK_MODEL` | Claude 모델 ID | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `MOCK_MODE` | true=실제 PR X | `true` (안전) |

## 🔄 호출 형식

### 입력
```json
{
  "resource_id": "vol-01e455b067179d5bf",
  "action": "delete",
  "rationale": "6/2 이후 unattached, snapshot 없음",
  "session_id": "abc-123"
}
```

### 출력 (성공)
```json
{
  "request_id": "req-1718700000-vol-01e4",
  "status": "pr_created",
  "pr_url": "https://github.com/Kjihoo/aws-aiops-platform/pull/45",
  "risk_level": "low",
  "impact_analysis": "vol-01e455... 만 제거, 데이터 손실 없음",
  "files_changed": ["data_pipeline.tf"]
}
```

### 출력 (차단)
```json
{
  "status": "rejected",
  "reason": "위험 자원 패턴 매칭, 자동 PR 생성 차단: i-prod[0-9a-f]+"
}
```

## 🧪 로컬 테스트

```bash
cd terraform/jihoo/lambda-src/ai-remediation
MOCK_MODE=true python test_local.py
```

→ Bedrock·GitHub·AWS 호출 없이 로직만 검증.

실제 GitHub 테스트:
```bash
export GITHUB_TOKEN="ghp_..."
MOCK_MODE=false python test_local.py
```

## 📋 배포 절차

```
1. terraform apply
   - DynamoDB ai-remediation-audit 생성
   - Secrets Manager 시크릿 생성 (빈 값)
   - IAM Role + Policy
   - Lambda 함수 (MOCK_MODE=true 로 시작)

2. GitHub PAT 생성 + Secrets Manager 값 입력
   - GitHub Settings → Developer settings → Personal access tokens
   - 권한: repo (전체) — PR 생성용
   
   aws secretsmanager put-secret-value \
     --secret-id <arn> \
     --secret-string "ghp_xxxxxxxx"

3. LangGraph Lambda 환경변수 REMEDIATION_LAMBDA 설정 + 재배포
   (Docker 이미지 재빌드 필요 — tools.py 변경 반영)

4. MOCK_MODE=true 로 검증
   - 챗봇에 "테스트 정리해줘" 요청
   - CloudWatch Logs 에서 PR 생성 시뮬레이션 확인

5. MOCK_MODE=false 변경 후 재배포
   - 실제 PR 생성 흐름 검증
   - 첫 PR 머지 X (수동으로 close 권장)

6. 전체 시연 시나리오 녹화
```

## 🎤 발표 시연 시나리오

```
[화면 1: 대시보드 챗봇]
사용자: "오늘 미사용 리소스 자동으로 정리해줘"

[15초 대기]

AI: 분석 결과 vol-01e455... 1GB 미사용 발견.
    정리 PR 생성 완료:
    🔗 https://github.com/.../pull/45
    [🔧 도구: get_resource_check → propose_remediation]

[화면 2: GitHub PR]
🤖 [AI] delete vol-01e455b067179d5bf

변경 사항:
- terraform/jihoo/data_pipeline.tf (-12 줄)

영향 분석:
vol-01e455... 는 unattached 상태. Snapshot 없음.
데이터 손실 없음. 의존성 X.

위험도: LOW
라벨: ai-generated, risk-low

[Merge pull request 버튼]

[화면 3: 검토 후 머지]
"이 PR 머지하면 다음 terraform apply 때 EBS 자동 삭제됩니다."
Merge → CI/CD 가 자동 apply (이현지님 영역)

[화면 4: 챗봇으로 돌아가서]
사용자: "방금 정리한 거 확인해줘"

AI: vol-01e455... 가 더 이상 존재하지 않음을 확인했습니다.
    정리 완료. 월 약 100원 절감.
```

## 🔧 트러블슈팅

### "Bedrock 응답 JSON 파싱 실패"
- Claude 가 가끔 JSON 외 텍스트 추가
- terraform_editor.py 가 ```json ... ``` 블록 자동 추출
- 그래도 실패 시 max_tokens 증가 or temperature 낮춤

### "자원 미존재"
- Resource Checker 가 발견한 자원 ID 가 이미 삭제됨
- 정상 동작 — 무시

### "다른 팀원 자원, 차단"
- Owner 태그가 jihoo 가 아닌 경우
- 의도된 동작 — 다른 팀원에게 PR 부탁

### GitHub API rate limit
- 인증된 호출 = 시간당 5,000회
- 우리 사용량 = 시간당 10회 미만
- 문제 거의 없음

## 📊 비용

| 항목 | 월 추정 |
|---|---|
| Lambda 실행 | ~50원 (호출 빈도 낮음) |
| Bedrock Claude | ~500원 (코드 분석 토큰) |
| Secrets Manager | ~400원 (시크릿 1개) |
| DynamoDB Audit | ~10원 (PAY_PER_REQUEST) |
| **합계** | **~960원/월** |

## 🎯 다음 단계 (Level 3)

- 위험도 low 자원은 PR 자동 머지 (whitelist)
- 위험도 medium/high 만 사람 승인
- 적용 후 Resource Checker 가 확인 → 챗봇이 결과 알림
