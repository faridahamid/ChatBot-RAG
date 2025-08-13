from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

class OrgCreate(BaseModel):
    name: str
    description: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = Field(pattern="^(super-admin|admin|user)$")
    organization_id: Optional[UUID] = None  # Optional for super-admin

class SuperAdminCreate(BaseModel):
    username: str
    password: str

class SuperAdminLogin(BaseModel):
    username: str
    password: str

class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    user_count: int = 0
    admin_count: int = 0

class UserResponse(BaseModel):
    id: UUID
    username: str
    role: str
    organization_id: UUID
    organization_name: str
    created_at: str


class UploadResponse(BaseModel):
    document_id: UUID
    chunks: int


class AskRequest(BaseModel):
    org_id: UUID
    user_id: UUID
    question: str

class AskResponse(BaseModel):
    answer: str
    

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"