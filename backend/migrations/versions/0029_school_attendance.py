"""JOSE student attendance

Revision ID: 0029
Revises: 0028

One row per student per class date of their batch: present, absent, late or
on leave. Uses the existing hrms.school permissions.
"""
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE TABLE school_attendance (
    company_id UUID NOT NULL, 
    batch_id UUID NOT NULL, 
    enrollment_id UUID NOT NULL, 
    class_date DATE NOT NULL, 
    status VARCHAR(10) NOT NULL, 
    remarks VARCHAR(200), 
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_school_attendance UNIQUE (enrollment_id, class_date), 
    FOREIGN KEY(company_id) REFERENCES companies (id), 
    FOREIGN KEY(batch_id) REFERENCES school_batches (id), 
    FOREIGN KEY(enrollment_id) REFERENCES school_enrollments (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(updated_by) REFERENCES users (id)
)""",
    """CREATE INDEX ix_school_attendance_enrollment_id ON school_attendance (enrollment_id)""",
    """CREATE INDEX ix_school_attendance_company_id ON school_attendance (company_id)""",
    """CREATE INDEX ix_school_attendance_class_date ON school_attendance (class_date)""",
    """CREATE INDEX ix_school_attendance_batch_id ON school_attendance (batch_id)""",
    "alter table school_attendance add constraint ck_school_attendance_status "
    "check (status in ('PRESENT','ABSENT','LATE','LEAVE'))",
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.drop_table("school_attendance")
