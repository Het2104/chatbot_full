"""
Create first admin user for the system.

Run this script after running the database migration to create
an admin account for accessing admin-only features.
"""

from database import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password

def create_admin():
    """Create the first admin user."""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == "admin@example.com").first()
        if existing_admin:
            print("❌ Admin user already exists!")
            print(f"   Email: {existing_admin.email}")
            print(f"   Username: {existing_admin.username}")
            return
        
        # Create admin user
        admin = User(
            email="admin@example.com",
            username="admin",
            password_hash=hash_password("admin123"),
            full_name="System Administrator",
            role="admin",
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ Admin user created successfully!")
        print(f"   Email: {admin.email}")
        print(f"   Username: {admin.username}")
        print(f"   Password: admin123")
        print(f"   Role: {admin.role}")
        print("\n⚠️  IMPORTANT: Change the password after first login!")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
