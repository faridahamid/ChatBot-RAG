# admin_auth.py
import os
import ssl
import smtplib
import secrets
import string
import uuid
from email.message import EmailMessage
from typing import List

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, Organization, Document, Chat, ChatMessage, Feedback, SuperAdmin
from schemas import (
    OrgCreate,
    UserCreate,
    OrganizationResponse,
    UserResponse,
    SuperAdminCreate,
    SuperAdminLogin,
)

router = APIRouter(prefix="/admin", tags=["admin"])

# =========================================================
# Utilities
# =========================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

def generate_temp_password(length: int = 12) -> str:
    """Generate a random strong temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))

# --- Email config ---
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@example.com")
# Used to create absolute links in emails
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

def send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Sends an HTML email using STARTTLS.
    Falls back to console if SMTP credentials are not configured.
    """
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        print(f"[EMAIL MOCK] To: {to_email}\nSubject: {subject}\n\n{html_body}")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content("This message contains HTML. Please view with an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

# =========================================================
# Pydantic models for admin registration / user creation
# =========================================================

class AdminRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=100)
    email: str | None = None
    organization_id: uuid.UUID

class AdminRegisterResponse(BaseModel):
    message: str
    user_id: uuid.UUID
    username: str
    organization_name: str

class UserLoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=100)
    role: str = Field(..., pattern="^(admin|user)$")
    organization_id: uuid.UUID
    email: str | None = None

# =========================================================
# Routes
# =========================================================

@router.get("/organizations", response_model=List[OrganizationResponse])
def get_organizations(db: Session = Depends(get_db)):
    """Get all active organizations (for dropdowns)."""
    try:
        organizations = db.query(Organization).filter(Organization.is_active == True).all()
        return [
            OrganizationResponse(
                id=org.id,
                name=org.name,
                description=org.description
            )
            for org in organizations
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/register", response_model=AdminRegisterResponse)
def register_admin(request: AdminRegisterRequest, db: Session = Depends(get_db)):
    """Register a new admin user."""
    # Username unique
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Org exists and active
    organization = (
        db.query(Organization)
        .filter(Organization.id == request.organization_id, Organization.is_active == True)
        .first()
    )
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Email unique (active)
    if request.email:
        dup = (
            db.query(User)
            .filter(User.email != None)
            .filter(User.is_active == True)
            .filter(User.email.ilike(request.email))
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="Email already exists")

    # Password: provided or temp
    plain_password = request.password or generate_temp_password()
    password_hash = hash_password(plain_password)

    # Create admin
    new_admin = User(
        username=request.username,
        password_hash=password_hash,
        role="admin",
        organization_id=request.organization_id,
        email=request.email,
        must_change_password=True if not request.password else False,
    )

    try:
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        # Email credentials if email provided
        if request.email:
            try:
                login_url = f"{APP_BASE_URL}/change-password?user_id={new_admin.id}"
                html = f"""
                <div style="font-family:Segoe UI,Roboto,Arial,sans-serif;font-size:14px;color:#111;">
                  <h2 style="margin:0 0 12px;">Your Admin Account</h2>
                  <p>Hello {request.username},</p>
                  <p>Your admin account has been created for <b>{organization.name}</b>.</p>
                  <p><b>Username:</b> {request.username}<br/>
                     <b>Temporary Password:</b> <code style="font-size:16px;">{plain_password}</code></p>
                  <p>Please <a href="{login_url}" style="color:#6c2bd9;">change your password</a> before your first login. After changing, sign in normally.</p>
                  <hr style="border:none;border-top:1px solid #eee;margin:16px 0;" />
                  <p style="color:#555;">If you didn’t expect this email, you can ignore it.</p>
                </div>
                """
                send_email(
                    to_email=request.email,
                    subject="Your Admin Account Credentials",
                    html_body=html,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")

        return AdminRegisterResponse(
            message="Admin registered successfully",
            user_id=new_admin.id,
            username=new_admin.username,
            organization_name=organization.name,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register admin: {str(e)}"
        )

@router.post("/login")
def admin_login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Login for admin users (Form data)."""
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")

    # Enforce password change if flagged
    if getattr(user, "must_change_password", False):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Invalid credentials. Check your email and change password.",
                "must_change_password": True,
                "user_id": str(user.id),
                "role": user.role,
            }
        )

    organization = (
        db.query(Organization)
        .filter(Organization.id == user.organization_id, Organization.is_active == True)
        .first()
    )
    if not organization:
        raise HTTPException(status_code=403, detail="Organization is inactive")

    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": organization.name if organization else None,
        "created_at": user.created_at,
    }

@router.get("/profile/{user_id}")
def get_admin_profile(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get admin user profile."""
    user = db.query(User).filter(User.id == user_id, User.role == "admin", User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    organization = db.query(Organization).filter(Organization.id == user.organization_id, Organization.is_active == True).first()

    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": organization.name if organization else None,
        "created_at": user.created_at,
    }

@router.post("/create-user", response_model=AdminRegisterResponse)
def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    """
    Create a new regular user. Admins can only create 'user' roles (security).
    """
    if request.role != "user":
        raise HTTPException(status_code=403, detail="Admins can only create regular users")

    # Unique username
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Org exists
    organization = (
        db.query(Organization)
        .filter(Organization.id == request.organization_id, Organization.is_active == True)
        .first()
    )
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Email unique (active)
    if request.email:
        dup = (
            db.query(User)
            .filter(User.email != None)
            .filter(User.is_active == True)
            .filter(User.email.ilike(request.email))
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="Email already exists")

    # Password: provided or temp
    plain_password = request.password or generate_temp_password()
    password_hash = hash_password(plain_password)

    # Create user (force role to 'user')
    new_user = User(
        username=request.username,
        password_hash=password_hash,
        role="user",
        organization_id=request.organization_id,
        email=request.email,
        must_change_password=True if not request.password else False,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        if request.email:
            try:
                login_url = f"{APP_BASE_URL}/change-password?user_id={new_user.id}"
                html = f"""
                <div style="font-family:Segoe UI,Roboto,Arial,sans-serif;font-size:14px;color:#111;">
                  <h2 style="margin:0 0 12px;">Your Account</h2>
                  <p>Hello {request.username},</p>
                  <p>Your account has been created for <b>{organization.name}</b>.</p>
                  <p><b>Username:</b> {request.username}<br/>
                     <b>Temporary Password:</b> <code style="font-size:16px;">{plain_password}</code></p>
                  <p>Please <a href="{login_url}" style="color:#6c2bd9;">change your password</a> before your first login. After changing, sign in normally.</p>
                  <hr style="border:none;border-top:1px solid #eee;margin:16px 0;" />
                  <p style="color:#555;">If you didn’t expect this email, you can ignore it.</p>
                </div>
                """
                send_email(
                    to_email=request.email,
                    subject="Your Account Credentials",
                    html_body=html,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")

        return AdminRegisterResponse(
            message="User created successfully",
            user_id=new_user.id,
            username=new_user.username,
            organization_name=organization.name,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )

@router.post("/user/login")
def user_login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login for users (JSON body).
    Returns 403 with must_change_password=True if a forced change is required.
    """
    user = db.query(User).filter(User.username == request.username, User.is_active == True).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if getattr(user, "must_change_password", False):
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Invalid credentials. Check your email and change password.",
                "must_change_password": True,
                "user_id": str(user.id),
                "role": user.role,
            }
        )

    organization = (
        db.query(Organization)
        .filter(Organization.id == user.organization_id, Organization.is_active == True)
        .first()
    )
    if not organization:
        raise HTTPException(status_code=403, detail="Organization is inactive")

    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": organization.name if organization else None,
        "created_at": user.created_at,
    }

@router.get("/organization-users/{org_id}")
def get_org_users_admin(org_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get all active users in a specific organization."""
    organization = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    users = db.query(User).filter(User.organization_id == org_id, User.is_active == True).all()
    return [
        {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "created_at": user.created_at,
        }
        for user in users
    ]

@router.delete("/delete-user/{user_id}")
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Soft-deactivate a user (cannot delete last admin in org)."""
    user_to_delete = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting the last admin of an org
    if user_to_delete.role == "admin":
        admin_count = (
            db.query(User)
            .filter(
                User.organization_id == user_to_delete.organization_id,
                User.role == "admin",
                User.is_active == True,
            )
            .count()
        )
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin in the organization")

    try:
        user_to_delete.is_active = False
        db.commit()

        verification = db.query(User).filter(User.id == user_id).first()
        if verification and verification.is_active:
            print(f"Warning: user {user_to_delete.username} still active after deletion attempt")
        else:
            print(f"Verification: user {user_to_delete.username} successfully deactivated")

        return {
            "message": f"User {user_to_delete.username} deactivated successfully",
            "user_id": str(user_id),
            "username": user_to_delete.username,
            "organization_id": str(user_to_delete.organization_id),
        }

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        # Provide a friendlier message for common DB errors
        if "foreign key constraint" in error_msg.lower():
            detail = "Cannot delete user due to remaining references. Please contact support."
        elif "permission" in error_msg.lower():
            detail = "Permission denied. You may not have the right to delete this user."
        elif "unique constraint" in error_msg.lower():
            detail = "Database constraint violation. Please contact support."
        elif "connection" in error_msg.lower():
            detail = "Database connection error. Please try again."
        elif "timeout" in error_msg.lower():
            detail = "Database operation timed out. Please try again."
        elif "deadlock" in error_msg.lower():
            detail = "Database deadlock detected. Please try again."
        else:
            detail = f"Failed to delete user: {error_msg}"

        print(f"Detailed error during user deletion: {error_msg}")
        print(f"Error type: {type(e).__name__}")
        print(f"User being deleted: {user_to_delete.username if user_to_delete else 'Unknown'}")
        print(f"User ID: {user_id}")

        raise HTTPException(status_code=500, detail=detail)

# ---------------- Super Admin ----------------

@router.post("/super-admin/login")
def super_admin_login(request: SuperAdminLogin, db: Session = Depends(get_db)):
    """Login for super-admin users (JSON)."""
    super_admin = db.query(SuperAdmin).filter(SuperAdmin.username == request.username).first()
    if not super_admin or not verify_password(request.password, super_admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "message": "Login successful",
        "user_id": super_admin.id,
        "username": super_admin.username,
        "role": "super-admin",
        "created_at": super_admin.created_at,
    }

@router.post("/super-admin/register")
def register_super_admin(request: SuperAdminCreate, db: Session = Depends(get_db)):
    """Register a new super-admin user (initial setup)."""
    existing_user = db.query(SuperAdmin).filter(SuperAdmin.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    password_hash = hash_password(request.password)
    new_super_admin = SuperAdmin(username=request.username, password_hash=password_hash)

    try:
        db.add(new_super_admin)
        db.commit()
        db.refresh(new_super_admin)
        return {
            "message": "Super-admin registered successfully",
            "user_id": new_super_admin.id,
            "username": new_super_admin.username,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to register super-admin: {str(e)}")

@router.get("/super-admin/organizations", response_model=List[OrganizationResponse])
def get_all_organizations(db: Session = Depends(get_db)):
    """Get all organizations with user/admin counts for super-admin."""
    try:
        organizations = db.query(Organization).filter(Organization.is_active == True).all()
        result = []
        for org in organizations:
            user_count = db.query(User).filter(User.organization_id == org.id, User.is_active == True).count()
            admin_count = db.query(User).filter(
                User.organization_id == org.id, User.role == "admin", User.is_active == True
            ).count()
            result.append(
                OrganizationResponse(
                    id=org.id,
                    name=org.name,
                    description=org.description,
                    user_count=user_count,
                    admin_count=admin_count,
                )
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/super-admin/organizations", response_model=dict)
def create_organization(payload: OrgCreate, db: Session = Depends(get_db)):
    """Create a new organization (super-admin)."""
    try:
        org = Organization(name=payload.name, description=payload.description)
        db.add(org)
        db.commit()
        db.refresh(org)
        return {"id": org.id, "name": org.name, "message": "Organization created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create organization: {str(e)}")

@router.delete("/super-admin/organizations/{org_id}")
def delete_organization(org_id: uuid.UUID, db: Session = Depends(get_db)):
    """Soft-delete an organization and deactivate all its users (super-admin)."""
    try:
        org = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found or already inactive")

        # Deactivate all users first
        db.query(User).filter(User.organization_id == org_id, User.is_active == True).update(
            {User.is_active: False}, synchronize_session=False
        )

        org.is_active = False
        db.commit()
        return {"message": f"Organization '{org.name}' deactivated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to deactivate organization: {str(e)}")

@router.get("/super-admin/organizations/{org_id}/users", response_model=List[UserResponse])
def get_organization_users_super_admin(org_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get all users in a specific organization (super-admin view)."""
    try:
        organization = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        users = db.query(User).filter(User.organization_id == org_id, User.is_active == True).all()

        return [
            UserResponse(
                id=user.id,
                username=user.username,
                role=user.role,
                organization_id=user.organization_id,
                organization_name=organization.name,
                created_at=str(user.created_at),
            )
            for user in users
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/super-admin/organizations/{org_id}/admins", response_model=dict)
def add_admin_to_organization(org_id: uuid.UUID, request: UserCreate, db: Session = Depends(get_db)):
    """Add an admin to an organization (super-admin)."""
    try:
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        existing_user = db.query(User).filter(User.username == request.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Email unique (active)
        if request.email:
            dup = (
                db.query(User)
                .filter(User.email != None)
                .filter(User.is_active == True)
                .filter(User.email.ilike(request.email))
                .first()
            )
            if dup:
                raise HTTPException(status_code=400, detail="Email already exists")

        plain_password = request.password or generate_temp_password()
        password_hash = hash_password(plain_password)

        new_admin = User(
            username=request.username,
            password_hash=password_hash,
            role="admin",
            organization_id=org_id,
            email=request.email,
            must_change_password=True if not request.password else False,
        )

        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        if request.email:
            try:
                login_url = f"{APP_BASE_URL}/change-password?user_id={new_admin.id}"
                html = f"""
                <div style="font-family:Segoe UI,Roboto,Arial,sans-serif;font-size:14px;color:#111;">
                  <h2 style="margin:0 0 12px;">Your Admin Account</h2>
                  <p>Hello {request.username},</p>
                  <p>Your admin account has been created for <b>{organization.name}</b>.</p>
                  <p><b>Username:</b> {request.username}<br/>
                     <b>Temporary Password:</b> <code style="font-size:16px;">{plain_password}</code></p>
                  <p>Please <a href="{login_url}" style="color:#6c2bd9;">change your password</a> before your first login. After changing, sign in normally.</p>
                  <hr style="border:none;border-top:1px solid #eee;margin:16px 0;" />
                  <p style="color:#555;">If you didn’t expect this email, you can ignore it.</p>
                </div>
                """
                send_email(
                    to_email=request.email,
                    subject="Your Admin Account Credentials",
                    html_body=html,
                )
            except Exception as e:
                print(f"Failed to send email: {e}")

        return {
            "message": "Admin added successfully",
            "user_id": new_admin.id,
            "username": new_admin.username,
            "organization_name": organization.name,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add admin: {str(e)}")

@router.delete("/super-admin/users/{user_id}")
def delete_user_super_admin(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Soft-deactivate a user (super-admin, any org)."""
    try:
        user_to_delete = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user_to_delete:
            raise HTTPException(status_code=404, detail="User not found or already inactive")

        # Prevent deactivation of last admin in an org
        if user_to_delete.role == "admin":
            admin_count = (
                db.query(User)
                .filter(
                    User.organization_id == user_to_delete.organization_id,
                    User.role == "admin",
                    User.is_active == True,
                )
                .count()
            )
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot deactivate the last admin in the organization")

        user_to_delete.is_active = False
        db.commit()

        return {
            "message": f"User {user_to_delete.username} deactivated successfully",
            "user_id": str(user_id),
            "username": user_to_delete.username,
            "organization_id": str(user_to_delete.organization_id),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to deactivate user: {str(e)}")
