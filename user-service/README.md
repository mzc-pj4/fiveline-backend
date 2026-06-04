# user-service

mzc-pj4 의 인증·사용자 마이크로서비스. 회원가입·로그인·JWT 발급 담당.


## 엔드포인트

- `POST /api/auth/signup` — 회원가입 (이메일·비밀번호·이름 → 토큰)
- `POST /api/auth/login` — 로그인 (이메일·비밀번호 → 토큰)
- `GET /api/health` — 헬스체크
- `GET /docs` — Swagger UI

## 스키마

`user_schema` 사용 (PG 공유 인스턴스 안의 분리된 namespace). 테이블: `users`.

## 마이그레이션

```bash
# 모델 변경 후 새 리비전 생성
alembic revision --autogenerate -m "describe change"

# 적용
alembic upgrade head
```

## 로컬 실행

```bash
# 레포 루트에서
docker compose -f apps/docker-compose.yml up user-service postgres
```

## 발생 이벤트

- `USER_SIGNUP`
- `USER_LOGIN`
- `USER_LOGIN_FAILED`



