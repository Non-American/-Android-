import os


def env_bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


DATABASE_URL = os.environ["DATABASE_URL"]
DATABASE_READ_URL = os.environ.get("DATABASE_READ_URL") or DATABASE_URL
DB_POOL_MAX = int(os.environ.get("DB_POOL_MAX", "10"))
PGBOUNCER = env_bool("PGBOUNCER", False)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
JWT_SECRET = os.environ["JWT_SECRET"]
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8000").rstrip("/")

# auto | hash | remote
EMBEDDINGS = os.environ.get("EMBEDDINGS", "auto")
EMBEDDER_URL = os.environ.get("EMBEDDER_URL", "http://embedder:8001")

MEDIA_DIR = os.environ.get("MEDIA_DIR", "./media")
MAX_PHOTOS = 6
MAX_PHOTO_BYTES = 8 * 1024 * 1024

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_STARTTLS = env_bool("SMTP_STARTTLS", False)
SMTP_FROM = os.environ.get("SMTP_FROM", "Orbita <no-reply@orbita.local>")

RATE_LIMITS = env_bool("RATE_LIMITS", True)
TRUST_PROXY = env_bool("TRUST_PROXY", False)
FEED_CACHE_TTL = int(os.environ.get("FEED_CACHE_TTL", "300"))
REPORTS_TO_HIDE = int(os.environ.get("REPORTS_TO_HIDE", "3"))
