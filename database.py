from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

MYSQL_USER = os.getenv("MYSQLUSER")
MYSQL_PASSWORD = os.getenv("MYSQLPASSWORD")
MYSQL_HOST = os.getenv("MYSQLHOST")
MYSQL_PORT = os.getenv("MYSQLPORT", "3306")
MYSQL_DB = os.getenv("MYSQLDATABASE")

if not all([MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DB]):
    raise RuntimeError("One or more MySQL environment variables are missing")

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
