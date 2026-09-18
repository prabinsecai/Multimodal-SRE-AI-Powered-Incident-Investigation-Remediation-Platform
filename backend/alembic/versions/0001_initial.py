"""Create MultiModal-SRE schema with explicit DDL.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(30), nullable=False, server_default='VIEWER'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # 2. services
    op.create_table(
        'services',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('environment', sa.String(50), nullable=False, server_default='production'),
        sa.Column('owner', sa.String(100), nullable=False, server_default='sre-team'),
        sa.Column('status', sa.String(30), nullable=False, server_default='healthy'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_services_name', 'services', ['name'])

    # 3. incidents
    op.create_table(
        'incidents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('service_id', sa.Integer(), sa.ForeignKey('services.id', ondelete='CASCADE'), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='SEV-2'),
        sa.Column('status', sa.String(30), nullable=False, server_default='OPEN'),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_incidents_service_id', 'incidents', ['service_id'])
    op.create_index('ix_incidents_status', 'incidents', ['status'])

    # 4. incident_events
    op.create_table(
        'incident_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(80), nullable=False),
        sa.Column('source', sa.String(80), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_incident_events_incident_id', 'incident_events', ['incident_id'])

    # 5. logs
    op.create_table(
        'logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('service', sa.String(100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('level', sa.String(20), nullable=False, server_default='INFO'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('template', sa.Text(), nullable=True),
        sa.Column('trace_id', sa.String(100), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=True),
    )
    op.create_index('ix_logs_service', 'logs', ['service'])
    op.create_index('ix_logs_timestamp', 'logs', ['timestamp'])
    op.create_index('ix_logs_service_time', 'logs', ['service', 'timestamp'])

    # 6. metrics
    op.create_table(
        'metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('service', sa.String(100), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('labels', sa.JSON(), nullable=False, server_default='{}'),
    )
    op.create_index('ix_metrics_service', 'metrics', ['service'])
    op.create_index('ix_metrics_metric_name', 'metrics', ['metric_name'])
    op.create_index('ix_metrics_timestamp', 'metrics', ['timestamp'])
    op.create_index('ix_metrics_service_name_time', 'metrics', ['service', 'metric_name', 'timestamp'])

    # 7. traces
    op.create_table(
        'traces',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('service', sa.String(100), nullable=False),
        sa.Column('trace_id', sa.String(100), nullable=False),
        sa.Column('span_id', sa.String(100), nullable=False),
        sa.Column('duration', sa.Float(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='OK'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_traces_service', 'traces', ['service'])
    op.create_index('ix_traces_trace_id', 'traces', ['trace_id'])
    op.create_index('ix_traces_timestamp', 'traces', ['timestamp'])

    # 8. hypotheses
    op.create_table(
        'hypotheses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hypothesis', sa.Text(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_hypotheses_incident_id', 'hypotheses', ['incident_id'])

    # 9. remediation_actions
    op.create_table(
        'remediation_actions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False, server_default='LOW'),
        sa.Column('approval_status', sa.String(30), nullable=False, server_default='PENDING'),
        sa.Column('execution_status', sa.String(30), nullable=False, server_default='NOT_STARTED'),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_remediation_actions_incident_id', 'remediation_actions', ['incident_id'])

    # 10. agent_runs
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_name', sa.String(100), nullable=False),
        sa.Column('input', sa.JSON(), nullable=False),
        sa.Column('output', sa.JSON(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='SUCCEEDED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_agent_runs_incident_id', 'agent_runs', ['incident_id'])

    # 11. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(80), nullable=False),
        sa.Column('resource_id', sa.String(80), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])

    # 12. deployment_events
    op.create_table(
        'deployment_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('service', sa.String(100), nullable=False),
        sa.Column('version', sa.String(100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='SUCCESS'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
    )
    op.create_index('ix_deployment_events_service', 'deployment_events', ['service'])
    op.create_index('ix_deployment_events_timestamp', 'deployment_events', ['timestamp'])

def downgrade() -> None:
    op.drop_table('deployment_events')
    op.drop_table('audit_logs')
    op.drop_table('agent_runs')
    op.drop_table('remediation_actions')
    op.drop_table('hypotheses')
    op.drop_table('traces')
    op.drop_table('metrics')
    op.drop_table('logs')
    op.drop_table('incident_events')
    op.drop_table('incidents')
    op.drop_table('services')
    op.drop_table('users')
