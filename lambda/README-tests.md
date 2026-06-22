# Lambda pytest 가이드

> 작성자: 김지후 (data-pipeline + AI 영역)
> 2026-06-22

## 📁 구조

```
lambda/
├── pytest.ini                 ← pytest 설정
├── requirements-dev.txt       ← 테스트 의존성
├── README-tests.md            ← 이 문서
├── ai/
│   ├── ai-remediation/
│   │   ├── handler.py
│   │   ├── validator.py
│   │   ├── github_client.py
│   │   ├── terraform_editor.py
│   │   └── tests/             ← 30 tests
│   │       ├── test_validator.py
│   │       ├── test_terraform_editor.py
│   │       └── test_github_client.py
│   └── report-embedder/
│       └── tests/             ← 8 tests
├── data-pipeline/
│   ├── resource-checker/
│   │   └── tests/             ← 12 tests
│   └── pipeline-orchestrator/
│       └── tests/             ← 7 tests
```

총 **약 57개 테스트**.

## 🚀 실행

### 로컬
```bash
# 의존성 설치 (한 번만)
pip install -r lambda/requirements-dev.txt

# 전체 실행
cd lambda && pytest

# 특정 함수만
pytest ai/ai-remediation/tests/

# 특정 파일만
pytest ai/ai-remediation/tests/test_validator.py

# 특정 테스트 1개
pytest ai/ai-remediation/tests/test_validator.py::test_prod_pattern_blocked
```

### CI/CD (이현지님 워크플로우 통합용)
```yaml
- name: Run Lambda pytest
  run: |
    pip install -r lambda/requirements-dev.txt
    cd lambda && pytest
```

## 🛡️ 테스트 전략

### Mock 위주
- **모든 AWS 호출 (boto3) 은 mock** — 실제 호출 X
- **외부 API (Bedrock, GitHub) 도 mock** — 환경 격리
- 단위 테스트가 빠르고 결정적

### 검증 포인트별
| 함수 | 주요 테스트 |
|---|---|
| ai-remediation/validator | whitelist + prod 패턴 + Owner 태그 (15) |
| ai-remediation/terraform_editor | Bedrock 응답 JSON 파싱 + 에러 처리 (7) |
| ai-remediation/github_client | GitHub API mock + PR 본문 (7) |
| report-embedder | S3 listing + Bedrock embed + DDB put (8) |
| resource-checker | EBS/EIP/Snapshot/Tag/SG/RDS 6종 점검 (12) |
| pipeline-orchestrator | Glue→MSCK→Lambda 체인 (7) |

## 🔄 CI 통합 — 이현지님께 제안

워크플로우 추가 (`.github/workflows/lambda-tests.yml`):

```yaml
name: Lambda pytest

on:
  pull_request:
    paths:
      - 'lambda/**'
  push:
    branches: [main, develop]
    paths:
      - 'lambda/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r lambda/requirements-dev.txt

      - name: Run pytest
        run: cd lambda && pytest --tb=short

      - name: Upload coverage (optional)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pytest-results
          path: lambda/pytest-results.xml
```

## ⚠️ 주의

- **environment variable**: 각 test 파일이 `os.environ.setdefault()` 로 기본값 주입
  → CI 에서 별도 env 설정 불필요
- **느린 테스트**: `@pytest.mark.slow` 마커 (현재 없음)
- **실제 AWS 호출**: `@pytest.mark.integration` 마커 (현재 없음, MOCK 위주)

## 🎯 추가 작성 권장 (시간 되면)

- [ ] handler.py 통합 흐름 (ai-remediation/handler.py 통합 테스트)
- [ ] coverage 측정 (`pytest --cov=lambda`)
- [ ] benchmark (`pytest-benchmark`)
