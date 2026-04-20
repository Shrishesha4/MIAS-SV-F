from sqlalchemy import Column, String, Integer, DateTime, Text
from datetime import datetime

from app.database import Base


class MrdQueryAudit(Base):
    """Audit log for every MRD query. Stored on OLTP DB (lightweight writes)."""
    __tablename__ = "mrd_query_audit"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    route = Column(String, nullable=False)
    filter_json = Column(Text, nullable=True)
    rows_returned = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    status = Column(String, default="ok")
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), index=True)
