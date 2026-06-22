"""
Bedrock Claude 로 Terraform 코드 변경 자동 생성
- 입력: 현재 .tf 파일 dict + 자원 ID + 액션
- 출력: 변경된 파일들 + 영향 분석 + 위험도
"""

import json


PROMPT_TEMPLATE = """당신은 Terraform 전문가입니다. 사용자 요청에 따라 AWS 자원 정리를 위한 Terraform 코드 변경을 만들어주세요.

# 작업 정보
- 자원 ID: {resource_id}
- 작업: {action}
- 사유: {rationale}

# 현재 Terraform 코드 (jihoo 폴더)
{tf_files_str}

# 작업 지침
1. 자원 ID `{resource_id}` 를 정확히 찾아서 처리
2. 작업이 `delete` 면 해당 자원 정의 블록을 제거 (의존성 있는 블록도 함께 정리)
3. 작업이 `tag` 면 tags 블록에 누락된 표준 태그 추가 (Project, Environment, Owner)
4. 작업이 `modify` 면 사유에 명시된 속성만 변경
5. 영향 받지 않는 다른 코드는 절대 수정 금지
6. 변경된 파일만 응답에 포함 (변경 없는 파일은 제외)

# 응답 형식 (반드시 JSON, 한국어 분석)
```json
{{
  "files_changed": [
    {{
      "filename": "<파일명, 예: data_pipeline.tf>",
      "new_content": "<수정된 전체 파일 내용>"
    }}
  ],
  "impact_analysis": "<영향 분석 한국어 3~5줄: 어떤 자원이 어떻게 바뀌고, 의존성·데이터 손실·다운타임 여부>",
  "risk_level": "low|medium|high"
}}
```

# 위험도 기준
- low: unattached 자원 삭제, 태그만 추가, 데이터 손실 없음
- medium: 사용 중 자원의 속성 변경, 일시적 영향
- high: 데이터 손실 가능, prod 영향, 의존 자원 다수 있음

코드 외에 다른 텍스트는 응답에 포함하지 마세요. JSON만 반환.
"""


def generate_terraform_change(
    bedrock_client,
    model_id: str,
    resource_id: str,
    action: str,
    rationale: str,
    tf_files: dict,
) -> dict:
    """
    tf_files: {"data_pipeline.tf": "...", "lambda.tf": "...", ...}
    Returns:
        {
            "files_changed": [...],
            "impact_analysis": "...",
            "risk_level": "low|medium|high"
        }
    """
    # 파일들을 프롬프트에 넣을 형식으로
    tf_files_str = ""
    for filename, content in tf_files.items():
        # 너무 긴 파일은 잘라서 (토큰 절약). 자원 ID 가 포함된 파일은 전체.
        if resource_id in content:
            tf_files_str += f"\n## {filename} (자원 포함)\n```hcl\n{content}\n```\n"
        elif len(content) < 3000:
            tf_files_str += f"\n## {filename}\n```hcl\n{content}\n```\n"
        else:
            tf_files_str += f"\n## {filename} (요약)\n```hcl\n{content[:1500]}\n... (생략) ...\n```\n"

    prompt = PROMPT_TEMPLATE.format(
        resource_id=resource_id,
        action=action,
        rationale=rationale or "사용자 요청",
        tf_files_str=tf_files_str,
    )

    # Bedrock 호출 (Converse API)
    resp = bedrock_client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={
            "maxTokens": 8192,
            "temperature": 0.1,  # 결정적 응답 (코드는 일관성 중요)
        },
    )

    text = resp["output"]["message"]["content"][0]["text"].strip()

    # JSON 코드 블록 추출
    if "```json" in text:
        text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()

    try:
        change = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Bedrock 응답 JSON 파싱 실패: {e}\n응답: {text[:500]}")

    # 필수 필드 검증
    if "files_changed" not in change:
        raise RuntimeError(f"files_changed 누락. 응답: {text[:500]}")
    if not change["files_changed"]:
        raise RuntimeError(f"변경 파일이 없음 (자원 못 찾은 듯). 응답: {text[:500]}")

    change.setdefault("impact_analysis", "분석 누락")
    change.setdefault("risk_level", "medium")

    return change
