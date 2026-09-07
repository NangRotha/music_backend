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

# Render Persistent Disk mount (keeps SQLite database + uploads alive across
# deploys). When set, any repo-local / relative SQLite default is redirected
# onto the disk so a deploy can never silently point back at the ephemeral
# copy that Render rebuilds from the source tree.
RENDER_DISK_PATH = os.getenv("RENDER_DISK_PATH", "").strip()
if RENDER_DISK_PATH:
    RENDER_DISK_PATH = os.path.abspath(os.path.expanduser(RENDER_DISK_PATH))
    os.makedirs(RENDER_DISK_PATH, exist_ok=True)

# SQLite URLs that live inside the source tree (ephemeral on Render)
REPO_LOCAL_SQLITE_URLS = {
    "sqlite:///music_store.db",
    "sqlite:///./music_store.db",
    "sqlite:///./backend/music_store.db",
}

if not db_url_env:
    # Default to sqlite. On Render with a mounted disk this lands on the
    # persistent volume; locally it stays inside backend/ as before.
    if RENDER_DISK_PATH:
        DATABASE_URL = f"sqlite:///{os.path.join(RENDER_DISK_PATH, 'music_store.db')}"
    else:
        DEFAULT_DB_FILE = os.path.join(BASE_DIR, "music_store.db")
        DATABASE_URL = f"sqlite:///{DEFAULT_DB_FILE}"
elif db_url_env.startswith("postgres://"):
    # Fix Render's postgres:// scheme to postgresql:// for SQLAlchemy >= 1.4/2.0
    DATABASE_URL = db_url_env.replace("postgres://", "postgresql://", 1)
elif db_url_env.startswith("sqlite:///./"):
    # Convert a repo-relative sqlite path. If a persistent disk is mounted the
    # relative path is meaningless (fresh copy every deploy) -> use the disk.
    if RENDER_DISK_PATH:
        DATABASE_URL = f"sqlite:///{os.path.join(RENDER_DISK_PATH, 'music_store.db')}"
    else:
        clean_path = db_url_env.replace("sqlite:///./backend/", "").replace("sqlite:///./", "")
        DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, clean_path)}"
elif db_url_env == "sqlite:///music_store.db" or db_url_env in REPO_LOCAL_SQLITE_URLS:
    if RENDER_DISK_PATH:
        DATABASE_URL = f"sqlite:///{os.path.join(RENDER_DISK_PATH, 'music_store.db')}"
    else:
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

