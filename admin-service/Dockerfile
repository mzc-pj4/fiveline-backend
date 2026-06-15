FROM node:20-slim AS frontend-builder
WORKDIR /admin-frontend
COPY --from=admin-frontend package.json ./
RUN npm install --ignore-scripts
COPY --from=admin-frontend . ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .
COPY --from=frontend-builder /admin-frontend/dist /app/static
EXPOSE 8004
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8004"]
