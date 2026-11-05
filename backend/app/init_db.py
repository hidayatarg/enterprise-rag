from sqlalchemy import text

from app.database import engine
from app.models import Base


def initialize_database():
    with engine.connect() as connection:
        version = connection.execute(
            text("""
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector'
            """)
        ).scalar_one_or_none()

        if version is None:
            raise RuntimeError(
                "pgvector extension is not enabled"
            )

        print(f"pgvector version: {version}")

    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully")


if __name__ == "__main__":
    initialize_database()
