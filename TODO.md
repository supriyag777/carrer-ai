# CareerAI Implementation Work Items

## 1. Full-stack foundation and route manifest
Create a clean project with `frontend/`, `backend/`, `database/`, and `docs/`; use React + TypeScript + Tailwind + React Router + TanStack Query + Recharts + Lucide on the frontend, FastAPI + Pydantic + SQLAlchemy + Alembic-compatible migrations on the backend, include pinned dependency manifests, `.env.example`, README, Docker/runtime files, and serve `GET /manus-routes.json` containing every frontend page route while excluding APIs and assets.

## 2. Relational schema and seed data
Implement relational models with foreign keys and ownership constraints for users, profiles, skills, user_skills, roles, role_skills, roadmaps, roadmap_items, aptitude_questions, aptitude_attempts, aptitude_answers, coding_problems, coding_submissions, interview_sessions, interview_questions, interview_answers, chat_sessions, chat_messages, notifications, and activity_history; add deterministic starter roles, skills, questions, coding problems, and roadmap data without overwriting later user edits.

## 3. Authentication and protected APIs
Implement registration, login, logout, JWT sessions, secure password hashing, protected routes, role-aware admin authorization, validation, CORS, basic auth/AI rate limiting, environment-based secrets, and structured error responses; expose `/api/auth/*`, `/api/users/*`, and `/api/profile/*` and keep authentication compatible with the managed preview without exposing secrets to the frontend.

## 4. Profile, resume analysis, skill gaps, roadmaps, and dashboard
Implement functional endpoints and UI for student profile fields, resume text/file metadata intake, technical/relevant/missing skills, ATS suggestions, recommended roles, target-role skill-gap comparison with priority and progress percentage, personalized weekly roadmaps with completion toggles, activity/notification recording, and dashboard aggregates for preparation score, completed skills, gaps, practice scores, roadmap progress, recent activity, and next action.

## 5. Aptitude and coding practice
Implement quantitative, logical, and verbal aptitude questions with multiple choices, timer, submission, score, answer explanations, and attempt history; implement coding problems for arrays, strings, searching, sorting, recursion, Python, and SQL with statement/input/output/difficulty/hints/solution explanation, a basic editor, safe constrained Python evaluation or a clearly labeled isolated evaluation mechanism, and stored submissions.

## 6. Mock interview and AI services
Implement technical, HR, and behavioral mock interview sessions generated from the target role, skills, and profile/project information; persist questions and submitted answers; evaluate correctness, clarity, technical depth, communication, confidence, and improvement suggestions. Add a server-side OpenAI-compatible adapter through environment variables plus a clearly separated deterministic local fallback for resume analysis, roadmap generation, interview generation/evaluation, and career chat, with stored chat history and no client-side secret exposure.

## 7. Responsive frontend experience
Implement the premium light SaaS landing page, authenticated shell, responsive navigation, dashboard charts, profile and analysis forms, skill-gap and roadmap views, aptitude timer and results, coding editor/submission flow, interview flow, AI assistant with chat history, notifications, and admin screens; every major action must connect to an API and provide loading, empty, error, and success states.

## 8. Admin, notifications, and documentation
Implement basic admin management for students, questions, coding problems, roadmaps, roles, and skill requirements with authorization; create useful notifications for learning tasks, pending roadmap items, new mock tests, and milestones; document architecture, setup, environment variables, SQLite/MySQL operation, migrations/seeding, API routes and payloads, testing, deployment, 30 project-specific technical questions, 15 HR/project questions, and how to present CareerAI in a Software Developer interview.

## 9. Verification and delivery
Run frontend typecheck/lint/build and backend compile/test checks, exercise the end-to-end frontend → API → database → AI/fallback paths, start on `0.0.0.0:3000`, verify `/`, `/health`, and `/manus-routes.json`, fix runtime and diagnostics issues, and create a canonical checkpoint after validation without enabling auto-publish.
