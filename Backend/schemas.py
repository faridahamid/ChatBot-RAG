from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

class OrgCreate(BaseModel):
    name: str
    description: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = Field(pattern="^(admin|user)$")
    organization_id: UUID


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

