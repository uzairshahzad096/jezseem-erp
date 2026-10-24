"""complaints about employees, raised by senior management

Revision ID: 0026
Revises: 0025

hr_employee_complaints keeps each complaint with who raised it, the action
taken and its status. Complaints are confidential, so their permissions
(hrms.complaints.view / create / edit) go to the Administrator role only;
the Staff role does not get them.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None

ACTIONS = ("view", "create", "edit")


def upgrade() -> None:
    op.create_table(
        "hr_employee_complaints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("complaint_number", sa.String(30), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("hr_employees.id"), nullable=False, index=True),
        sa.Column("complaint_date", sa.Date, nullable=False),
        sa.Column("raised_by", sa.String(150), nullable=False),
        sa.Column("raised_by_designation", sa.String(100)),
        sa.Column("category", sa.String(20), nullable=False, server_default="CONDUCT"),
        sa.Column("severity", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("details", sa.Text),
        sa.Column("action_taken", sa.Text),
        sa.Column("status", sa.String(15), nullable=False, server_default="OPEN", index=True),
        sa.Column("resolved_on", sa.Date),
        sa.UniqueConstraint("company_id", "complaint_number", name="uq_hr_complaint_number"),
        sa.CheckConstraint("status in ('OPEN','UNDER_REVIEW','RESOLVED','DISMISSED')", name="ck_hr_complaint_status"),
        sa.CheckConstraint("severity in ('LOW','MEDIUM','HIGH')", name="ck_hr_complaint_severity"),
    )
    bind = op.get_bind()
    for action in ACTIONS:
        code = f"hrms.complaints.{action}"
        bind.execute(sa.text("""
            insert into permissions (id, module, action, code, description)
            values (gen_random_uuid(), 'hrms', cast(:action as varchar), cast(:code as varchar), cast(:description as varchar))
            on conflict (code) do nothing
        """), {"action": action, "code": code, "description": f"Employee complaints: {action}"})
        bind.execute(sa.text("""
            insert into role_permissions (role_id, permission_id)
            select r.id, p.id from roles r cross join permissions p
            where r.name = 'Administrator' and p.code = :code
            on conflict do nothing
        """), {"code": code})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("delete from role_permissions where permission_id in "
                         "(select id from permissions where code like 'hrms.complaints.%')"))
    bind.execute(sa.text("delete from permissions where code like 'hrms.complaints.%'"))
    op.drop_table("hr_employee_complaints")
