# models.py
import uuid
import enum
from sqlalchemy import Column, Text, TIMESTAMP, ForeignKey, Enum, Integer, Boolean, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class RoleEnum(str, enum.Enum):
    super_admin = "super-admin"
    admin = "admin"
    user  = "user"



class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, server_default=text("true"), nullable=False)
    
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    email = Column(Text, nullable=False,unique=True)
    must_change_password = Column(Boolean, default=False, server_default=text("false"), nullable=False)
    
    role = Column(Text, nullable=False)  # values enforced by DB CHECK
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, server_default=text("true"), nullable=False)

    organization = relationship("Organization", back_populates="users")
    documents = relationship("Document", back_populates="uploader")
    chats = relationship("Chat", back_populates="user")


class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filename = Column(Text, nullable=False)
    filetype = Column(Text, nullable=False)  

    content_hash = Column(Text, nullable=True)
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="documents")
    uploader = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(512), nullable=False)  # pgvector column; dim must match your embed model
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")


class Chat(Base):
    __tablename__ = "chats"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="chat", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(Enum("user", "assistant", name="msg_role", create_type=False), nullable=False)
    content = Column(Text, nullable=False)
    citations = Column(JSONB)  
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")
    feedbacks = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=True)
    comment = Column(Text)
    seen_by_admin = Column(Boolean, default=False, server_default=text("false"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="feedbacks")
    message = relationship("ChatMessage", back_populates="feedbacks")
    user = relationship("User")


class SuperAdmin(Base):
    __tablename__ = "super_admins"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())