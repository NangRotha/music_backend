import os
import sys
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

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

# ==================== Turso (hosted SQLite) support ====================
# Turso (https://app.turso.tech) hosts a SQLite-compatible database so the app
# can run on Render's FREE plan without a paid Persistent Disk. The stock
# SQLAlchemy sqlite:// driver can only open a *local file*, which is why
# pointing it straight at a Turso URL fails - Turso needs its own libSQL
# driver + dialect (see requirements: sqlalchemy-libsql).
#
# Enable Turso by setting:
#   TURSO_DATABASE_URL = libsql://<database>-<organization>.turso.io
#                        (newer Turso consoles may show a "turso://" scheme -
#                         only the host name matters here, so both work)
#   TURSO_AUTH_TOKEN   = the database auth token from the Turso dashboard
# For convenience a DATABASE_URL that already starts with libsql:// or
# turso:// also activates Turso mode (an optional ?authToken=... query
# parameter in that URL is honoured as well).
turso_url_raw = (os.getenv("TURSO_DATABASE_URL") or "").strip()
if not turso_url_raw and db_url_env.startswith(("libsql://", "turso://")):
    turso_url_raw = db_url_env
TURSO_ACTIVE = bool(turso_url_raw)
turso_auth_token = ""

if TURSO_ACTIVE:
    _parsed = urlparse(turso_url_raw)
    _turso_host = (_parsed.netloc or _parsed.path).split("@")[-1]  # drop userinfo
    if not _turso_host:
        raise RuntimeError(
            f"Invalid TURSO_DATABASE_URL '{turso_url_raw}' - expected "
            "libsql://<db>-<org>.turso.io (or turso://<db>-<org>.turso.io)."
        )
    _query_params = parse_qs(_parsed.query)
    _token_from_url = (_query_params.get("authToken") or _query_params.get("auth_token") or [""])[0].strip()
    turso_auth_token = (os.getenv("TURSO_AUTH_TOKEN") or "").strip() or _token_from_url
    if not turso_auth_token:
        raise RuntimeError(
            "Turso is configured but no auth token was found. Set the "
            "TURSO_AUTH_TOKEN environment variable (or append "
            "?authToken=... to the Turso URL)."
        )
    # sqlalchemy-libsql registers the "sqlite+libsql" dialect for remote Turso.
    DATABASE_URL = f"sqlite+libsql://{_turso_host}?secure=true"

# ==================== Engine configuration ====================
# Local SQLite file  -> check_same_thread disabled (FastAPI threadpool).
# Turso (remote)     -> libSQL dialect + NullPool (don't pin a connection to a thread).
# PostgreSQL / MySQL -> pool_pre_ping so idle connections don't drop.
if TURSO_ACTIVE:
    try:
        import sqlalchemy_libsql  # noqa: F401  -- registers the "sqlite+libsql" dialect
    except ImportError as exc:
        raise RuntimeError(
            "TURSO_DATABASE_URL is set but the 'sqlalchemy-libsql' driver is not "
            "installed. Run: pip install 'sqlalchemy-libsql>=0.2.0' "
            "(requires Python <= 3.13; the project Docker image uses Python 3.11)."
        ) from exc
    engine = create_engine(
        DATABASE_URL,
        connect_args={"auth_token": turso_auth_token},
        poolclass=NullPool,  # remote DB: each connection is independent
    )
elif DATABASE_URL.startswith("sqlite"):
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

