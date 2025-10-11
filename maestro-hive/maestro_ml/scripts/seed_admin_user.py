#!/usr/bin/env python3
"""
Seed default admin user for Maestro ML Platform

Creates an admin user in the database if it doesn't already exist.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from maestro_ml.models.database import User
from sqlalchemy import select
from enterprise.auth.password_hasher import PasswordHasher
import uuid

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://maestro:maestro@localhost:15432/maestro_ml")
DEFAULT_TENANT_ID = "371191e4-9748-4b2a-9c7f-2d986463afa7"

# Create engine
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

password_hasher = PasswordHasher()


async def seed_admin_user():
    """Create default admin user if it doesn't exist"""
    async with async_session() as session:
        # Check if admin user exists
        stmt = select(User).where(User.email == "admin@maestro.ml")
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"✅ Admin user already exists (ID: {existing_user.id})")
            print(f"   Email: {existing_user.email}")
            print(f"   Name: {existing_user.name}")
            print(f"   Role: {existing_user.role}")
            return
        
        # Create admin user
        admin_user = User(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(DEFAULT_TENANT_ID),
            email="admin@maestro.ml",
            password_hash=password_hasher.hash_password("admin123"),
            name="Admin User",
            role="admin",
            is_active=True,
            is_verified=True
        )
        
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)
        
        print("✅ Created default admin user:")
        print(f"   ID: {admin_user.id}")
        print(f"   Email: {admin_user.email}")
        print(f"   Name: {admin_user.name}")
        print(f"   Role: {admin_user.role}")
        print(f"   Password: admin123")
        print()
        print("⚠️  IMPORTANT: Change the password in production!")


if __name__ == "__main__":
    asyncio.run(seed_admin_user())
    print("\n✅ Database seeding complete!")
