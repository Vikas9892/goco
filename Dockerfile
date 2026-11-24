# Stage 1: build the React app
FROM node:22-alpine AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: API, serving the built UI from /static (one container, one origin, no CORS)
FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=ui /ui/dist ./static
EXPOSE 8000
# Shell form so ${PORT} expands: hosts like Railway inject it
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
