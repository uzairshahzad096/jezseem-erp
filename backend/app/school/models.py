"""
JOSE — Jezseem School of Excellence, the company's training school, kept
inside HR and managed by HR (owner, 24-Oct-2026).

    course       what is taught: duration and standard fee
    batch        one run of a course: dates, class days and times, trainer, seats
    student      a person who trains with us
    enrollment   a student in a batch: the fee agreed (fee less discount),
                 status, result and certificate
    payment      fee received against an enrollment; a wrong one is
                 cancelled with a reason, never deleted

The balance a student owes is always computed (net fee less payments not
cancelled); nothing stores it. Fees are tracked here and not posted to the
accounts.
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.mixins import AuditMixin, UUIDPKMixin
from app.core.database import Base

MONEY = Numeric(18, 2)

DURATION_UNITS = ["DAYS", "WEEKS", "MONTHS"]
BATCH_STATUSES = ["PLANNED", "RUNNING", "COMPLETED", "CANCELLED"]
ENROLLMENT_STATUSES = ["ENROLLED", "COMPLETED", "DROPPED"]
PAYMENT_METHODS = ["CASH", "BANK", "CHEQUE", "ONLINE"]


def _company() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)


def _fk(target: str, nullable: bool = True) -> Mapped:
    return mapped_column(UUID(as_uuid=True), ForeignKey(target), nullable=nullable, index=True)


class Course(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "school_courses"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_school_course_code"),)

    company_id: Mapped[uuid.UUID] = _company()
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_value: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_unit: Mapped[str] = mapped_column(String(10), default="WEEKS", nullable=False)
    #: The standard fee; each batch may charge its own.
    fee: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Batch(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "school_batches"
    __table_args__ = (UniqueConstraint("company_id", "batch_code", name="uq_school_batch_code"),)

    company_id: Mapped[uuid.UUID] = _company()
    batch_code: Mapped[str] = mapped_column(String(40), nullable=False)
    course_id: Mapped[uuid.UUID] = _fk("school_courses.id", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    #: "MON,WED,FRI".
    class_days: Mapped[str | None] = mapped_column(String(40))
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    #: An employee teaching it, or an outside trainer by name.
    trainer_employee_id: Mapped[uuid.UUID | None] = _fk("hr_employees.id")
    trainer_name: Mapped[str | None] = mapped_column(String(150))
    venue: Mapped[str | None] = mapped_column(String(150))
    capacity: Mapped[int | None] = mapped_column(Integer)
    fee: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="PLANNED", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class Student(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "school_students"
    __table_args__ = (UniqueConstraint("company_id", "student_no", name="uq_school_student_no"),)

    company_id: Mapped[uuid.UUID] = _company()
    student_no: Mapped[str] = mapped_column(String(30), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    father_name: Mapped[str | None] = mapped_column(String(200))
    gender: Mapped[str | None] = mapped_column(String(10))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    cnic: Mapped[str | None] = mapped_column(String(20), index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(80))
    education: Mapped[str | None] = mapped_column(String(150))
    #: Where the student works or studies, e.g. a customer's company.
    organization: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Enrollment(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "school_enrollments"
    __table_args__ = (UniqueConstraint("student_id", "batch_id", name="uq_school_enrollment"),)

    company_id: Mapped[uuid.UUID] = _company()
    student_id: Mapped[uuid.UUID] = _fk("school_students.id", nullable=False)
    batch_id: Mapped[uuid.UUID] = _fk("school_batches.id", nullable=False)
    enroll_date: Mapped[date] = mapped_column(Date, nullable=False)
    fee: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    discount: Mapped[Decimal] = mapped_column(MONEY, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="ENROLLED", nullable=False, index=True)
    completion_date: Mapped[date | None] = mapped_column(Date)
    result: Mapped[str | None] = mapped_column(String(60))
    certificate_no: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)

    payments: Mapped[list["FeePayment"]] = relationship(back_populates="enrollment", order_by="FeePayment.payment_date")

    @property
    def net_fee(self) -> Decimal:
        return Decimal(self.fee) - Decimal(self.discount or 0)

    @property
    def paid(self) -> Decimal:
        return sum((p.amount for p in self.payments if p.status == "RECEIVED"), Decimal("0"))


class FeePayment(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "school_fee_payments"
    __table_args__ = (UniqueConstraint("company_id", "receipt_no", name="uq_school_receipt_no"),)

    company_id: Mapped[uuid.UUID] = _company()
    receipt_no: Mapped[str] = mapped_column(String(30), nullable=False)
    enrollment_id: Mapped[uuid.UUID] = _fk("school_enrollments.id", nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="CASH", nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="RECEIVED", nullable=False, index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)

    enrollment: Mapped[Enrollment] = relationship(back_populates="payments")


ATTENDANCE_STATUSES = ["PRESENT", "ABSENT", "LATE", "LEAVE"]


class Attendance(UUIDPKMixin, AuditMixin, Base):
    """One student's attendance at one class of their batch (owner,
    24-Oct-2026). Late counts as attended; leave is excused, so it is left out
    of the attendance percentage."""

    __tablename__ = "school_attendance"
    __table_args__ = (UniqueConstraint("enrollment_id", "class_date", name="uq_school_attendance"),)

    company_id: Mapped[uuid.UUID] = _company()
    batch_id: Mapped[uuid.UUID] = _fk("school_batches.id", nullable=False)
    enrollment_id: Mapped[uuid.UUID] = _fk("school_enrollments.id", nullable=False)
    class_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    remarks: Mapped[str | None] = mapped_column(String(200))
