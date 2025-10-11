"""add users table for authentication

Revision ID: 002_add_users
Revises: 001_add_tenant_id_to_all_tables
Create Date: 2025-10-05 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '002_add_users'
down_revision = '001_add_tenant_id'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create users table for authentication
    
    Features:
    - UUID primary key
    - Multi-tenancy support (tenant_id)
    - Email + password authentication
    - Role-based access control
    - User profile and status fields
    - Timestamps and metadata
    """
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('last_login_at', sa.DateTime()),
        sa.Column('meta', sa.JSON()),
    )
    
    # Create indexes
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_tenant_email', 'users', ['tenant_id', 'email'])
    op.create_index('ix_users_tenant_role', 'users', ['tenant_id', 'role'])
    op.create_index('ix_users_active', 'users', ['is_active'])
    
    # Create foreign key
    op.create_foreign_key(
        'fk_users_tenant_id',
        'users', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )
    
    print("✅ Created users table with 5 indexes and 1 foreign key")


def downgrade():
    """
    Drop users table
    """
    # Drop foreign key
    op.drop_constraint('fk_users_tenant_id', 'users', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_users_active', 'users')
    op.drop_index('ix_users_tenant_role', 'users')
    op.drop_index('ix_users_tenant_email', 'users')
    op.drop_index('ix_users_email', 'users')
    op.drop_index('ix_users_tenant_id', 'users')
    
    # Drop table
    op.drop_table('users')
    
    print("✅ Dropped users table")
