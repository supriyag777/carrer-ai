# CareerAI API reference

All protected requests send `Authorization: Bearer <token>`. The frontend uses the same endpoints through its `/api` base path.

## Auth and profile

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Create a student account and return `{token,user}` |
| POST | `/api/auth/login` | Authenticate with email/password |
| POST | `/api/auth/logout` | Confirm sign-out for the current session |
| GET | `/api/auth/me` | Return the current user |
| GET/PUT | `/api/profile` | Read or update profile, target role, skills and resume text |
| POST | `/api/profile/analyze` | Analyze resume text for catalog skills, gaps, ATS suggestions and roles |
| GET | `/api/skills`, `/api/roles` | Read catalog data |

## Career plan

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/skill-gaps` | Compare current skills with the profile target role |
| GET/POST | `/api/roadmap` | Read or regenerate the personalized weekly roadmap |
| PATCH | `/api/roadmap/items/{id}` | Toggle a roadmap item and record activity/notification |
| GET | `/api/dashboard` | Aggregate readiness score, trend, activity, and next action |

## Practice and coaching

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/aptitude/questions?category=Quantitative&limit=5` | Load a practice sprint |
| POST | `/api/aptitude/attempts` | Grade and persist answers |
| GET | `/api/aptitude/history` | Read prior attempts |
| GET | `/api/coding/problems` | Load coding problems |
| POST | `/api/coding/submissions` | Store a constrained code evaluation result |
| POST | `/api/interview/sessions` | Generate role/category questions |
| POST | `/api/interview/questions/{id}/answers` | Store an answer and receive coaching feedback |
| GET/POST | `/api/ai/chat` | Read or append a persisted AI conversation |
| POST | `/api/ai/resume` | Request server-side AI resume feedback |

## Engagement and admin

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/notifications` | Load current-user notifications |
| PATCH | `/api/notifications/{id}/read` | Mark one notification as read |
| GET | `/api/admin/overview` | Admin-only content/student aggregates |
| GET | `/health` | Unauthenticated service health |
| GET | `/manus-routes.json` | Frontend route manifest |

Errors are JSON objects with a `detail` string. Validation failures use FastAPI's standard 422 response shape; authentication failures use 401 and admin authorization failures use 403.
