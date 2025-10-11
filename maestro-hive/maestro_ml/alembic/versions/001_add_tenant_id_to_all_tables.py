"""add tenant_id to all tables

Revision ID: 001_add_tenant_id
Revises:
Create Date: 2025-10-05

GAP FIX: Multi-Tenancy Database Integration (Task 2.1.2)
Adds tenant_id field to all tables for multi-tenancy support.

Migration Plan:
1. Create tenants table
2. Add tenant_id column to all tables (nullable initially)
3. Create default tenant for existing data
4. Backfill tenant_id for all existing records
5. Make tenant_id NOT NULL
6. Add foreign key constraints
7. Add indexes for performance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '001_add_tenant_id'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Upgrade database schema to support multi-tenancy
    """

    # ========================================================================
    # Step 1: Create tenants table
    # ========================================================================

    print("Creating tenants table...")

    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('max_users', sa.Integer(), default=10),
        sa.Column('max_projects', sa.Integer(), default=100),
        sa.Column('max_artifacts', sa.Integer(), default=1000),
        sa.Column('meta', sa.JSON())
    )

    # ========================================================================
    # Step 2: Create default tenant for existing data
    # ========================================================================

    print("Creating default tenant for existing data...")

    # Generate default tenant ID
    default_tenant_id = str(uuid.uuid4())

    # Insert default tenant
    op.execute(f"""
        INSERT INTO tenants (id, name, slug, created_at, is_active, max_users, max_projects, max_artifacts)
        VALUES (
            '{default_tenant_id}'::uuid,
            'Default Organization',
            'default',
            NOW(),
            true,
            1000,
            10000,
            100000
        )
    """)

    print(f"Default tenant created with ID: {default_tenant_id}")

    # ========================================================================
    # Step 3: Add tenant_id to projects table
    # ========================================================================

    print("Adding tenant_id to projects table...")

    # Add column (nullable initially)
    op.add_column('projects', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Backfill with default tenant
    op.execute(f"UPDATE projects SET tenant_id = '{default_tenant_id}'::uuid WHERE tenant_id IS NULL")

    # Make NOT NULL
    op.alter_column('projects', 'tenant_id', nullable=False)

    # Add foreign key
    op.create_foreign_key(
        'fk_projects_tenant',
        'projects', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add indexes
    op.create_index('ix_projects_tenant_id', 'projects', ['tenant_id'])
    op.create_index('ix_projects_tenant_created', 'projects', ['tenant_id', 'start_date'])
    op.create_index('ix_projects_tenant_name', 'projects', ['tenant_id', 'name'])

    # ========================================================================
    # Step 4: Add tenant_id to artifacts table
    # ========================================================================

    print("Adding tenant_id to artifacts table...")

    op.add_column('artifacts', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(f"UPDATE artifacts SET tenant_id = '{default_tenant_id}'::uuid WHERE tenant_id IS NULL")
    op.alter_column('artifacts', 'tenant_id', nullable=False)

    op.create_foreign_key(
        'fk_artifacts_tenant',
        'artifacts', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )

    op.create_index('ix_artifacts_tenant_id', 'artifacts', ['tenant_id'])
    op.create_index('ix_artifacts_tenant_created', 'artifacts', ['tenant_id', 'created_at'])
    op.create_index('ix_artifacts_tenant_type', 'artifacts', ['tenant_id', 'type'])
    op.create_index('ix_artifacts_tenant_active', 'artifacts', ['tenant_id', 'is_active'])

    # ========================================================================
    # Step 5: Add tenant_id to artifact_usage table
    # ========================================================================

    print("Adding tenant_id to artifact_usage table...")

    op.add_column('artifact_usage', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(f"UPDATE artifact_usage SET tenant_id = '{default_tenant_id}'::uuid WHERE tenant_id IS NULL")
    op.alter_column('artifact_usage', 'tenant_id', nullable=False)

    op.create_foreign_key(
        'fk_artifact_usage_tenant',
        'artifact_usage', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )

    op.create_index('ix_artifact_usage_tenant_id', 'artifact_usage', ['tenant_id'])
    op.create_index('ix_artifact_usage_tenant_used', 'artifact_usage', ['tenant_id', 'used_at'])

    # ========================================================================
    # Step 6: Add tenant_id to team_members table
    # ========================================================================

    print("Adding tenant_id to team_members table...")

    op.add_column('team_members', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(f"UPDATE team_members SET tenant_id = '{default_tenant_id}'::uuid WHERE tenant_id IS NULL")
    op.alter_column('team_members', 'tenant_id', nullable=False)

    op.create_foreign_key(
        'fk_team_members_tenant',
        'team_members', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )

    op.create_index('ix_team_members_tenant_id', 'team_members', ['tenant_id'])

    # ========================================================================
    # Step 7: Add tenant_id to process_metrics table
    # ========================================================================

    print("Adding tenant_id to process_metrics table...")

    op.add_column('process_metrics', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(f"UPDATE process_metrics SET tenant_id = '{default_tenant_id}'::uuid WHERE tenant_id IS NULL")
    op.alter_column('process_metrics', 'tenant_id', nullable=False)

    op.create_foreign_key(
        'fk_process_metrics_tenant',
        'process_metrics', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )

    op.create_index('ix_process_metrics_tenant_id', 'process_metrics', ['tenant_id'])
    op.create_index('ix_process_metrics_tenant_timestamp', 'process_metrics', ['tenant_id', 'timestamp'])
    op.create_index('ix_process_metrics_tenant_type', 'process_metrics', ['tenant_id', 'metric_type'])

    # ========================================================================
    # Step 8: Add tenant_id to predictions table
    # ========================================================================

    print("Adding tenant_id to predictions table...")

    op.add_column('predictions', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(f"UPDATE predictions SET tenant_id = '{default_tenant_id}'::uuid WHERE tenant_id IS NULL")
    op.alter_column('predictions', 'tenant_id', nullable=False)

    op.create_foreign_key(
        'fk_predictions_tenant',
        'predictions', 'tenants',
        ['tenant_id'], ['id'],
        ondelete='CASCADE'
    )

    op.create_index('ix_predictions_tenant_id', 'predictions', ['tenant_id'])
    op.create_index('ix_predictions_tenant_created', 'predictions', ['tenant_id', 'created_at'])

    print("✅ Multi-tenancy migration completed successfully!")
    print(f"   Default tenant ID: {default_tenant_id}")
    print("   All existing records assigned to default tenant")


def downgrade():
    """
    Rollback multi-tenancy changes
    """

    print("Rolling back multi-tenancy migration...")

    # Remove indexes and foreign keys from predictions
    op.drop_index('ix_predictions_tenant_created', 'predictions')
    op.drop_index('ix_predictions_tenant_id', 'predictions')
    op.drop_constraint('fk_predictions_tenant', 'predictions', type_='foreignkey')
    op.drop_column('predictions', 'tenant_id')

    # Remove indexes and foreign keys from process_metrics
    op.drop_index('ix_process_metrics_tenant_type', 'process_metrics')
    op.drop_index('ix_process_metrics_tenant_timestamp', 'process_metrics')
    op.drop_index('ix_process_metrics_tenant_id', 'process_metrics')
    op.drop_constraint('fk_process_metrics_tenant', 'process_metrics', type_='foreignkey')
    op.drop_column('process_metrics', 'tenant_id')

    # Remove indexes and foreign keys from team_members
    op.drop_index('ix_team_members_tenant_id', 'team_members')
    op.drop_constraint('fk_team_members_tenant', 'team_members', type_='foreignkey')
    op.drop_column('team_members', 'tenant_id')

    # Remove indexes and foreign keys from artifact_usage
    op.drop_index('ix_artifact_usage_tenant_used', 'artifact_usage')
    op.drop_index('ix_artifact_usage_tenant_id', 'artifact_usage')
    op.drop_constraint('fk_artifact_usage_tenant', 'artifact_usage', type_='foreignkey')
    op.drop_column('artifact_usage', 'tenant_id')

    # Remove indexes and foreign keys from artifacts
    op.drop_index('ix_artifacts_tenant_active', 'artifacts')
    op.drop_index('ix_artifacts_tenant_type', 'artifacts')
    op.drop_index('ix_artifacts_tenant_created', 'artifacts')
    op.drop_index('ix_artifacts_tenant_id', 'artifacts')
    op.drop_constraint('fk_artifacts_tenant', 'artifacts', type_='foreignkey')
    op.drop_column('artifacts', 'tenant_id')

    # Remove indexes and foreign keys from projects
    op.drop_index('ix_projects_tenant_name', 'projects')
    op.drop_index('ix_projects_tenant_created', 'projects')
    op.drop_index('ix_projects_tenant_id', 'projects')
    op.drop_constraint('fk_projects_tenant', 'projects', type_='foreignkey')
    op.drop_column('projects', 'tenant_id')

    # Drop tenants table
    op.drop_table('tenants')

    print("✅ Multi-tenancy migration rolled back successfully!")
