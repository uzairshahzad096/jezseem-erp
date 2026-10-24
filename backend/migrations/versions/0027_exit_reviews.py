"""senior management's remarks on employees who left

Revision ID: 0027
Revises: 0026

hr_exit_reviews keeps, for an employee who resigned or was terminated, one
or more managers' ratings (behaviour, discipline, punctuality, work quality,
honesty, 1-5), whether they would be rehired, and comments. Confidential:
hrms.exit_reviews.view / create / edit go to the Administrator role only.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

AREAS = ("behaviour", "discipline", "punctuality", "work_quality", "honesty")


def upgrade() -> None:
    op.create_table(
        "hr_exit_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("hr_employees.id"), nullable=False, index=True),
        sa.Column("review_date", sa.Date, nullable=False),
        sa.Column("reviewer_name", sa.String(150), nullable=False),
        sa.Column("reviewer_designation", sa.String(100)),
        *[sa.Column(a, sa.Integer) for a in AREAS],
        sa.Column("rehire", sa.String(12), nullable=False),
        sa.Column("comments", sa.Text, nullable=False),
        sa.CheckConstraint("rehire in ('YES','NO','CONDITIONAL')", name="ck_hr_exit_review_rehire"),
        *[sa.CheckConstraint(f"{a} between 1 and 5", name=f"ck_hr_exit_review_{a}") for a in AREAS],
    )
    bind = op.get_bind()
    for action in ("view", "create", "edit"):
        code = f"hrms.exit_reviews.{action}"
        bind.execute(sa.text("""
            insert into permissions (id, module, action, code, description)
            values (gen_random_uuid(), 'hrms', cast(:action as varchar), cast(:code as varchar), cast(:description as varchar))
            on conflict (code) do nothing
        """), {"action": action, "code": code, "description": f"Leaving remarks on employees: {action}"})
        bind.execute(sa.text("""
            insert into role_permissions (role_id, permission_id)
            select r.id, p.id from roles r cross join permissions p
            where r.name = 'Administrator' and p.code = :code
            on conflict do nothing
        """), {"code": code})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("delete from role_permissions where permission_id in "
                         "(select id from permissions where code like 'hrms.exit_reviews.%')"))
    bind.execute(sa.text("delete from permissions where code like 'hrms.exit_reviews.%'"))
    op.drop_table("hr_exit_reviews")
