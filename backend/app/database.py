
import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from pgvector.psycopg import register_vector

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True, # Check if the connection is alive before using it
    pool_size=5,        # The number of connections to keep in the pool
    max_overflow=10,    # The number of connections to allow in overflow, that is, connections that can be opened above and beyond the pool_size
)

# Register the pgvector extension for the connection
@event.listens_for(engine, "connect")
def register_pgvector(dbapi_connection, connection_record):
    register_vector(dbapi_connection)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# dependency injection with resource cleanup
# after the request session is closed -> its database connection can be returned to the pool
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
