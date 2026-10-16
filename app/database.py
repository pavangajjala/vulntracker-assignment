from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def search_scans_by_query(db, query: str, owner_id: int) -> list:
    # User input goes in as a bound parameter (:pattern), never pasted into the SQL
    # string, so it cannot change the query. Results are limited to the caller's own scans.
    sql = text(
        "SELECT id, title, description, severity, status, cve_id, "
        "affected_component, owner_id, created_at FROM scan_results "
        "WHERE owner_id = :owner_id "
        "AND (title LIKE :pattern OR description LIKE :pattern OR cve_id LIKE :pattern)"
    )
    result = db.execute(sql, {"owner_id": owner_id, "pattern": f"%{query}%"})
    return [dict(row._mapping) for row in result]