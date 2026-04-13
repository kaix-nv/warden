from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from warden.state import Base

class GraphNode(Base):
    __tablename__ = "graph_nodes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    qualified_name = Column(String, nullable=False, unique=True)
    file_path = Column(String, nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=False)
    outgoing_edges = relationship("GraphEdge", foreign_keys="GraphEdge.source_id",
                                  cascade="all, delete-orphan", passive_deletes=True)
    incoming_edges = relationship("GraphEdge", foreign_keys="GraphEdge.target_id",
                                  cascade="all, delete-orphan", passive_deletes=True)
    annotations = relationship("GraphAnnotation", cascade="all, delete-orphan",
                               passive_deletes=True)

class GraphEdge(Base):
    __tablename__ = "graph_edges"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint("source_id", "target_id", "type"),)

class GraphAnnotation(Base):
    __tablename__ = "graph_annotations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    node_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source_commit = Column(String, nullable=True)
    source_pr = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)
