-- CareerAI schema reference. The FastAPI startup uses SQLAlchemy create_all for local SQLite;
-- production deployments should run this migration through the selected migration runner.
-- Tables: users, profiles, skills, user_skills, roles, role_skills, roadmaps, roadmap_items,
-- aptitude_questions, aptitude_attempts, aptitude_answers, coding_problems, coding_submissions,
-- interview_sessions, interview_questions, interview_answers, chat_sessions, chat_messages,
-- notifications, activity_history.

CREATE TABLE IF NOT EXISTS schema_migrations (
  version VARCHAR(40) PRIMARY KEY,
  applied_at TIMESTAMP NOT NULL
);
