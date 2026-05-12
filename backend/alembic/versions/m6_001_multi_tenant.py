"""multi-tenant migration

Revision ID: m6_001
Revises: 
Create Date: 2026-05-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'm6_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # 1. 创建 tenants 表
    op.create_table(
        'tenants',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('plan', sa.Enum('basic', 'pro', 'enterprise', name='tenant_plan_enum'), nullable=True),
        sa.Column('quota_monthly', sa.Integer(), nullable=True),
        sa.Column('quota_used', sa.Integer(), nullable=True),
        sa.Column('quota_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('settings', postgresql.JSONB(), nullable=True),
        sa.Column('contact_name', sa.String(length=100), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tenants')),
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)
    op.create_index('ix_tenants_plan_active', 'tenants', ['plan', 'is_active'])

    # 2. 修改 users 表：添加 tenant_id，更新 role enum
    # 2a. 先删除旧 enum 约束
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(20)")
    
    # 2b. 添加 tenant_id
    op.add_column('users', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_users_tenant_id_tenants', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    
    # 2c. 创建新 enum 并切换
    tenant_role_enum = postgresql.ENUM(
        'system_admin', 'tenant_admin', 'reviewer', 'user',
        name='user_role_enum',
        create_type=True,
    )
    tenant_role_enum.create(op.get_bind(), checkfirst=True)
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role_enum USING role::user_role_enum")

    # 3. works 表添加 tenant_id
    op.add_column('works', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_works_tenant_id_tenants', 'works', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_works_tenant_id', 'works', ['tenant_id'])

    # 4. tasks 表添加 tenant_id
    op.add_column('tasks', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_tasks_tenant_id_tenants', 'tasks', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_tasks_tenant_id', 'tasks', ['tenant_id'])

    # 5. results 表添加 tenant_id
    op.add_column('results', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_results_tenant_id_tenants', 'results', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_results_tenant_id', 'results', ['tenant_id'])


def downgrade() -> None:
    # 5. results 移除 tenant_id
    op.drop_index('ix_results_tenant_id', table_name='results')
    op.drop_constraint('fk_results_tenant_id_tenants', 'results', type_='foreignkey')
    op.drop_column('results', 'tenant_id')

    # 4. tasks 移除 tenant_id
    op.drop_index('ix_tasks_tenant_id', table_name='tasks')
    op.drop_constraint('fk_tasks_tenant_id_tenants', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'tenant_id')

    # 3. works 移除 tenant_id
    op.drop_index('ix_works_tenant_id', table_name='works')
    op.drop_constraint('fk_works_tenant_id_tenants', 'works', type_='foreignkey')
    op.drop_column('works', 'tenant_id')

    # 2. users 恢复旧 enum，移除 tenant_id
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(20)")
    op.drop_index('ix_users_tenant_id', table_name='users')
    op.drop_constraint('fk_users_tenant_id_tenants', 'users', type_='foreignkey')
    op.drop_column('users', 'tenant_id')
    # 恢复旧 enum
    old_role_enum = postgresql.ENUM(
        'admin', 'user', 'reviewer',
        name='user_role_enum',
        create_type=True,
    )
    old_role_enum.create(op.get_bind(), checkfirst=True)
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE user_role_enum USING role::user_role_enum")

    # 1. 删除 tenants 表
    op.drop_table('tenants')

    # 清理新 enum
    op.execute("DROP TYPE IF EXISTS tenant_plan_enum")
