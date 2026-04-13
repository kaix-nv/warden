from datetime import datetime, timezone
from pathlib import Path
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from warden.state import Base
from warden.graph.models import GraphNode, GraphEdge, GraphAnnotation

@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_create_node(db_session):
    node = GraphNode(type="file", name="config.py", qualified_name="warden.config",
                     file_path="warden/config.py", line_start=1, line_end=50,
                     updated_at=datetime.now(timezone.utc))
    db_session.add(node)
    db_session.commit()
    assert node.id is not None

def test_create_edge(db_session):
    source = GraphNode(type="file", name="cli.py", qualified_name="warden.cli",
                       file_path="warden/cli.py", updated_at=datetime.now(timezone.utc))
    target = GraphNode(type="file", name="config.py", qualified_name="warden.config",
                       file_path="warden/config.py", updated_at=datetime.now(timezone.utc))
    db_session.add_all([source, target])
    db_session.flush()
    edge = GraphEdge(source_id=source.id, target_id=target.id, type="imports")
    db_session.add(edge)
    db_session.commit()
    assert edge.id is not None

def test_create_annotation(db_session):
    node = GraphNode(type="class", name="QuantizerConfig",
                     qualified_name="modelopt.quantization.QuantizerConfig",
                     file_path="modelopt/quantization/config.py",
                     updated_at=datetime.now(timezone.utc))
    db_session.add(node)
    db_session.flush()
    ann = GraphAnnotation(node_id=node.id, type="design_decision",
                          content="Redesigned in PR #1094", source_pr="1094",
                          created_at=datetime.now(timezone.utc))
    db_session.add(ann)
    db_session.commit()
    assert ann.id is not None

def test_cascade_delete_removes_edges(db_session):
    source = GraphNode(type="file", name="a.py", qualified_name="a",
                       file_path="a.py", updated_at=datetime.now(timezone.utc))
    target = GraphNode(type="file", name="b.py", qualified_name="b",
                       file_path="b.py", updated_at=datetime.now(timezone.utc))
    db_session.add_all([source, target])
    db_session.flush()
    edge = GraphEdge(source_id=source.id, target_id=target.id, type="imports")
    db_session.add(edge)
    db_session.commit()
    db_session.delete(source)
    db_session.commit()
    assert db_session.query(GraphEdge).count() == 0

def test_cascade_delete_removes_annotations(db_session):
    node = GraphNode(type="class", name="Foo", qualified_name="mod.Foo",
                     file_path="mod.py", updated_at=datetime.now(timezone.utc))
    db_session.add(node)
    db_session.flush()
    ann = GraphAnnotation(node_id=node.id, type="tech_debt", content="needs refactor",
                          created_at=datetime.now(timezone.utc))
    db_session.add(ann)
    db_session.commit()
    db_session.delete(node)
    db_session.commit()
    assert db_session.query(GraphAnnotation).count() == 0

def test_unique_edge_constraint(db_session):
    a = GraphNode(type="file", name="a.py", qualified_name="a",
                  file_path="a.py", updated_at=datetime.now(timezone.utc))
    b = GraphNode(type="file", name="b.py", qualified_name="b",
                  file_path="b.py", updated_at=datetime.now(timezone.utc))
    db_session.add_all([a, b])
    db_session.flush()
    db_session.add(GraphEdge(source_id=a.id, target_id=b.id, type="imports"))
    db_session.commit()
    from sqlalchemy.exc import IntegrityError
    db_session.add(GraphEdge(source_id=a.id, target_id=b.id, type="imports"))
    with pytest.raises(IntegrityError):
        db_session.commit()
