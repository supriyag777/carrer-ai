# CareerAI architecture

CareerAI is a small full-stack application with a React/TypeScript client and a FastAPI service. The browser uses a same-origin `/api` client, so the frontend does not contain database credentials or AI provider keys. FastAPI validates every payload with Pydantic, resolves the current user from a signed JWT, and persists product data with SQLAlchemy.

## Runtime flow

1. Vite compiles `frontend/` into `frontend/dist`.
2. Uvicorn starts `backend.app.main:app` on `0.0.0.0:3000`.
3. FastAPI initializes the SQLite fallback or the `DATABASE_URL` database, creates the relational tables, and seeds only when the database is empty.
4. `/api/*` routes serve application data. `/health` exposes readiness. The remaining frontend paths are served by the built React SPA.
5. AI requests use the server-side OpenAI-compatible adapter when `OPENAI_API_KEY` is present; otherwise a separate deterministic fallback keeps the core flow usable and visibly reports `local-fallback` to the UI.

## Major boundaries

- **Identity:** `users`, `profiles`, JWT helpers, and protected dependencies.
- **Career signal:** `skills`, `user_skills`, `roles`, `role_skills`, profile analysis, skill gaps, and roadmap generation.
- **Practice:** aptitude attempts/answers, coding problems/submissions, and interview sessions/questions/answers.
- **Coaching:** chat sessions/messages and resume feedback via the AI adapter.
- **Engagement:** notifications and activity history feed the dashboard and next-action surfaces.
- **Admin:** role-protected aggregate view for students, practice content, roles, and skill coverage.

## Security notes

Passwords use salted PBKDF2-HMAC-SHA256 and are never returned to the client. JWTs expire after seven days and are validated on each protected request. CORS is environment-configurable. Coding submissions are handled by a constrained evaluator response rather than unrestricted execution inside the API process. AI credentials are read only on the server.
