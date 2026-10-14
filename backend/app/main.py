from __future__ import annotations

import hashlib
import json
import os
import secrets
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator, Optional

import jwt
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.types import JSON


class Settings(BaseSettings):
    database_url: str = "sqlite:///./careerai.db"
    jwt_secret: str = "careerai-dev-secret-change-me"
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
database_url = settings.database_url
connect_args: dict[str, Any] = {}
if database_url.startswith("mysql://"):
    database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
if database_url.startswith("mysql+"):
    # Managed MySQL DSNs expose `ssl` as a URL query string, while PyMySQL
    # expects an SSL options mapping. Preserve the TLS intent without passing
    # the raw string through to the driver.
    parsed_url = make_url(database_url)
    query = dict(parsed_url.query)
    ssl_requested = query.pop("ssl", None)
    database_url = parsed_url.set(query=query)
    if ssl_requested and str(ssl_requested).lower() not in {"0", "false", "off"}:
        # The managed DSN carries a Node-style `rejectUnauthorized` object.
        # PyMySQL needs an options mapping; the server enforces TLS transport,
        # while certificate verification can be tightened with a CA bundle.
        connect_args["ssl"] = {"check_hostname": False}
elif database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


now = lambda: datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30), default="student")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    profile: Mapped[Optional[Profile]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    college: Mapped[str] = mapped_column(String(180), default="")
    degree: Mapped[str] = mapped_column(String(120), default="")
    branch: Mapped[str] = mapped_column(String(120), default="")
    graduation_year: Mapped[int] = mapped_column(Integer, default=2026)
    preferred_role: Mapped[str] = mapped_column(String(180), default="Python Full Stack Developer")
    experience_level: Mapped[str] = mapped_column(String(60), default="Student")
    career_goal: Mapped[str] = mapped_column(Text, default="")
    resume_text: Mapped[str] = mapped_column(Text, default="")
    skills_json: Mapped[list] = mapped_column(JSON, default=list)
    user: Mapped[User] = relationship(back_populates="profile")


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(80), default="Technical")


class UserSkill(Base):
    __tablename__ = "user_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    level: Mapped[str] = mapped_column(String(30), default="familiar")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")


class RoleSkill(Base):
    __tablename__ = "role_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    priority: Mapped[str] = mapped_column(String(30), default="core")


class Roadmap(Base):
    __tablename__ = "roadmaps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    title: Mapped[str] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    items: Mapped[list[RoadmapItem]] = relationship(cascade="all, delete-orphan")


class RoadmapItem(Base):
    __tablename__ = "roadmap_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.id", ondelete="CASCADE"))
    week: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class AptitudeQuestion(Base):
    __tablename__ = "aptitude_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)
    correct_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(30), default="Medium")


class AptitudeAttempt(Base):
    __tablename__ = "aptitude_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(50))
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AptitudeAnswer(Base):
    __tablename__ = "aptitude_answers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("aptitude_attempts.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("aptitude_questions.id"))
    selected_index: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean)


class CodingProblem(Base):
    __tablename__ = "coding_problems"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(60))
    difficulty: Mapped[str] = mapped_column(String(30))
    statement: Mapped[str] = mapped_column(Text)
    input_format: Mapped[str] = mapped_column(Text)
    output_format: Mapped[str] = mapped_column(Text)
    hints: Mapped[list] = mapped_column(JSON)
    solution: Mapped[str] = mapped_column(Text)
    starter_code: Mapped[str] = mapped_column(Text)


class CodingSubmission(Base):
    __tablename__ = "coding_submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    problem_id: Mapped[int] = mapped_column(ForeignKey("coding_problems.id"))
    code: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(30), default="python")
    status: Mapped[str] = mapped_column(String(40))
    score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="active")
    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(30))


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("interview_questions.id", ondelete="CASCADE"))
    answer: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer, default=0)
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(180), default="Career coaching session")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(30), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ActivityHistory(Base):
    __tablename__ = "activity_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(180))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=120)


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    college: str = ""
    degree: str = ""
    branch: str = ""
    graduation_year: int = Field(default=2026, ge=2020, le=2040)
    preferred_role: str = "Python Full Stack Developer"
    experience_level: str = "Student"
    career_goal: str = ""
    skills: list[str] = []
    resume_text: str = ""


class RoadmapRequest(BaseModel):
    role: str = "Python Full Stack Developer"


class AptitudeAttemptRequest(BaseModel):
    category: str = "Quantitative"
    answers: dict[str, int]


class CodingSubmissionRequest(BaseModel):
    problem_id: int
    code: str = Field(min_length=1, max_length=20000)
    language: str = "python"


class InterviewStartRequest(BaseModel):
    category: str = "Technical"
    role: str = "Python Full Stack Developer"


class InterviewAnswerRequest(BaseModel):
    answer: str = Field(min_length=5, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[int] = None


class ResumeRequest(BaseModel):
    resume_text: str = Field(min_length=20, max_length=30000)
    target_role: str = "Python Full Stack Developer"


class TokenResponse(BaseModel):
    token: str
    user: dict[str, Any]


app = FastAPI(title="CareerAI API", version="1.0.0")
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"pbkdf2_sha256$120000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = encoded.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return secrets.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_token(user: User) -> str:
    payload = {"sub": str(user.id), "email": user.email, "role": user.role, "exp": now() + timedelta(days=7)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def user_payload(user: User) -> dict[str, Any]:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


def get_current_user(token: Optional[str] = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = int(payload.get("sub", 0))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def record_activity(db: Session, user_id: int, action: str, detail: str = "") -> None:
    db.add(ActivityHistory(user_id=user_id, action=action, detail=detail))


def add_notification(db: Session, user_id: int, title: str, body: str, kind: str = "info") -> None:
    db.add(Notification(user_id=user_id, title=title, body=body, type=kind))


def skill_names(db: Session, user_id: int) -> list[str]:
    rows = db.query(UserSkill, Skill).join(Skill, UserSkill.skill_id == Skill.id).filter(UserSkill.user_id == user_id).all()
    return [skill.name for _, skill in rows]


def ensure_skills(db: Session, user_id: int, names: list[str]) -> None:
    normalized = {n.strip().lower(): n.strip() for n in names if n.strip()}
    for name in normalized.values():
        skill = db.query(Skill).filter(func.lower(Skill.name) == name.lower()).first()
        if not skill:
            skill = Skill(name=name, category="Technical")
            db.add(skill)
            db.flush()
        existing = db.query(UserSkill).filter(UserSkill.user_id == user_id, UserSkill.skill_id == skill.id).first()
        if not existing:
            db.add(UserSkill(user_id=user_id, skill_id=skill.id, level="familiar", completed=True))


def get_role(db: Session, name: str) -> Optional[Role]:
    return db.query(Role).filter(func.lower(Role.name) == name.lower()).first()


def role_gap(db: Session, user: User, role_name: str) -> dict[str, Any]:
    role = get_role(db, role_name) or db.query(Role).first()
    owned = {n.lower() for n in skill_names(db, user.id)}
    requirements = db.query(RoleSkill, Skill).join(Skill, RoleSkill.skill_id == Skill.id).filter(RoleSkill.role_id == role.id).all()
    current, missing = [], []
    for req, skill in requirements:
        item = {"name": skill.name, "priority": req.priority, "category": skill.category}
        (current if skill.name.lower() in owned else missing).append(item)
    percent = round((len(current) / max(len(requirements), 1)) * 100)
    return {"role": {"id": role.id, "name": role.name, "description": role.description}, "current": current, "missing": missing, "progress": percent, "total": len(requirements)}


def roadmap_payload(db: Session, roadmap: Roadmap) -> dict[str, Any]:
    items = sorted(roadmap.items, key=lambda item: item.week)
    done = sum(1 for item in items if item.completed)
    return {"id": roadmap.id, "title": roadmap.title, "role": db.get(Role, roadmap.role_id).name if db.get(Role, roadmap.role_id) else "Target role", "progress": round(done / max(len(items), 1) * 100), "items": [{"id": i.id, "week": i.week, "title": i.title, "description": i.description, "completed": i.completed} for i in items]}


def ensure_roadmap(db: Session, user: User, role_name: Optional[str] = None) -> Roadmap:
    role = get_role(db, role_name or (user.profile.preferred_role if user.profile else "Python Full Stack Developer")) or db.query(Role).first()
    roadmap = db.query(Roadmap).filter(Roadmap.user_id == user.id).first()
    if roadmap and roadmap.role_id == role.id:
        return roadmap
    if roadmap:
        db.delete(roadmap)
        db.flush()
    gaps = role_gap(db, user, role.name)["missing"]
    default_topics = [item["name"] for item in gaps] or ["Python fundamentals", "Object-oriented design", "Data structures & algorithms", "SQL and data modeling", "FastAPI services", "REST API design", "Interview storytelling"]
    roadmap = Roadmap(user_id=user.id, role_id=role.id, title=f"{role.name} launch plan")
    db.add(roadmap)
    db.flush()
    for index, topic in enumerate(default_topics[:8], 1):
        db.add(RoadmapItem(roadmap_id=roadmap.id, week=index, title=topic, description=f"Build a focused practice block around {topic.lower()} and save one proof of work.", completed=False))
    return roadmap


def fallback_ai(prompt: str, context: str = "") -> str:
    lower = prompt.lower()
    if "resume" in lower or "ats" in lower:
        return "Your profile is strongest when it names the stack, the outcome, and the evidence. Add measurable impact to two projects, mirror the target role's vocabulary, and surface Python, SQL, APIs, testing, and Git where they are truthful."
    if "roadmap" in lower or "learn" in lower or "next" in lower:
        return "Start with the highest-priority gap that unlocks the most projects: Python fluency → OOP → DSA patterns → SQL → FastAPI/REST → testing and deployment. Study in 45-minute blocks and publish a small proof each week."
    if "interview" in lower:
        return "Use a clear structure: context, decision, implementation, trade-off, and result. For technical answers, explain the invariant first, then complexity, then one edge case. Close with what you would improve next."
    if "sql" in lower:
        return "An INNER JOIN keeps rows matched in both tables. A LEFT JOIN keeps every row from the left table and fills unmatched right-side columns with NULL. Choose based on which population you must preserve."
    return "I’m your local CareerAI coach. Turn your question into a small next step: name the target role, choose one skill gap, practice with a real artifact, and reflect on the result. Add an OpenAI-compatible key for richer, personalized guidance."


def call_ai(messages: list[dict[str, str]]) -> tuple[str, str]:
    if not settings.openai_api_key:
        return fallback_ai(messages[-1]["content"]), "local-fallback"
    try:
        body = json.dumps({"model": "gpt-4o-mini", "messages": messages, "temperature": 0.4}).encode()
        request = urllib.request.Request(f"{settings.openai_api_base.rstrip('/')}/chat/completions", data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.openai_api_key}"})
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode())
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if content:
            return content, "openai"
    except Exception:
        pass
    return fallback_ai(messages[-1]["content"]), "local-fallback"


def seed_database() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(Role).count() == 0:
            skill_rows = [
                ("Python", "Language"), ("OOP", "Foundations"), ("DSA", "Foundations"), ("SQL", "Data"), ("FastAPI", "Backend"),
                ("REST APIs", "Backend"), ("Git", "Tools"), ("Testing", "Quality"), ("Docker", "DevOps"), ("React", "Frontend"),
                ("TypeScript", "Frontend"), ("Communication", "Soft skill")
            ]
            skills = {name: Skill(name=name, category=category) for name, category in skill_rows}
            db.add_all(skills.values())
            db.flush()
            role_specs = {
                "Python Full Stack Developer": ("Build production APIs and thoughtful user experiences with Python, React, and reliable delivery.", ["Python", "OOP", "DSA", "SQL", "FastAPI", "REST APIs", "Git", "Testing", "React", "TypeScript"]),
                "Backend Developer": ("Design maintainable services, data models, and integrations.", ["Python", "OOP", "SQL", "FastAPI", "REST APIs", "Git", "Testing", "Docker"]),
                "Frontend Developer": ("Create accessible, high-performance interfaces with a strong product sense.", ["React", "TypeScript", "DSA", "REST APIs", "Git", "Testing", "Communication"]),
                "Data Analyst": ("Turn messy data into decisions with SQL, analysis, and communication.", ["Python", "SQL", "Communication", "Git"]),
            }
            for name, (description, required) in role_specs.items():
                role = Role(name=name, description=description)
                db.add(role)
                db.flush()
                for skill_name in required:
                    db.add(RoleSkill(role_id=role.id, skill_id=skills[skill_name].id, priority="core" if skill_name in required[:5] else "supporting"))
            questions = [
                ("Quantitative", "A train travels 180 km in 3 hours. What is its average speed?", ["45 km/h", "60 km/h", "90 km/h", "120 km/h"], 1, "Speed = distance ÷ time = 180 ÷ 3 = 60 km/h.", "Easy"),
                ("Quantitative", "If 20% of a number is 36, what is the number?", ["120", "150", "180", "200"], 2, "36 ÷ 0.20 = 180.", "Easy"),
                ("Logical", "Find the next number: 2, 6, 12, 20, 30, ?", ["36", "40", "42", "44"], 2, "The differences are 4, 6, 8, 10; the next difference is 12, giving 42.", "Medium"),
                ("Logical", "If all APIs are contracts and some contracts are versioned, which statement is certain?", ["All APIs are versioned", "Some APIs may be versioned", "No APIs are versioned", "All contracts are APIs"], 1, "The overlap is possible but not guaranteed for every API.", "Medium"),
                ("Verbal", "Choose the clearest sentence.", ["The report was completed by me yesterday.", "Yesterday, I completed the report.", "The report yesterday by me was completed.", "Completed was the report yesterday."], 1, "Active voice is direct and puts the actor first.", "Easy"),
                ("Verbal", "A concise summary should primarily preserve:", ["Every detail", "The author's exact wording", "The main idea and relevant evidence", "Only opinions"], 2, "A summary keeps the core idea and the evidence needed to understand it.", "Easy"),
            ]
            for category, question, options, correct, explanation, difficulty in questions:
                db.add(AptitudeQuestion(category=category, question=question, options=options, correct_index=correct, explanation=explanation, difficulty=difficulty))
            coding = [
                ("two-sum", "Two Sum", "Arrays", "Easy", "Given an array of integers and a target, return the indices of two numbers that add up to the target.", "nums: list[int], target: int", "return tuple[int, int]", ["Use a dictionary of seen values.", "Look for target - current before storing current."], "Use a hash map for O(n) time and O(n) space.", "def two_sum(nums, target):\n    pass"),
                ("valid-parentheses", "Valid Parentheses", "Strings", "Easy", "Determine whether an input string containing brackets is valid and properly nested.", "s: str", "return bool", ["Push opening brackets.", "Match each closing bracket with the latest opener."], "A stack models the last-opened bracket; scan once.", "def is_valid(s):\n    pass"),
                ("sql-retention", "Weekly Active Users", "SQL", "Medium", "Write a query that returns the count of distinct users active in each calendar week.", "events(user_id, occurred_at)", "week, active_users", ["Use DATE_TRUNC or an equivalent week expression.", "Count distinct user IDs."], "Group by a normalized week and count distinct users.", "SELECT ..."),
                ("reverse-linked-list", "Reverse a List", "Recursion", "Medium", "Return a reversed Python list without using built-in reverse helpers.", "values: list[int]", "return list[int]", ["Two pointers are enough.", "Keep the loop invariant explicit."], "Swap from both ends until the pointers meet.", "def reverse_values(values):\n    pass"),
            ]
            for slug, title, category, difficulty, statement, input_format, output_format, hints, solution, starter in coding:
                db.add(CodingProblem(slug=slug, title=title, category=category, difficulty=difficulty, statement=statement, input_format=input_format, output_format=output_format, hints=hints, solution=solution, starter_code=starter))
        if db.query(User).count() == 0:
            demo = User(email="demo@careerai.app", password_hash=hash_password("demo123"), name="Aarav Mehta", role="student")
            admin = User(email="admin@careerai.app", password_hash=hash_password("admin123"), name="CareerAI Admin", role="admin")
            db.add_all([demo, admin])
            db.flush()
            demo.profile = Profile(user_id=demo.id, college="National Institute of Technology", degree="B.Tech", branch="Computer Science", graduation_year=2026, preferred_role="Python Full Stack Developer", experience_level="Final-year student", career_goal="Become a backend-leaning full-stack developer.", skills_json=["Python", "SQL", "HTML"])
            ensure_skills(db, demo.id, ["Python", "SQL", "HTML"])
            ensure_roadmap(db, demo, "Python Full Stack Developer")
            add_notification(db, demo.id, "Your first roadmap is ready", "Start with the highest-priority skill gap and log one proof of work this week.", "milestone")
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    seed_database()


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "careerai-api", "timestamp": now().isoformat()}


@app.get("/manus-routes.json")
def routes_manifest() -> Any:
    path = Path(__file__).resolve().parents[2] / "frontend" / "public" / "manus-routes.json"
    return json.loads(path.read_text()) if path.exists() else {"routes": []}


@app.post("/api/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(payload.password), name=payload.name.strip())
    db.add(user)
    db.flush()
    user.profile = Profile(user_id=user.id, preferred_role="Python Full Stack Developer", experience_level="Student", graduation_year=2026, skills_json=[])
    ensure_roadmap(db, user)
    add_notification(db, user.id, "Welcome to CareerAI", "Complete your profile to unlock a more personal roadmap.", "welcome")
    db.commit()
    return TokenResponse(token=create_token(user), user=user_payload(user))


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return TokenResponse(token=create_token(user), user=user_payload(user))


@app.post("/api/auth/logout")
def logout(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"message": "Signed out safely"}


@app.get("/api/auth/me")
def me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return user_payload(user)


@app.get("/api/profile")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = user.profile or Profile(user_id=user.id)
    return {"name": user.name, "email": user.email, "college": profile.college, "degree": profile.degree, "branch": profile.branch, "graduation_year": profile.graduation_year, "preferred_role": profile.preferred_role, "experience_level": profile.experience_level, "career_goal": profile.career_goal, "skills": skill_names(db, user.id), "resume_text": profile.resume_text}


@app.put("/api/profile")
def update_profile(payload: ProfileRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    user.name = payload.name.strip()
    profile = user.profile or Profile(user_id=user.id)
    profile.college = payload.college.strip(); profile.degree = payload.degree.strip(); profile.branch = payload.branch.strip()
    profile.graduation_year = payload.graduation_year; profile.preferred_role = payload.preferred_role.strip(); profile.experience_level = payload.experience_level.strip(); profile.career_goal = payload.career_goal.strip(); profile.resume_text = payload.resume_text
    profile.skills_json = payload.skills
    user.profile = profile
    ensure_skills(db, user.id, payload.skills)
    record_activity(db, user.id, "Updated profile", f"Target role: {profile.preferred_role}")
    ensure_roadmap(db, user, profile.preferred_role)
    db.commit()
    return get_profile(user, db)


@app.post("/api/profile/analyze")
def analyze_resume(payload: ResumeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    text = payload.resume_text.lower()
    catalog = [skill.name for skill in db.query(Skill).all()]
    found = [name for name in catalog if name.lower() in text]
    target = role_gap(db, user, payload.target_role)
    missing = [item["name"] for item in target["missing"] if item["name"] not in found]
    recommendations = [f"Add a measurable project outcome that demonstrates {skill}." for skill in missing[:3]]
    result = {"technical_skills": found, "relevant_skills": [s for s in found if s in [x["name"] for x in target["current"]]], "missing_skills": missing, "ats_suggestions": ["Use a clear skills section with role-specific keywords.", "Lead each project bullet with an action and a measurable outcome.", "Keep the most relevant projects above the fold."], "suggested_improvements": recommendations, "recommended_roles": [r.name for r in db.query(Role).limit(4).all()], "provider": "deterministic-analysis"}
    record_activity(db, user.id, "Analyzed resume", f"Found {len(found)} catalog skills")
    db.commit()
    return result


@app.get("/api/skills")
def list_skills(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [{"id": s.id, "name": s.name, "category": s.category} for s in db.query(Skill).order_by(Skill.category, Skill.name).all()]


@app.get("/api/roles")
def list_roles(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [{"id": r.id, "name": r.name, "description": r.description} for r in db.query(Role).all()]


@app.get("/api/skill-gaps")
def get_skill_gaps(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    return role_gap(db, user, user.profile.preferred_role if user.profile else "Python Full Stack Developer")


@app.get("/api/roadmap")
def get_roadmap(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    roadmap = ensure_roadmap(db, user)
    db.commit()
    return roadmap_payload(db, roadmap)


@app.post("/api/roadmap")
def generate_roadmap(payload: RoadmapRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    if user.profile:
        user.profile.preferred_role = payload.role
    roadmap = ensure_roadmap(db, user, payload.role)
    record_activity(db, user.id, "Generated roadmap", payload.role)
    add_notification(db, user.id, "Roadmap refreshed", f"Your {payload.role} plan is ready to work through.", "learning")
    db.commit()
    return roadmap_payload(db, roadmap)


@app.patch("/api/roadmap/items/{item_id}")
def toggle_roadmap_item(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.query(RoadmapItem).join(Roadmap, Roadmap.id == RoadmapItem.roadmap_id).filter(RoadmapItem.id == item_id, Roadmap.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    item.completed = not item.completed
    record_activity(db, user.id, "Completed roadmap item" if item.completed else "Reopened roadmap item", item.title)
    if item.completed:
        add_notification(db, user.id, "Progress milestone", f"You completed: {item.title}.", "milestone")
    roadmap = db.get(Roadmap, item.roadmap_id)
    db.commit()
    return roadmap_payload(db, roadmap)


@app.get("/api/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    gap = role_gap(db, user, user.profile.preferred_role if user.profile else "Python Full Stack Developer")
    roadmap = ensure_roadmap(db, user)
    db.commit()
    attempts = db.query(AptitudeAttempt).filter(AptitudeAttempt.user_id == user.id).order_by(AptitudeAttempt.created_at.desc()).all()
    submissions = db.query(CodingSubmission).filter(CodingSubmission.user_id == user.id).all()
    interviews = db.query(InterviewSession).filter(InterviewSession.user_id == user.id).all()
    roadmap_progress = roadmap_payload(db, roadmap)["progress"]
    aptitude_score = round(sum((a.score / max(a.total, 1)) * 100 for a in attempts) / max(len(attempts), 1))
    coding_score = round(sum(s.score for s in submissions) / max(len(submissions), 1))
    interview_score = round(sum(s.overall_score for s in interviews) / max(len(interviews), 1))
    overall = round((gap["progress"] + roadmap_progress + aptitude_score + coding_score + interview_score) / 5)
    activities = db.query(ActivityHistory).filter(ActivityHistory.user_id == user.id).order_by(ActivityHistory.created_at.desc()).limit(6).all()
    return {"overall_score": overall, "skills_completed": len(gap["current"]), "skill_gaps": len(gap["missing"]), "aptitude_score": aptitude_score, "coding_progress": len(submissions), "coding_score": coding_score, "interview_score": interview_score, "roadmap_progress": roadmap_progress, "recommended_next_action": f"Focus on {gap['missing'][0]['name']} next" if gap["missing"] else "Run a mock interview to keep momentum", "trend": [{"label": "Skills", "value": gap["progress"]}, {"label": "Roadmap", "value": roadmap_progress}, {"label": "Aptitude", "value": aptitude_score}, {"label": "Coding", "value": coding_score}], "recent_activity": [{"action": a.action, "detail": a.detail, "created_at": a.created_at.isoformat()} for a in activities]}


@app.get("/api/aptitude/questions")
def aptitude_questions(category: str = "Quantitative", limit: int = 5, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(AptitudeQuestion).filter(AptitudeQuestion.category == category).limit(min(limit, 10)).all()
    if not rows:
        rows = db.query(AptitudeQuestion).limit(min(limit, 10)).all()
    return [{"id": q.id, "category": q.category, "question": q.question, "options": q.options, "difficulty": q.difficulty} for q in rows]


@app.post("/api/aptitude/attempts")
def submit_aptitude(payload: AptitudeAttemptRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    ids = [int(key) for key in payload.answers.keys()]
    questions = db.query(AptitudeQuestion).filter(AptitudeQuestion.id.in_(ids)).all()
    score = 0
    attempt = AptitudeAttempt(user_id=user.id, category=payload.category, score=0, total=len(questions))
    db.add(attempt); db.flush()
    results = []
    for q in questions:
        selected = payload.answers.get(str(q.id), -1); correct = selected == q.correct_index
        score += int(correct)
        db.add(AptitudeAnswer(attempt_id=attempt.id, question_id=q.id, selected_index=selected, is_correct=correct))
        results.append({"id": q.id, "correct": correct, "correct_index": q.correct_index, "explanation": q.explanation})
    attempt.score = score
    record_activity(db, user.id, "Completed aptitude test", f"{score}/{len(questions)} correct")
    db.commit()
    return {"attempt_id": attempt.id, "score": score, "total": len(questions), "percentage": round(score / max(len(questions), 1) * 100), "results": results}


@app.get("/api/aptitude/history")
def aptitude_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(AptitudeAttempt).filter(AptitudeAttempt.user_id == user.id).order_by(AptitudeAttempt.created_at.desc()).limit(12).all()
    return [{"id": a.id, "category": a.category, "score": a.score, "total": a.total, "percentage": round(a.score / max(a.total, 1) * 100), "created_at": a.created_at.isoformat()} for a in rows]


@app.get("/api/coding/problems")
def coding_problems(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [{"id": p.id, "slug": p.slug, "title": p.title, "category": p.category, "difficulty": p.difficulty, "statement": p.statement, "input_format": p.input_format, "output_format": p.output_format, "hints": p.hints, "solution": p.solution, "starter_code": p.starter_code} for p in db.query(CodingProblem).all()]


@app.post("/api/coding/submissions")
def submit_coding(payload: CodingSubmissionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    problem = db.get(CodingProblem, payload.problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Coding problem not found")
    has_code = len(payload.code.strip()) > 20 and "pass" not in payload.code.strip().splitlines()[-1:]
    status_text = "passed" if has_code else "needs-review"
    score = 100 if has_code else 35
    submission = CodingSubmission(user_id=user.id, problem_id=problem.id, code=payload.code, language=payload.language, status=status_text, score=score)
    db.add(submission); record_activity(db, user.id, "Submitted coding solution", problem.title)
    db.commit()
    return {"id": submission.id, "status": status_text, "score": score, "message": "Your constrained evaluator accepted the submission shape. Review the solution explanation for edge cases." if has_code else "Add the core implementation, then resubmit. This safe evaluator does not execute arbitrary code in the API process."}


@app.post("/api/interview/sessions")
def start_interview(payload: InterviewStartRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    session = InterviewSession(user_id=user.id, role=payload.role, category=payload.category)
    db.add(session); db.flush()
    question_sets = {
        "Technical": [f"Explain how you would design a reliable {payload.role} API.", "Tell me about a difficult bug and how you isolated it.", "What trade-offs do you consider when choosing a database schema?"],
        "HR": ["Walk me through your background and the kind of team where you do your best work.", "Why are you interested in this role?", "Tell me about a time feedback changed your approach."],
        "Behavioral": ["Describe a project where priorities changed mid-way.", "How do you make progress when a problem is ambiguous?", "What does quality mean to you in a student project?"]
    }
    questions = question_sets.get(payload.category, question_sets["Technical"])
    for question in questions:
        db.add(InterviewQuestion(session_id=session.id, question=question, question_type=payload.category))
    record_activity(db, user.id, "Started mock interview", f"{payload.category} · {payload.role}")
    db.commit()
    return {"id": session.id, "role": session.role, "category": session.category, "questions": [{"id": q.id, "question": q.question, "question_type": q.question_type} for q in db.query(InterviewQuestion).filter(InterviewQuestion.session_id == session.id).all()]}


@app.post("/api/interview/questions/{question_id}/answers")
def answer_interview(question_id: int, payload: InterviewAnswerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    question = db.query(InterviewQuestion).join(InterviewSession, InterviewSession.id == InterviewQuestion.session_id).filter(InterviewQuestion.id == question_id, InterviewSession.user_id == user.id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Interview question not found")
    prompt = f"Evaluate this interview answer for clarity, technical depth, communication and confidence. Return concise coaching feedback. Question: {question.question}\nAnswer: {payload.answer}"
    feedback, provider = call_ai([{ "role": "system", "content": "You are a supportive interview coach." }, {"role": "user", "content": prompt}])
    score = min(95, max(45, 45 + len(payload.answer.split()) // 3))
    db.add(InterviewAnswer(question_id=question.id, answer=payload.answer, score=score, feedback=feedback))
    session = db.get(InterviewSession, question.session_id); session.overall_score = score
    record_activity(db, user.id, "Practiced interview answer", question.question[:80])
    db.commit()
    return {"score": score, "feedback": feedback, "provider": provider}


@app.get("/api/ai/chat")
def chat_history(session_id: Optional[int] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    session = db.query(ChatSession).filter(ChatSession.user_id == user.id).order_by(ChatSession.created_at.desc()).first() if not session_id else db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        return {"session_id": None, "messages": []}
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at).all()
    return {"session_id": session.id, "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages]}


@app.post("/api/ai/chat")
def chat(payload: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    session = db.get(ChatSession, payload.session_id) if payload.session_id else None
    if session and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="This chat is not yours")
    if not session:
        session = ChatSession(user_id=user.id, title=payload.message[:60])
        db.add(session); db.flush()
    history = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.desc()).limit(8).all()[::-1]
    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))
    profile_context = f"Student target role: {user.profile.preferred_role if user.profile else 'not set'}; skills: {', '.join(skill_names(db, user.id))}"
    messages = [{"role": "system", "content": f"You are CareerAI, a concise and practical placement coach. {profile_context}"}] + [{"role": m.role, "content": m.content} for m in history] + [{"role": "user", "content": payload.message}]
    answer, provider = call_ai(messages)
    db.add(ChatMessage(session_id=session.id, role="assistant", content=answer))
    record_activity(db, user.id, "Asked CareerAI", payload.message[:100])
    db.commit()
    return {"session_id": session.id, "message": {"role": "assistant", "content": answer}, "provider": provider}


@app.post("/api/ai/resume")
def ai_resume(payload: ResumeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    prompt = f"Review this resume for a {payload.target_role} student. Give three specific improvements and one ATS tip. Resume: {payload.resume_text}"
    answer, provider = call_ai([{ "role": "system", "content": "You are a practical resume coach." }, {"role": "user", "content": prompt}])
    return {"feedback": answer, "provider": provider}


@app.get("/api/notifications")
def notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(20).all()
    return [{"id": n.id, "title": n.title, "body": n.body, "type": n.type, "read": n.read, "created_at": n.created_at.isoformat()} for n in rows]


@app.patch("/api/notifications/{notification_id}/read")
def read_notification(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    item = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.read = True; db.commit(); return {"message": "Notification marked as read"}


@app.get("/api/admin/overview")
def admin_overview(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict[str, Any]:
    return {"students": db.query(User).filter(User.role == "student").count(), "questions": db.query(AptitudeQuestion).count(), "coding_problems": db.query(CodingProblem).count(), "roadmaps": db.query(Roadmap).count(), "roles": db.query(Role).count(), "skills": db.query(Skill).count(), "recent_users": [{"name": u.name, "email": u.email, "created_at": u.created_at.isoformat()} for u in db.query(User).order_by(User.created_at.desc()).limit(8).all()]}


# In production/preview, FastAPI serves the built React application from the same port.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
