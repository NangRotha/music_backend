import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load .env from backend folder and workspace root if present
load_dotenv(os.path.join(BASE_DIR, '.env'))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), '.env'))

db_url_env = os.getenv("DATABASE_URL", "").strip()

if not db_url_env:
    # Default to sqlite inside backend/ folder
    DEFAULT_DB_FILE = os.path.join(BASE_DIR, "music_store.db")
    DATABASE_URL = f"sqlite:///{DEFAULT_DB_FILE}"
elif db_url_env.startswith("postgres://"):
    # Fix Render's postgres:// scheme to postgresql:// for SQLAlchemy >= 1.4/2.0
    DATABASE_URL = db_url_env.replace("postgres://", "postgresql://", 1)
elif db_url_env.startswith("sqlite:///./"):
    # Convert relative sqlite path to absolute path inside BASE_DIR
    clean_path = db_url_env.replace("sqlite:///./backend/", "").replace("sqlite:///./", "")
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, clean_path)}"
elif db_url_env == "sqlite:///music_store.db":
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'music_store.db')}"
else:
    DATABASE_URL = db_url_env

# Engine configuration: conditional connect_args for SQLite vs pool pre-ping for PostgreSQL
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL / MySQL on Render
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

