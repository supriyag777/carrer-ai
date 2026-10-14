FROM node:22-bookworm AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./frontend/
RUN npm --prefix frontend install --no-audit --no-fund
COPY frontend ./frontend
RUN npm --prefix frontend run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend ./backend
COPY database ./database
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
ENV PORT=3000
EXPOSE 3000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-3000}"]
