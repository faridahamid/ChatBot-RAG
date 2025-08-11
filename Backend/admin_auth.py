import bcrypt
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from database import get_db
from models import User, Organization

router = APIRouter(prefix="/admin", tags=["admin"])

# Pydantic models for admin registration
class AdminRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    organization_id: uuid.UUID

class AdminRegisterResponse(BaseModel):
    message: str
    user_id: uuid.UUID
    username: str
    organization_name: str

class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str = None

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

@router.get("/organizations", response_model=List[OrganizationResponse])
def get_organizations(db: Session = Depends(get_db)):
    """Get all organizations for the dropdown menu"""
    try:
        organizations = db.query(Organization).all()
        print(f"Found {len(organizations)} organizations in database")
        
        result = [
            OrganizationResponse(
                id=org.id,
                name=org.name,
                description=org.description
            ) for org in organizations
        ]
        
        print(f"Returning {len(result)} organizations")
        return result
        
    except Exception as e:
        print(f"Error in get_organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/register", response_model=AdminRegisterResponse)
def register_admin(
    request: AdminRegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new admin user"""
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Verify organization exists
    organization = db.query(Organization).filter(Organization.id == request.organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Hash the password
    password_hash = hash_password(request.password)
    
    # Create new admin user
    new_admin = User(
        username=request.username,
        password_hash=password_hash,
        role="admin",
        organization_id=request.organization_id
    )
    
    try:
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        return AdminRegisterResponse(
            message="Admin registered successfully",
            user_id=new_admin.id,
            username=new_admin.username,
            organization_name=organization.name
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register admin: {str(e)}"
        )

@router.post("/login")
def admin_login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Login for admin users"""
    
    # Find user by username
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if user is admin
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )
    
    # Get organization info
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": organization.name if organization else None,
        "created_at": user.created_at
    }

@router.get("/profile/{user_id}")
def get_admin_profile(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get admin user profile"""
    
    user = db.query(User).filter(User.id == user_id, User.role == "admin").first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )
    
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": organization.name if organization else None,
        "created_at": user.created_at
    }

# User authentication endpoints
class UserLoginRequest(BaseModel):
    username: str
    password: str
    role: str = Field(..., pattern="^(admin|user)$")

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(..., pattern="^(admin|user)$")
    organization_id: uuid.UUID

@router.post("/create-user", response_model=AdminRegisterResponse)
def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db)
):
    """Create a new regular user - Only for existing admins"""
    
    # Security: Admins can only create regular users, not other admins
    if request.role != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins can only create regular users for security reasons"
        )
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Verify organization exists
    organization = db.query(Organization).filter(Organization.id == request.organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Hash the password
    password_hash = hash_password(request.password)
    
    # Create new user (role is enforced to be "user")
    new_user = User(
        username=request.username,
        password_hash=password_hash,
        role="user",  # Force role to be user
        organization_id=request.organization_id
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return AdminRegisterResponse(
            message="User created successfully",
            user_id=new_user.id,
            username=new_user.username,
            organization_name=organization.name
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.post("/user/login")
def user_login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """Login for users (both admin and regular users)"""
    
    # Find user by username
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if user role matches requested role
    if user.role != request.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. You are registered as a {user.role}, not {request.role}."
        )
    
    # Get organization info
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": organization.name if organization else None,
        "created_at": user.created_at
    }

@router.get("/organization-users/{org_id}")
def get_organization_users(
    org_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get all users in a specific organization"""
    
    # Get organization
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Get all users in the organization
    users = db.query(User).filter(User.organization_id == org_id).all()
    
    # Return user list (without sensitive info like password_hash)
    return [
        {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "created_at": user.created_at
        }
        for user in users
    ]

@router.delete("/delete-user/{user_id}")
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Delete a user from the organization"""
    
    # Get the user to delete
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # Delete the user
        db.delete(user_to_delete)
        db.commit()
        
        return {
            "message": f"User {user_to_delete.username} deleted successfully"
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
