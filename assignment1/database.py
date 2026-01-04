from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Using SQLite for this assignment.
# For PostgreSQL use: "postgresql+asyncpg://user:password@localhost/dbname"
DATABASE_URL = "sqlite+aiosqlite:///./users.db"

engine = create_async_engine(DATABASE_URL, echo=True)

# Create Async Session
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency to get DB session in routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
