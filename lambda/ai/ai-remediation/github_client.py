"""
GitHub API 클라이언트 — Terraform 코드 읽기 + PR 자동 생성
"""

import base64
import json
from datetime import datetime, timezone
from urllib import request, error, parse


class GitHubClient:
    def __init__(self, token: str, repo: str):
        """
        token: GitHub Personal Access Token (repo scope)
        repo:  "owner/repo" 형식 (예: "Kjihoo/aws-aiops-platform")
        """
        self.token = token
        self.repo = repo
        self.api = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "fiveline-ai-remediation",
        }

    # ─── 내부 HTTP 헬퍼 (urllib 사용, requests 의존 X) ────────────────────

    def _request(self, method: str, path: str, body: dict = None, raw_url: str = None):
        url = raw_url or f"{self.api}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = request.Request(url, data=data, method=method)
        for k, v in self.headers.items():
            req.add_header(k, v)
        if body:
            req.add_header("Content-Type", "application/json")
        try:
            with request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"GitHub {method} {path} -> {e.code}: {body_text}")

    def _fetch_raw(self, raw_url: str) -> str:
        """download_url 같은 raw 파일 가져오기"""
        req = request.Request(raw_url)
        req.add_header("Authorization", f"token {self.token}")
        req.add_header("User-Agent", "fiveline-ai-remediation")
        with request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")

    # ─── 공개 메서드 ─────────────────────────────────────────────────────

    def fetch_terraform_files(self, base_branch: str, path_prefix: str) -> dict:
        """
        path_prefix 폴더의 모든 .tf 파일 내용을 dict 로 반환
        Returns: {"data_pipeline.tf": "...", "lambda.tf": "...", ...}
        """
        listing = self._request("GET", f"/contents/{path_prefix}?ref={base_branch}")
        tf_contents = {}
        for f in listing:
            if f["type"] == "file" and f["name"].endswith(".tf"):
                content = self._fetch_raw(f["download_url"])
                tf_contents[f["name"]] = content
        return tf_contents

    def get_branch_sha(self, branch: str) -> str:
        """브랜치의 최신 commit SHA"""
        ref = self._request("GET", f"/git/ref/heads/{parse.quote(branch, safe='')}")
        return ref["object"]["sha"]

    def create_branch(self, new_branch: str, base_sha: str):
        """새 브랜치 생성"""
        self._request("POST", "/git/refs", body={
            "ref": f"refs/heads/{new_branch}",
            "sha": base_sha,
        })

    def get_file_sha(self, path: str, branch: str) -> str:
        """파일의 현재 SHA (commit 시 필요)"""
        f = self._request("GET", f"/contents/{parse.quote(path)}?ref={parse.quote(branch, safe='')}")
        return f["sha"]

    def commit_file(self, path: str, content: str, branch: str, message: str, file_sha: str = None):
        """파일 수정 후 commit"""
        body = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if file_sha:
            body["sha"] = file_sha
        self._request("PUT", f"/contents/{parse.quote(path)}", body=body)

    def open_pr(self, title: str, head: str, base: str, body: str) -> str:
        """PR 생성 후 URL 반환"""
        pr = self._request("POST", "/pulls", body={
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": False,
        })
        return pr["html_url"]

    def add_labels(self, pr_number: int, labels: list):
        """PR 에 라벨 추가 (실패해도 무시)"""
        try:
            self._request("POST", f"/issues/{pr_number}/labels", body={"labels": labels})
        except Exception as e:
            print(f"라벨 추가 실패 (무시): {e}")

    # ─── 통합 — PR 한 번에 생성 ──────────────────────────────────────────

    def create_remediation_pr(
        self,
        base_branch: str,
        request_id: str,
        resource_id: str,
        action: str,
        change: dict,
        session_id: str,
    ) -> str:
        """
        Bedrock 이 생성한 change dict 로 새 브랜치·commit·PR 자동 생성

        change: {
            "files_changed": [
                {"filename": "data_pipeline.tf", "new_content": "...전체 내용..."}
            ],
            "impact_analysis": "...",
            "risk_level": "low|medium|high"
        }
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        new_branch = f"ai-remediation/{action}-{resource_id[:16]}-{timestamp}"

        # 1. 새 브랜치 생성
        base_sha = self.get_branch_sha(base_branch)
        self.create_branch(new_branch, base_sha)

        # 2. 각 파일 수정 commit
        for f in change["files_changed"]:
            filename = f["filename"]
            new_content = f["new_content"]
            file_path = f"terraform/jihoo/{filename}"  # 경로 prefix

            file_sha = self.get_file_sha(file_path, new_branch)
            self.commit_file(
                path=file_path,
                content=new_content,
                branch=new_branch,
                message=f"chore(ai): {action} {resource_id}",
                file_sha=file_sha,
            )

        # 3. PR 생성
        pr_body = self._build_pr_body(
            request_id=request_id,
            resource_id=resource_id,
            action=action,
            change=change,
            session_id=session_id,
        )
        pr_url = self.open_pr(
            title=f"🤖 [AI] {action} {resource_id}",
            head=new_branch,
            base=base_branch,
            body=pr_body,
        )

        # 4. 라벨 추가
        pr_number = int(pr_url.rsplit("/", 1)[-1])
        self.add_labels(pr_number, ["ai-generated", f"risk-{change.get('risk_level', 'unknown')}"])

        return pr_url

    def _build_pr_body(self, request_id, resource_id, action, change, session_id) -> str:
        files_list = "\n".join([f"- `terraform/jihoo/{f['filename']}`" for f in change.get("files_changed", [])])
        impact = change.get("impact_analysis", "분석 없음")
        risk = change.get("risk_level", "unknown").upper()
        now = datetime.now(timezone.utc).isoformat()

        return f"""## 🤖 AI 자동 생성 PR

> **이 PR은 AI 어시스턴트가 자동으로 생성했습니다. 머지 전 반드시 검토 부탁드립니다.**

### 변경 요청
- **자원 ID**: `{resource_id}`
- **액션**: `{action}`
- **요청 ID**: `{request_id}`

### 변경 파일
{files_list}

### 영향 분석
{impact}

### 위험도
**{risk}**

### 검토 체크리스트
- [ ] 자원 ID 정확한지 확인 (AWS 콘솔에서 검색)
- [ ] 의존성 영향 확인 (관련 IAM, Snapshot, ENI 등)
- [ ] 데이터 백업 필요 여부 확인
- [ ] 머지 후 `terraform plan` 결과 확인

---

생성 도구: LangGraph V2.1 + Bedrock Claude (자동)
챗봇 세션: `{session_id}`
생성 시각: {now}
"""
