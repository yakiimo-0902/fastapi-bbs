from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = "sqlite:///./bbs.db"  # 相対パス

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite のおまじない
)

SessionLocal = sessionmaker(
	autocommit=False, 
	autoflush=False, 
	bind=engine
)

Base = declarative_base()

# ============================
# DB セッション（依存性注入用）
# ============================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

