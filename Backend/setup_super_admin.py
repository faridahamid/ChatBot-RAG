#!/usr/bin/env python3
"""
Setup script to create the initial super-admin user.
Run this script once to set up your first super-admin account.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(_file_)))

from database import get_db, engine
from models import SuperAdmin, Base
from admin_auth import hash_password
from sqlalchemy.orm import Session

def create_super_admin(username: str, password: str):
    """Create a new super-admin user"""
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if super-admin already exists
        existing_admin = db.query(SuperAdmin).filter(SuperAdmin.username == username).first()
        if existing_admin:
            print(f"Super-admin user '{username}' already exists!")
            return False
        
        # Hash the password
        password_hash = hash_password(password)
        
        # Create new super-admin
        new_super_admin = SuperAdmin(
            username=username,
            password_hash=password_hash
        )
        
        db.add(new_super_admin)
        db.commit()
        db.refresh(new_super_admin)
        
        print(f"✅ Super-admin user '{username}' created successfully!")
        print(f"   User ID: {new_super_admin.id}")
        print(f"   Created at: {new_super_admin.created_at}")
        print("\nYou can now log in with these credentials at /login")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating super-admin: {str(e)}")
        return False
    finally:
        db.close()

def main():
    print("🚀 Super-Admin Setup Script")
    print("=" * 40)
    
    if len(sys.argv) != 3:
        print("Usage: python setup_super_admin.py <username> <password>")
        print("Example: python setup_super_admin.py admin password123")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    if len(password) < 6:
        print("❌ Password must be at least 6 characters long")
        sys.exit(1)
    
    print(f"Creating super-admin user: {username}")
    print(f"Password: {'*' * len(password)}")
    print()
    
    success = create_super_admin(username, password)
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("You can now start the application and log in as super-admin.")
    else:
        print("\n💥 Setup failed. Please check the error messages above.")
        sys.exit(1)

if _name_ == "_main_":
    main()