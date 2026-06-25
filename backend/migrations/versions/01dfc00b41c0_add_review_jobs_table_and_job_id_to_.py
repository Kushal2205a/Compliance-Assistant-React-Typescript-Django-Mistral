"""add review_jobs table and job_id to control_evaluations

Revision ID: 01dfc00b41c0
Revises: 4b6042d2a920
Create Date: 2026-06-25 22:54:45.124017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = '01dfc00b41c0'
down_revision: Union[str, Sequence[str], None] = '4b6042d2a920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('review_jobs',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('review_id', UUID(), nullable=False),
        sa.Column('checklist_id', UUID(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('total_controls', sa.Integer(), nullable=True),
        sa.Column('evaluated_controls', sa.Integer(), nullable=True),
        sa.Column('overall_percentage', sa.Float(), nullable=True),
        sa.Column('average_confidence', sa.Float(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ),
        sa.ForeignKeyConstraint(['checklist_id'], ['checklists.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('control_evaluations',
        sa.Column('job_id', UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_control_eval_job', 'control_evaluations',
        'review_jobs', ['job_id'], ['id']
    )
    op.drop_column('reviews', 'total_controls')
    op.drop_column('reviews', 'evaluated_controls')
    op.drop_column('reviews', 'overall_percentage')
    op.drop_column('reviews', 'average_confidence')
    op.drop_column('reviews', 'processing_time')


def downgrade() -> None:
    op.add_column('reviews',
        sa.Column('total_controls', sa.Integer(), nullable=True)
    )
    op.add_column('reviews',
        sa.Column('evaluated_controls', sa.Integer(), nullable=True)
    )
    op.add_column('reviews',
        sa.Column('overall_percentage', sa.Float(), nullable=True)
    )
    op.add_column('reviews',
        sa.Column('average_confidence', sa.Float(), nullable=True)
    )
    op.add_column('reviews',
        sa.Column('processing_time', sa.Float(), nullable=True)
    )
    op.drop_constraint('fk_control_eval_job', 'control_evaluations', type_='foreignkey')
    op.drop_column('control_evaluations', 'job_id')
    op.drop_table('review_jobs')
