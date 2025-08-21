# import bcrypt
# import uuid
# from fastapi import APIRouter, Depends, HTTPException, status, Form
# from sqlalchemy.orm import Session
# from typing import List
# from pydantic import BaseModel, Field
# from database import get_db
# from models import User, Organization, Document, Chat, ChatMessage, Feedback, SuperAdmin
# from schemas import OrgCreate, UserCreate, OrganizationResponse, UserResponse, SuperAdminCreate, SuperAdminLogin

# router = APIRouter(prefix="/admin", tags=["admin"])

# # Pydantic models for admin registration
# class AdminRegisterRequest(BaseModel):
#     username: str = Field(..., min_length=3, max_length=50)
#     password: str = Field(..., min_length=6, max_length=100)
#     organization_id: uuid.UUID

# class AdminRegisterResponse(BaseModel):
#     message: str
#     user_id: uuid.UUID
#     username: str
#     organization_name: str

# def hash_password(password: str) -> str:
#     """Hash a password using bcrypt"""
#     salt = bcrypt.gensalt()
#     hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
#     return hashed.decode('utf-8')

# def verify_password(password: str, hashed_password: str) -> bool:
#     """Verify a password against its hash"""
#     return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# @router.get("/organizations", response_model=List[OrganizationResponse])
# def get_organizations(db: Session = Depends(get_db)):
#     """Get all organizations for the dropdown menu"""
#     try:
#         organizations = db.query(Organization).all()
#         print(f"Found {len(organizations)} organizations in database")
        
#         result = [
#             OrganizationResponse(
#                 id=org.id,
#                 name=org.name,
#                 description=org.description
#             ) for org in organizations
#         ]
        
#         print(f"Returning {len(result)} organizations")
#         return result
        
#     except Exception as e:
#         print(f"Error in get_organizations: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Database error: {str(e)}"
#         )

# @router.post("/register", response_model=AdminRegisterResponse)
# def register_admin(
#     request: AdminRegisterRequest,
#     db: Session = Depends(get_db)
# ):
#     """Register a new admin user"""
    
#     # Check if username already exists
#     existing_user = db.query(User).filter(User.username == request.username).first()
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Username already exists"
#         )
    
#     # Verify organization exists
#     organization = db.query(Organization).filter(Organization.id == request.organization_id).first()
#     if not organization:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Organization not found"
#         )
    
#     # Hash the password
#     password_hash = hash_password(request.password)
    
#     # Create new admin user
#     new_admin = User(
#         username=request.username,
#         password_hash=password_hash,
#         role="admin",
#         organization_id=request.organization_id
#     )
    
#     try:
#         db.add(new_admin)
#         db.commit()
#         db.refresh(new_admin)
        
#         return AdminRegisterResponse(
#             message="Admin registered successfully",
#             user_id=new_admin.id,
#             username=new_admin.username,
#             organization_name=organization.name
#         )
    
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to register admin: {str(e)}"
#         )

# @router.post("/login")
# def admin_login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
#     """Login for admin users"""
    
#     # Find user by username
#     user = db.query(User).filter(User.username == username).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password"
#         )
    
#     # Verify password
#     if not verify_password(password, user.password_hash):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password"
#         )
    
#     # Check if user is admin
#     if user.role != "admin":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Access denied. Admin privileges required."
#         )
    
#     # Get organization info
#     organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
#     return {
#         "message": "Login successful",
#         "user_id": user.id,
#         "username": user.username,
#         "role": user.role,
#         "organization_id": user.organization_id,
#         "organization_name": organization.name if organization else None,
#         "created_at": user.created_at
#     }

# @router.get("/profile/{user_id}")
# def get_admin_profile(user_id: uuid.UUID, db: Session = Depends(get_db)):
#     """Get admin user profile"""
    
#     user = db.query(User).filter(User.id == user_id, User.role == "admin").first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Admin user not found"
#         )
    
#     organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
#     return {
#         "user_id": user.id,
#         "username": user.username,
#         "role": user.role,
#         "organization_id": user.organization_id,
#         "organization_name": organization.name if organization else None,
#         "created_at": user.created_at
#     }

# # User authentication endpoints
# class UserLoginRequest(BaseModel):
#     username: str
#     password: str
#     role: str = Field(..., pattern="^(admin|user)$")

# class CreateUserRequest(BaseModel):
#     username: str = Field(..., min_length=3, max_length=50)
#     password: str = Field(..., min_length=6, max_length=100)
#     role: str = Field(..., pattern="^(admin|user)$")
#     organization_id: uuid.UUID

# @router.post("/create-user", response_model=AdminRegisterResponse)
# def create_user(
#     request: CreateUserRequest,
#     db: Session = Depends(get_db)
# ):
#     """Create a new regular user - Only for existing admins"""
    
#     # Security: Admins can only create regular users, not other admins
#     if request.role != "user":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Admins can only create regular users for security reasons"
#         )
    
#     # Check if username already exists
#     existing_user = db.query(User).filter(User.username == request.username).first()
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Username already exists"
#         )
    
#     # Verify organization exists
#     organization = db.query(Organization).filter(Organization.id == request.organization_id).first()
#     if not organization:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Organization not found"
#         )
    
#     # Hash the password
#     password_hash = hash_password(request.password)
    
#     # Create new user (role is enforced to be "user")
#     new_user = User(
#         username=request.username,
#         password_hash=password_hash,
#         role="user",  # Force role to be user
#         organization_id=request.organization_id
#     )
    
#     try:
#         db.add(new_user)
#         db.commit()
#         db.refresh(new_user)
        
#         return AdminRegisterResponse(
#             message="User created successfully",
#             user_id=new_user.id,
#             username=new_user.username,
#             organization_name=organization.name
#         )
    
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create user: {str(e)}"
#         )

# @router.post("/user/login")
# def user_login(
#     request: UserLoginRequest,
#     db: Session = Depends(get_db)
# ):
#     """Login for users (both admin and regular users)"""
    
#     # Find user by username
#     user = db.query(User).filter(User.username == request.username).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password"
#         )
    
#     # Verify password
#     if not verify_password(request.password, user.password_hash):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password"
#         )
    
#     # Check if user role matches requested role
#     if user.role != request.role:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail=f"Access denied. You are registered as a {user.role}, not {request.role}."
#         )
    
#     # Get organization info
#     organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
#     return {
#         "message": "Login successful",
#         "user_id": user.id,
#         "username": user.username,
#         "role": user.role,
#         "organization_id": user.organization_id,
#         "organization_name": organization.name if organization else None,
#         "created_at": user.created_at
#     }

# @router.get("/organization-users/{org_id}")
# def get_organization_users(
#     org_id: uuid.UUID,
#     db: Session = Depends(get_db)
# ):
#     """Get all users in a specific organization"""
    
#     # Get organization
#     organization = db.query(Organization).filter(Organization.id == org_id).first()
#     if not organization:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Organization not found"
#         )
    
#     # Get all users in the organization
#     users = db.query(User).filter(User.organization_id == org_id).all()
    
#     # Return user list (without sensitive info like password_hash)
#     return [
#         {
#             "id": str(user.id),
#             "username": user.username,
#             "role": user.role,
#             "created_at": user.created_at
#         }
#         for user in users
#     ]

# @router.delete("/delete-user/{user_id}")
# def delete_user(
#     user_id: uuid.UUID,
#     db: Session = Depends(get_db)
# ):
#     """Delete a user from the organization and all related data"""
    
#     # Get the user to delete
#     user_to_delete = db.query(User).filter(User.id == user_id).first()
#     if not user_to_delete:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#             # Prevent deletion of the last admin in an organization
#         if user_to_delete.role == "admin":
#             admin_count = db.query(User).filter(
#                 User.organization_id == user_to_delete.organization_id,
#                 User.role == "admin"
#             ).count()
#             if admin_count <= 1:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Cannot delete the last admin in the organization"
#                 )
#             print(f"Admin deletion allowed - {admin_count} admins remain in organization")
#         else:
#             print(f"Regular user deletion - {user_to_delete.username}")
        
#         # Additional safety check: Ensure user is not trying to delete themselves
#         # This could be enhanced to check if the current admin is from the same organization
#         # For now, we'll just log a warning if someone tries to delete themselves
#         if user_to_delete.role == "admin":
#             print(f"Warning: Admin user {user_to_delete.username} is being deleted")
#             print(f"   Organization: {user_to_delete.organization_id}")
#             print(f"   Admin count in org: {admin_count}")
#             print(f"   Deletion timestamp: {user_to_delete.created_at}")
#             print(f"   User ID: {user_to_delete.id}")
#         else:
#             print(f"Regular user deletion - {user_to_delete.username}")
#             print(f"   Organization: {user_to_delete.organization_id}")
#             print(f"   User role: {user_to_delete.role}")
#             print(f"   User ID: {user_to_delete.id}")
    
#     try:
#         # First, manually delete all related data to ensure proper cleanup
#         # Delete all feedbacks related to user's chats
        
#         # Get all chats for this user
#         user_chats = db.query(Chat).filter(Chat.user_id == user_id).all()
#         print(f"Found {len(user_chats)} chats to delete for user {user_to_delete.username}")
        
#         if user_chats:
#             total_feedbacks = 0
#             total_messages = 0
            
#             for chat in user_chats:
#                 # Delete all feedbacks for this chat
#                 feedback_count = db.query(Feedback).filter(Feedback.chat_id == chat.id).count()
#                 if feedback_count > 0:
#                     db.query(Feedback).filter(Feedback.chat_id == chat.id).delete()
#                     total_feedbacks += feedback_count
#                     print(f"Deleted {feedback_count} feedbacks for chat {chat.id}")
                
#                 # Delete all messages for this chat
#                 message_count = db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).count()
#                 if message_count > 0:
#                     db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).delete()
#                     total_messages += message_count
#                     print(f"Deleted {message_count} messages for chat {chat.id}")
            
#             # Delete all chats for this user
#             db.query(Chat).filter(Chat.user_id == user_id).delete()
#             print(f"Deleted {len(user_chats)} chats for user {user_to_delete.username}")
#             print(f"Total feedbacks deleted: {total_feedbacks}")
#             print(f"Total messages deleted: {total_messages}")
#         else:
#             print(f"No chats found for user {user_to_delete.username}")
        
#         # Delete all documents uploaded by this user (set uploaded_by to NULL)
#         doc_count = db.query(Document).filter(Document.uploaded_by == user_id).count()
#         if doc_count > 0:
#             db.query(Document).filter(Document.uploaded_by == user_id).update({Document.uploaded_by: None})
#             print(f"Updated {doc_count} documents (set uploaded_by to NULL) for user {user_to_delete.username}")
#         else:
#             print(f"No documents found for user {user_to_delete.username}")
        
#         # Finally, delete the user
#         db.delete(user_to_delete)
#         db.commit()
#         #print(f"Successfully deleted user {user_to_delete.username} and all related data")
        
#         # Log the complete deletion summary
#         #print(f"  - Chats deleted: {len(user_chats)}")
#         # print(f"  - Documents updated (uploaded_by set to NULL): {doc_count}")
#         # print(f"  - User record deleted: {user_to_delete.username}")
#         # print(f"  - Organization ID: {user_to_delete.organization_id}")
#         # print(f"  - User role: {user_to_delete.role}")
#         # print(f"  - Deletion timestamp: {user_to_delete.created_at}")
#         # print(f"  - Total data records processed: {len(user_chats) + doc_count}")
#         # print(f"  - User ID: {user_to_delete.id}")
        
#         # Verify deletion was successful
#         verification = db.query(User).filter(User.id == user_id).first()
#         if verification:
#             print(f"  Warning: User {user_to_delete.username} still exists after deletion attempt")
#             print(f"   User ID: {verification.id}")
#             print(f"   Username: {verification.username}")
#         else:
#             print(f" Verification: User {user_to_delete.username} successfully removed from database")
        
#         # Final cleanup verification
#         remaining_chats = db.query(Chat).filter(Chat.user_id == user_id).count()
#         remaining_feedbacks = db.query(Feedback).filter(Feedback.user_id == user_id).count()
#         remaining_docs = db.query(Document).filter(Document.uploaded_by == user_id).count()
        
#         if remaining_chats > 0 or remaining_feedbacks > 0 or remaining_docs > 0:
#             print(f" Warning: Some data still exists for user {user_to_delete.username}")
#             print(f"   Remaining chats: {remaining_chats}")
#             print(f"   Remaining feedbacks: {remaining_feedbacks}")
#             print(f"   Remaining documents with user reference: {remaining_docs}")
#         else:
#             print(f"✅ All user data successfully cleaned up")
        
#         # Return success response with detailed information
#         return {
#             "message": f"User {user_to_delete.username} and all related data deleted successfully",
#             "deleted_data": {
#                 "chats_deleted": len(user_chats),
#                 "documents_updated": doc_count,
#                 "user_id": str(user_id),
#                 "username": user_to_delete.username,
#                 "organization_id": str(user_to_delete.organization_id),
#                 "total_records_processed": len(user_chats) + doc_count,
#                 "deletion_timestamp": str(user_to_delete.created_at)
#             }
#         }
    
#     except Exception as e:
#         db.rollback()
#         print(f"Error deleting user {user_to_delete.username}: {str(e)}")
        
#         # Provide more specific error messages for common issues
#         error_msg = str(e)
#         if "foreign key constraint" in error_msg.lower():
#             detail = "Cannot delete user due to remaining references. Please contact support."
#         elif "permission" in error_msg.lower():
#             detail = "Permission denied. You may not have the right to delete this user."
#         elif "unique constraint" in error_msg.lower():
#             detail = "Database constraint violation. Please contact support."
#         elif "connection" in error_msg.lower():
#             detail = "Database connection error. Please try again."
#         elif "timeout" in error_msg.lower():
#             detail = "Database operation timed out. Please try again."
#         elif "deadlock" in error_msg.lower():
#             detail = "Database deadlock detected. Please try again."
#         else:
#             detail = f"Failed to delete user: {error_msg}"
        
#         # Log the detailed error for debugging
#         print(f"Detailed error during user deletion: {error_msg}")
#         print(f"Error type: {type(e).name}")
#         print(f"User being deleted: {user_to_delete.username if user_to_delete else 'Unknown'}")
#         print(f"User ID: {user_id}")
        
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=detail
#         )

# @router.post("/super-admin/login")
# def super_admin_login(request: SuperAdminLogin, db: Session = Depends(get_db)):
#     """Login for super-admin users"""
    
#     # Find super-admin by username
#     super_admin = db.query(SuperAdmin).filter(SuperAdmin.username == request.username).first()
#     if not super_admin:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password"
#         )
    
#     # Verify password
#     if not verify_password(request.password, super_admin.password_hash):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid username or password"
#         )
    
#     return {
#         "message": "Login successful",
#         "user_id": super_admin.id,
#         "username": super_admin.username,
#         "role": "super-admin",
#         "created_at": super_admin.created_at
#     }

# @router.post("/super-admin/register")
# def register_super_admin(request: SuperAdminCreate, db: Session = Depends(get_db)):
#     """Register a new super-admin user (only for initial setup)"""
    
#     # Check if username already exists
#     existing_user = db.query(SuperAdmin).filter(SuperAdmin.username == request.username).first()
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Username already exists"
#         )
    
#     # Hash the password
#     password_hash = hash_password(request.password)
    
#     # Create new super-admin user
#     new_super_admin = SuperAdmin(
#         username=request.username,
#         password_hash=password_hash
#     )
    
#     try:
#         db.add(new_super_admin)
#         db.commit()
#         db.refresh(new_super_admin)
        
#         return {
#             "message": "Super-admin registered successfully",
#             "user_id": new_super_admin.id,
#             "username": new_super_admin.username
#         }
    
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to register super-admin: {str(e)}"
#         )

# @router.get("/super-admin/organizations", response_model=List[OrganizationResponse])
# def get_all_organizations(db: Session = Depends(get_db)):
#     """Get all organizations with user counts for super-admin"""
#     try:
#         organizations = db.query(Organization).all()
        
#         result = []
#         for org in organizations:
#             # Count users and admins in this organization
#             user_count = db.query(User).filter(User.organization_id == org.id).count()
#             admin_count = db.query(User).filter(
#                 User.organization_id == org.id, 
#                 User.role == "admin"
#             ).count()
            
#             result.append(OrganizationResponse(
#                 id=org.id,
#                 name=org.name,
#                 description=org.description,
#                 user_count=user_count,
#                 admin_count=admin_count
#             ))
        
#         return result
        
#     except Exception as e:
#         print(f"Error in get_all_organizations: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Database error: {str(e)}"
#         )

# @router.post("/super-admin/organizations", response_model=dict)
# def create_organization(payload: OrgCreate, db: Session = Depends(get_db)):
#     """Create a new organization - Super-admin only"""
#     try:
#         org = Organization(name=payload.name, description=payload.description)
#         db.add(org)
#         db.commit()
#         db.refresh(org)
#         return {"id": org.id, "name": org.name, "message": "Organization created successfully"}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to create organization: {str(e)}"
#         )

# @router.delete("/super-admin/organizations/{org_id}")
# def delete_organization(org_id: uuid.UUID, db: Session = Depends(get_db)):
#     """Delete an organization and all its data - Super-admin only"""
#     try:
#         org = db.query(Organization).filter(Organization.id == org_id).first()
#         if not org:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Organization not found"
#             )
        
#         # Delete the organization (cascade will handle related data)
#         db.delete(org)
#         db.commit()
        
#         return {"message": f"Organization '{org.name}' deleted successfully"}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete organization: {str(e)}"
#         )

# @router.get("/super-admin/organizations/{org_id}/users", response_model=List[UserResponse])
# def get_organization_users(org_id: uuid.UUID, db: Session = Depends(get_db)):
#     """Get all users in a specific organization for super-admin"""
#     try:
#         # Get organization
#         organization = db.query(Organization).filter(Organization.id == org_id).first()
#         if not organization:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Organization not found"
#             )
        
#         # Get all users in the organization
#         users = db.query(User).filter(User.organization_id == org_id).all()
        
#         # Return user list with organization name
#         return [
#             UserResponse(
#                 id=user.id,
#                 username=user.username,
#                 role=user.role,
#                 organization_id=user.organization_id,
#                 organization_name=organization.name,
#                 created_at=str(user.created_at)
#             )
#             for user in users
#         ]
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Database error: {str(e)}"
#         )

# @router.post("/super-admin/organizations/{org_id}/admins", response_model=dict)
# def add_admin_to_organization(
#     org_id: uuid.UUID, 
#     request: UserCreate, 
#     db: Session = Depends(get_db)
# ):
#     """Add an admin to an organization - Super-admin only"""
#     try:
#         # Verify organization exists
#         organization = db.query(Organization).filter(Organization.id == org_id).first()
#         if not organization:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Organization not found"
#             )
        
#         # Check if username already exists
#         existing_user = db.query(User).filter(User.username == request.username).first()
#         if existing_user:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Username already exists"
#             )
        
#         # Hash the password
#         password_hash = hash_password(request.password)
        
#         # Create new admin user
#         new_admin = User(
#             username=request.username,
#             password_hash=password_hash,
#             role="admin",
#             organization_id=org_id
#         )
        
#         db.add(new_admin)
#         db.commit()
#         db.refresh(new_admin)
        
#         return {
#             "message": "Admin added successfully",
#             "user_id": new_admin.id,
#             "username": new_admin.username,
#             "organization_name": organization.name
#         }
    
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to add admin: {str(e)}"
#         )

# @router.delete("/super-admin/users/{user_id}")
# def delete_user_super_admin(user_id: uuid.UUID, db: Session = Depends(get_db)):
#     """Delete a user from any organization - Super-admin only"""
#     try:
#         # Get the user to delete
#         user_to_delete = db.query(User).filter(User.id == user_id).first()
#         if not user_to_delete:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="User not found"
#             )
        
#         # Prevent deletion of the last admin in an organization
#         if user_to_delete.role == "admin":
#             admin_count = db.query(User).filter(
#                 User.organization_id == user_to_delete.organization_id,
#                 User.role == "admin"
#             ).count()
#             if admin_count <= 1:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail="Cannot delete the last admin in the organization"
#                 )
        
#         # Get all chats for this user
#         user_chats = db.query(Chat).filter(Chat.user_id == user_id).all()
        
#         if user_chats:
#             for chat in user_chats:
#                 # Delete all feedbacks for this chat
#                 db.query(Feedback).filter(Feedback.chat_id == chat.id).delete()
#                 # Delete all messages for this chat
#                 db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).delete()
            
#             # Delete all chats for this user
#             db.query(Chat).filter(Chat.user_id == user_id).delete()
        
#         # Update documents uploaded by this user (set uploaded_by to NULL)
#         db.query(Document).filter(Document.uploaded_by == user_id).update({Document.uploaded_by: None})
        
#         # Finally, delete the user
#         db.delete(user_to_delete)
#         db.commit()
        
#         return {
#             "message": f"User {user_to_delete.username} deleted successfully",
#             "deleted_data": {
#                 "chats_deleted": len(user_chats),
#                 "user_id": str(user_id),
#                 "username": user_to_delete.username,
#                 "organization_id": str(user_to_delete.organization_id)
#             }
#         }
    
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete user: {str(e)}"
#         )


import bcrypt
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from database import get_db
from models import User, Organization, Document, Chat, ChatMessage, Feedback, SuperAdmin
from schemas import OrgCreate, UserCreate, OrganizationResponse, UserResponse, SuperAdminCreate, SuperAdminLogin

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
        organizations = db.query(Organization).filter(Organization.is_active == True).all()
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
    organization = db.query(Organization).filter(Organization.id == request.organization_id, Organization.is_active == True).first()
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
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
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
    organization = db.query(Organization).filter(Organization.id == user.organization_id, Organization.is_active == True).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive"
        )
    
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
    
    user = db.query(User).filter(User.id == user_id, User.role == "admin", User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )
    
    organization = db.query(Organization).filter(Organization.id == user.organization_id, Organization.is_active == True).first()
    
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
    organization = db.query(Organization).filter(Organization.id == request.organization_id, Organization.is_active == True).first()
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
    """Login for users (admin or regular) with username and password only"""
    # Find user by username
    user = db.query(User).filter(User.username == request.username, User.is_active == True).first()
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

    # Ensure user's organization is active
    organization = db.query(Organization).filter(Organization.id == user.organization_id, Organization.is_active == True).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive"
        )

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
    organization = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Get all users in the organization
    users = db.query(User).filter(User.organization_id == org_id, User.is_active == True).all()
    
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
    """Delete a user from the organization and all related data"""
    
    # Get the user to delete
    user_to_delete = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
            # Prevent deletion of the last admin in an organization
        if user_to_delete.role == "admin":
            admin_count = db.query(User).filter(
                User.organization_id == user_to_delete.organization_id,
                User.role == "admin",
                User.is_active == True
            ).count()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last admin in the organization"
                )
            print(f"Admin deletion allowed - {admin_count} admins remain in organization")
        else:
            print(f"Regular user deletion - {user_to_delete.username}")
        
        # Additional safety check: Ensure user is not trying to delete themselves
        # This could be enhanced to check if the current admin is from the same organization
        # For now, we'll just log a warning if someone tries to delete themselves
        if user_to_delete.role == "admin":
            print(f"Warning: Admin user {user_to_delete.username} is being deleted")
            print(f"   Organization: {user_to_delete.organization_id}")
            print(f"   Admin count in org: {admin_count}")
            print(f"   Deletion timestamp: {user_to_delete.created_at}")
            print(f"   User ID: {user_to_delete.id}")
        else:
            print(f"Regular user deletion - {user_to_delete.username}")
            print(f"   Organization: {user_to_delete.organization_id}")
            print(f"   User role: {user_to_delete.role}")
            print(f"   User ID: {user_to_delete.id}")
    
    try:
        # Soft-delete: mark user as inactive
        user_to_delete.is_active = False
        db.commit()
        #print(f"Successfully deleted user {user_to_delete.username} and all related data")
        
        # Log the complete deletion summary
        #print(f"  - Chats deleted: {len(user_chats)}")
        # print(f"  - Documents updated (uploaded_by set to NULL): {doc_count}")
        # print(f"  - User record deleted: {user_to_delete.username}")
        # print(f"  - Organization ID: {user_to_delete.organization_id}")
        # print(f"  - User role: {user_to_delete.role}")
        # print(f"  - Deletion timestamp: {user_to_delete.created_at}")
        # print(f"  - Total data records processed: {len(user_chats) + doc_count}")
        # print(f"  - User ID: {user_to_delete.id}")
        
        # Verify deletion was successful
        verification = db.query(User).filter(User.id == user_id).first()
        if verification and verification.is_active:
            print(f"  Warning: User {user_to_delete.username} is still active after deletion attempt")
        else:
            print(f" Verification: User {user_to_delete.username} successfully deactivated")
        
        # Final cleanup verification
        return {
            "message": f"User {user_to_delete.username} deactivated successfully",
            "user_id": str(user_id),
            "username": user_to_delete.username,
            "organization_id": str(user_to_delete.organization_id)
        }
    
    except Exception as e:
        db.rollback()
        print(f"Error deleting user {user_to_delete.username}: {str(e)}")
        
        # Provide more specific error messages for common issues
        error_msg = str(e)
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
        
        # Log the detailed error for debugging
        print(f"Detailed error during user deletion: {error_msg}")
        print(f"Error type: {type(e).name}")
        print(f"User being deleted: {user_to_delete.username if user_to_delete else 'Unknown'}")
        print(f"User ID: {user_id}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

@router.post("/super-admin/login")
def super_admin_login(request: SuperAdminLogin, db: Session = Depends(get_db)):
    """Login for super-admin users"""
    
    # Find super-admin by username
    super_admin = db.query(SuperAdmin).filter(SuperAdmin.username == request.username).first()
    if not super_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(request.password, super_admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    return {
        "message": "Login successful",
        "user_id": super_admin.id,
        "username": super_admin.username,
        "role": "super-admin",
        "created_at": super_admin.created_at
    }

@router.post("/super-admin/register")
def register_super_admin(request: SuperAdminCreate, db: Session = Depends(get_db)):
    """Register a new super-admin user (only for initial setup)"""
    
    # Check if username already exists
    existing_user = db.query(SuperAdmin).filter(SuperAdmin.username == request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Hash the password
    password_hash = hash_password(request.password)
    
    # Create new super-admin user
    new_super_admin = SuperAdmin(
        username=request.username,
        password_hash=password_hash
    )
    
    try:
        db.add(new_super_admin)
        db.commit()
        db.refresh(new_super_admin)
        
        return {
            "message": "Super-admin registered successfully",
            "user_id": new_super_admin.id,
            "username": new_super_admin.username
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register super-admin: {str(e)}"
        )

@router.get("/super-admin/organizations", response_model=List[OrganizationResponse])
def get_all_organizations(db: Session = Depends(get_db)):
    """Get all organizations with user counts for super-admin"""
    try:
        organizations = db.query(Organization).filter(Organization.is_active == True).all()
        
        result = []
        for org in organizations:
            # Count users and admins in this organization
            user_count = db.query(User).filter(User.organization_id == org.id, User.is_active == True).count()
            admin_count = db.query(User).filter(
                User.organization_id == org.id, 
                User.role == "admin",
                User.is_active == True
            ).count()
            
            result.append(OrganizationResponse(
                id=org.id,
                name=org.name,
                description=org.description,
                user_count=user_count,
                admin_count=admin_count
            ))
        
        return result
        
    except Exception as e:
        print(f"Error in get_all_organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/super-admin/organizations", response_model=dict)
def create_organization(payload: OrgCreate, db: Session = Depends(get_db)):
    """Create a new organization - Super-admin only"""
    try:
        org = Organization(name=payload.name, description=payload.description)
        db.add(org)
        db.commit()
        db.refresh(org)
        return {"id": org.id, "name": org.name, "message": "Organization created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}"
        )

@router.delete("/super-admin/organizations/{org_id}")
def delete_organization(org_id: uuid.UUID, db: Session = Depends(get_db)):
    """Soft-delete an organization and deactivate all its users - Super-admin only"""
    try:
        org = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or already inactive"
            )
        # Deactivate all users in the organization
        db.query(User).filter(User.organization_id == org_id, User.is_active == True).update({User.is_active: False}, synchronize_session=False)
        # Deactivate organization
        org.is_active = False
        db.commit()
        return {"message": f"Organization '{org.name}' deactivated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate organization: {str(e)}"
        )

@router.get("/super-admin/organizations/{org_id}/users", response_model=List[UserResponse])
def get_organization_users(org_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get all users in a specific organization for super-admin"""
    try:
        # Get organization
        organization = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Get all users in the organization
        users = db.query(User).filter(User.organization_id == org_id, User.is_active == True).all()
        
        # Return user list with organization name
        return [
            UserResponse(
                id=user.id,
                username=user.username,
                role=user.role,
                organization_id=user.organization_id,
                organization_name=organization.name,
                created_at=str(user.created_at)
            )
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/super-admin/organizations/{org_id}/admins", response_model=dict)
def add_admin_to_organization(
    org_id: uuid.UUID, 
    request: UserCreate, 
    db: Session = Depends(get_db)
):
    """Add an admin to an organization - Super-admin only"""
    try:
        # Verify organization exists
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Check if username already exists
        existing_user = db.query(User).filter(User.username == request.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Hash the password
        password_hash = hash_password(request.password)
        
        # Create new admin user
        new_admin = User(
            username=request.username,
            password_hash=password_hash,
            role="admin",
            organization_id=org_id
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        return {
            "message": "Admin added successfully",
            "user_id": new_admin.id,
            "username": new_admin.username,
            "organization_name": organization.name
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add admin: {str(e)}"
        )

@router.delete("/super-admin/users/{user_id}")
def delete_user_super_admin(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Soft-delete a user from any organization - Super-admin only"""
    try:
        # Get the user to deactivate
        user_to_delete = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or already inactive"
            )
        
        # Prevent deactivation of the last active admin in an organization
        if user_to_delete.role == "admin":
            admin_count = db.query(User).filter(
                User.organization_id == user_to_delete.organization_id,
                User.role == "admin",
                User.is_active == True
            ).count()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the last admin in the organization"
                )
        
        # Soft delete: mark as inactive
        user_to_delete.is_active = False
        db.commit()
        
        return {
            "message": f"User {user_to_delete.username} deactivated successfully",
            "user_id": str(user_id),
            "username": user_to_delete.username,
            "organization_id": str(user_to_delete.organization_id)
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate user: {str(e)}"
        )