import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


class CommitRecord(Base):
    __tablename__ = "commits_processed"
    hash = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    files_changed = Column(Text, nullable=False, default="[]")
    understand_done = Column(Boolean, nullable=False, default=False)
    review_done = Column(Boolean, nullable=False, default=False)


class ReviewRecord(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_hash = Column(String, nullable=False)
    issue_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")
    pr_url = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class StateManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

    def initialize(self):
        Base.metadata.create_all(self.engine)

    def record_commit(self, hash: str, timestamp: datetime, files_changed: list[str]):
        with Session(self.engine) as session:
            existing = session.get(CommitRecord, hash)
            if existing:
                return
            record = CommitRecord(
                hash=hash,
                timestamp=timestamp,
                files_changed=json.dumps(files_changed),
            )
            session.add(record)
            session.commit()

    def get_commit(self, hash: str) -> dict | None:
        with Session(self.engine) as session:
            record = session.get(CommitRecord, hash)
            if record is None:
                return None
            return {
                "hash": record.hash,
                "timestamp": record.timestamp,
                "files_changed": json.loads(record.files_changed),
                "understand_done": record.understand_done,
                "review_done": record.review_done,
            }

    def mark_commit_understood(self, hash: str):
        with Session(self.engine) as session:
            record = session.get(CommitRecord, hash)
            record.understand_done = True
            session.commit()

    def mark_commit_reviewed(self, hash: str):
        with Session(self.engine) as session:
            record = session.get(CommitRecord, hash)
            record.review_done = True
            session.commit()

    def get_last_processed_hash(self) -> str | None:
        with Session(self.engine) as session:
            record = (
                session.query(CommitRecord)
                .order_by(CommitRecord.timestamp.desc())
                .first()
            )
            return record.hash if record else None

    def record_review(
        self,
        commit_hash: str,
        issue_type: str,
        description: str,
        pr_url: str | None,
    ):
        with Session(self.engine) as session:
            record = ReviewRecord(
                commit_hash=commit_hash,
                issue_type=issue_type,
                description=description,
                pr_url=pr_url,
            )
            session.add(record)
            session.commit()

    def get_reviews(self, status: str | None = None) -> list[dict]:
        with Session(self.engine) as session:
            query = session.query(ReviewRecord)
            if status:
                query = query.filter(ReviewRecord.status == status)
            return [
                {
                    "id": r.id,
                    "commit_hash": r.commit_hash,
                    "issue_type": r.issue_type,
                    "description": r.description,
                    "status": r.status,
                    "pr_url": r.pr_url,
                    "created_at": r.created_at,
                }
                for r in query.all()
            ]

    def update_review_status(self, review_id: int, status: str):
        with Session(self.engine) as session:
            record = session.get(ReviewRecord, review_id)
            record.status = status
            session.commit()

    def get_stats(self) -> dict:
        with Session(self.engine) as session:
            total = session.query(CommitRecord).count()
            understood = (
                session.query(CommitRecord)
                .filter(CommitRecord.understand_done == True)  # noqa: E712
                .count()
            )
            pending = (
                session.query(ReviewRecord)
                .filter(ReviewRecord.status == "pending")
                .count()
            )
            accepted = (
                session.query(ReviewRecord)
                .filter(ReviewRecord.status == "accepted")
                .count()
            )
            declined = (
                session.query(ReviewRecord)
                .filter(ReviewRecord.status == "declined")
                .count()
            )
            return {
                "commits_total": total,
                "commits_understood": understood,
                "reviews_pending": pending,
                "reviews_accepted": accepted,
                "reviews_declined": declined,
            }
