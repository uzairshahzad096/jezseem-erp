"""JOSE — Jezseem School of Excellence: courses, batches, students,
enrollments and fee payments, managed by HR

Revision ID: 0028
Revises: 0027

Five school_* tables. Fees are tracked here, not posted to the accounts.
Permissions hrms.school.view / create / edit / cancel go to the
Administrator and Staff roles (HR runs the school).
"""
import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

TABLES = [
    """CREATE TABLE school_courses (
    company_id UUID NOT NULL, 
    code VARCHAR(30) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    duration_value INTEGER NOT NULL, 
    duration_unit VARCHAR(10) NOT NULL, 
    fee NUMERIC(18, 2) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_school_course_code UNIQUE (company_id, code), 
    FOREIGN KEY(company_id) REFERENCES companies (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(updated_by) REFERENCES users (id)
)""",
    """CREATE INDEX ix_school_courses_company_id ON school_courses (company_id)""",
    """CREATE TABLE school_batches (
    company_id UUID NOT NULL, 
    batch_code VARCHAR(40) NOT NULL, 
    course_id UUID NOT NULL, 
    start_date DATE NOT NULL, 
    end_date DATE NOT NULL, 
    class_days VARCHAR(40), 
    start_time TIME WITHOUT TIME ZONE, 
    end_time TIME WITHOUT TIME ZONE, 
    trainer_employee_id UUID, 
    trainer_name VARCHAR(150), 
    venue VARCHAR(150), 
    capacity INTEGER, 
    fee NUMERIC(18, 2) NOT NULL, 
    status VARCHAR(12) NOT NULL, 
    notes TEXT, 
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_school_batch_code UNIQUE (company_id, batch_code), 
    FOREIGN KEY(company_id) REFERENCES companies (id), 
    FOREIGN KEY(course_id) REFERENCES school_courses (id), 
    FOREIGN KEY(trainer_employee_id) REFERENCES hr_employees (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(updated_by) REFERENCES users (id)
)""",
    """CREATE INDEX ix_school_batches_trainer_employee_id ON school_batches (trainer_employee_id)""",
    """CREATE INDEX ix_school_batches_status ON school_batches (status)""",
    """CREATE INDEX ix_school_batches_course_id ON school_batches (course_id)""",
    """CREATE INDEX ix_school_batches_company_id ON school_batches (company_id)""",
    """CREATE TABLE school_students (
    company_id UUID NOT NULL, 
    student_no VARCHAR(30) NOT NULL, 
    full_name VARCHAR(200) NOT NULL, 
    father_name VARCHAR(200), 
    gender VARCHAR(10), 
    date_of_birth DATE, 
    cnic VARCHAR(20), 
    phone VARCHAR(30), 
    email VARCHAR(150), 
    address TEXT, 
    city VARCHAR(80), 
    education VARCHAR(150), 
    organization VARCHAR(200), 
    notes TEXT, 
    is_active BOOLEAN NOT NULL, 
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_school_student_no UNIQUE (company_id, student_no), 
    FOREIGN KEY(company_id) REFERENCES companies (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(updated_by) REFERENCES users (id)
)""",
    """CREATE INDEX ix_school_students_company_id ON school_students (company_id)""",
    """CREATE INDEX ix_school_students_cnic ON school_students (cnic)""",
    """CREATE INDEX ix_school_students_full_name ON school_students (full_name)""",
    """CREATE TABLE school_enrollments (
    company_id UUID NOT NULL, 
    student_id UUID NOT NULL, 
    batch_id UUID NOT NULL, 
    enroll_date DATE NOT NULL, 
    fee NUMERIC(18, 2) NOT NULL, 
    discount NUMERIC(18, 2) NOT NULL, 
    status VARCHAR(12) NOT NULL, 
    completion_date DATE, 
    result VARCHAR(60), 
    certificate_no VARCHAR(40), 
    notes TEXT, 
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_school_enrollment UNIQUE (student_id, batch_id), 
    FOREIGN KEY(company_id) REFERENCES companies (id), 
    FOREIGN KEY(student_id) REFERENCES school_students (id), 
    FOREIGN KEY(batch_id) REFERENCES school_batches (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(updated_by) REFERENCES users (id)
)""",
    """CREATE INDEX ix_school_enrollments_company_id ON school_enrollments (company_id)""",
    """CREATE INDEX ix_school_enrollments_student_id ON school_enrollments (student_id)""",
    """CREATE INDEX ix_school_enrollments_status ON school_enrollments (status)""",
    """CREATE INDEX ix_school_enrollments_batch_id ON school_enrollments (batch_id)""",
    """CREATE TABLE school_fee_payments (
    company_id UUID NOT NULL, 
    receipt_no VARCHAR(30) NOT NULL, 
    enrollment_id UUID NOT NULL, 
    payment_date DATE NOT NULL, 
    amount NUMERIC(18, 2) NOT NULL, 
    method VARCHAR(10) NOT NULL, 
    reference VARCHAR(100), 
    notes TEXT, 
    status VARCHAR(10) NOT NULL, 
    cancelled_at TIMESTAMP WITH TIME ZONE, 
    cancel_reason TEXT, 
    id UUID NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by UUID, 
    updated_by UUID, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_school_receipt_no UNIQUE (company_id, receipt_no), 
    FOREIGN KEY(company_id) REFERENCES companies (id), 
    FOREIGN KEY(enrollment_id) REFERENCES school_enrollments (id), 
    FOREIGN KEY(created_by) REFERENCES users (id), 
    FOREIGN KEY(updated_by) REFERENCES users (id)
)""",
    """CREATE INDEX ix_school_fee_payments_company_id ON school_fee_payments (company_id)""",
    """CREATE INDEX ix_school_fee_payments_status ON school_fee_payments (status)""",
    """CREATE INDEX ix_school_fee_payments_enrollment_id ON school_fee_payments (enrollment_id)""",
]

CHECKS = [
    "alter table school_courses add constraint ck_school_course_fee check (fee >= 0 and duration_value > 0)",
    "alter table school_courses add constraint ck_school_course_unit check (duration_unit in ('DAYS','WEEKS','MONTHS'))",
    "alter table school_batches add constraint ck_school_batch_status check (status in ('PLANNED','RUNNING','COMPLETED','CANCELLED'))",
    "alter table school_batches add constraint ck_school_batch_dates check (end_date >= start_date)",
    "alter table school_enrollments add constraint ck_school_enrollment_status check (status in ('ENROLLED','COMPLETED','DROPPED'))",
    "alter table school_enrollments add constraint ck_school_enrollment_fee check (fee >= 0 and discount >= 0 and discount <= fee)",
    "alter table school_fee_payments add constraint ck_school_payment_amount check (amount > 0)",
    "alter table school_fee_payments add constraint ck_school_payment_status check (status in ('RECEIVED','CANCELLED'))",
]

ACTIONS = ("view", "create", "edit", "cancel")


def upgrade() -> None:
    for statement in TABLES + CHECKS:
        op.execute(statement)
    bind = op.get_bind()
    for action in ACTIONS:
        code = f"hrms.school.{action}"
        bind.execute(sa.text("""
            insert into permissions (id, module, action, code, description)
            values (gen_random_uuid(), 'hrms', cast(:action as varchar), cast(:code as varchar), cast(:description as varchar))
            on conflict (code) do nothing
        """), {"action": action, "code": code, "description": f"JOSE school: {action}"})
        bind.execute(sa.text("""
            insert into role_permissions (role_id, permission_id)
            select r.id, p.id from roles r cross join permissions p
            where r.name in ('Administrator', 'Staff') and p.code = :code
            on conflict do nothing
        """), {"code": code})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("delete from role_permissions where permission_id in "
                         "(select id from permissions where code like 'hrms.school.%')"))
    bind.execute(sa.text("delete from permissions where code like 'hrms.school.%'"))
    for table in ("school_fee_payments", "school_enrollments", "school_students", "school_batches", "school_courses"):
        op.drop_table(table)
