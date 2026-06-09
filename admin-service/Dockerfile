FROM node:20-slim AS frontend-builder
WORKDIR /admin-frontend
COPY admin-frontend/package.json ./
RUN npm install
COPY admin-frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .
COPY . .
COPY --from=frontend-builder /admin-frontend/dist /app/static
EXPOSE 8004
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8004"]
