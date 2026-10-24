"""JOSE — Jezseem School of Excellence (owner, 24-Oct-2026). See models.py.

Permissions: hrms.school.view / create / edit / cancel, given to HR.
"""

import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.audit import service as audit
from app.audit.service import AuditContext, request_context
from app.auth.dependencies import require_permission
from app.common.numbering import next_number
from app.core.database import get_db
from app.hrms.models import Employee
from app.inventory.router import active_company_id
from app.school import models as m
from app.users.models import User

router = APIRouter(prefix="/school", tags=["school"])

VIEW, CREATE, EDIT, CANCEL = ("hrms.school.view", "hrms.school.create", "hrms.school.edit", "hrms.school.cancel")
ZERO = Decimal("0")


# ------------------------------------------------------------------ helpers

def _blank(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _owned(db: Session, model, row_id: uuid.UUID, what: str, *options):
    row = db.scalar(select(model).options(*options).where(model.id == row_id))
    if row is None or row.company_id != active_company_id(db):
        raise HTTPException(404, f"{what} not found.")
    return row


def _page(db: Session, stmt, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    return total, list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique())


def _save(db: Session, what: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        text = str(exc.orig)
        if "uq_school_enrollment" in text:
            raise HTTPException(400, "This student is already enrolled in that batch.")
        if "uq_school_" in text:
            raise HTTPException(400, f"That {what} code or number is already in use.")
        raise


def _number(db: Session, company_id: uuid.UUID, kind: str, prefix: str) -> str:
    return f"{prefix}-{int(next_number(db, company_id, f'school_{kind}', 'ALL')):05d}"


def _hhmm(t: time | None) -> str | None:
    return t.strftime("%H:%M") if t else None


def _num(v) -> float:
    return float(v or 0)


# ------------------------------------------------------------------ lookups & summary

@router.get("/lookups")
def lookups(db: Session = Depends(get_db), user: User = Depends(require_permission(VIEW))):
    company_id = active_company_id(db)
    courses = db.scalars(select(m.Course).where(m.Course.company_id == company_id).order_by(m.Course.name)).all()
    batches = db.scalars(select(m.Batch).where(m.Batch.company_id == company_id)
                         .order_by(m.Batch.start_date.desc())).all()
    names = {c.id: c.name for c in courses}
    trainers = db.execute(select(Employee.id, Employee.employee_code, Employee.full_name)
                          .where(Employee.company_id == company_id, Employee.status == "ACTIVE")
                          .order_by(Employee.full_name)).all()
    return {
        "courses": [{"id": str(c.id), "code": c.code, "name": c.name, "fee": _num(c.fee), "is_active": c.is_active,
                     "duration": f"{c.duration_value} {c.duration_unit.lower()}"} for c in courses],
        "batches": [{"id": str(b.id), "batch_code": b.batch_code, "course": names.get(b.course_id), "fee": _num(b.fee),
                     "status": b.status, "start_date": b.start_date, "end_date": b.end_date} for b in batches],
        "trainers": [{"id": str(i), "label": f"{code}  {name}"} for i, code, name in trainers],
    }


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(require_permission(VIEW))):
    company_id = active_company_id(db)
    today = date.today()
    month_start = today.replace(day=1)
    enrollments = db.scalars(select(m.Enrollment).options(selectinload(m.Enrollment.payments))
                             .where(m.Enrollment.company_id == company_id, m.Enrollment.status != "DROPPED")).all()
    collected = db.scalar(select(func.coalesce(func.sum(m.FeePayment.amount), 0)).where(
        m.FeePayment.company_id == company_id, m.FeePayment.status == "RECEIVED",
        m.FeePayment.payment_date >= month_start)) or 0
    return {
        "students": db.scalar(select(func.count()).where(m.Student.company_id == company_id, m.Student.is_active)) or 0,
        "running_batches": db.scalar(select(func.count()).where(m.Batch.company_id == company_id,
                                                                m.Batch.status == "RUNNING")) or 0,
        "enrolled_now": sum(1 for e in enrollments if e.status == "ENROLLED"),
        "collected_month": _num(collected),
        "outstanding": _num(sum((max(e.net_fee - e.paid, ZERO) for e in enrollments), ZERO)),
    }


# ------------------------------------------------------------------ courses

class CourseIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    duration_value: int = Field(gt=0)
    duration_unit: Literal["DAYS", "WEEKS", "MONTHS"] = "WEEKS"
    fee: Decimal = Field(ge=0)
    is_active: bool = True


def _course(c: m.Course, counts: dict | None = None) -> dict:
    return {"id": str(c.id), "code": c.code, "name": c.name, "description": c.description,
            "duration_value": c.duration_value, "duration_unit": c.duration_unit, "fee": _num(c.fee),
            "is_active": c.is_active, "batches": (counts or {}).get(c.id, 0)}


@router.get("/courses")
def list_courses(search: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=5000),
                 db: Session = Depends(get_db), user: User = Depends(require_permission(VIEW))):
    company_id = active_company_id(db)
    stmt = select(m.Course).where(m.Course.company_id == company_id)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(m.Course.code.ilike(like), m.Course.name.ilike(like)))
    total, rows = _page(db, stmt.order_by(m.Course.name), page, page_size)
    counts = dict(db.execute(select(m.Batch.course_id, func.count()).where(m.Batch.company_id == company_id)
                             .group_by(m.Batch.course_id)).all())
    return {"items": [_course(c, counts) for c in rows], "total": total}


@router.post("/courses", status_code=201)
def create_course(payload: CourseIn, db: Session = Depends(get_db), ctx: AuditContext = Depends(request_context),
                  user: User = Depends(require_permission(CREATE))):
    c = m.Course(company_id=active_company_id(db), created_by=user.id,
                 **{k: _blank(v) for k, v in payload.model_dump().items()})
    c.code = c.code.upper()
    db.add(c)
    db.flush()
    audit.record(db, ctx, action="create", module="school", entity="school_course", entity_id=c.id,
                 company_id=c.company_id, new_values=audit.snapshot(c))
    _save(db, "course")
    return _course(c)


@router.put("/courses/{course_id}")
def update_course(course_id: uuid.UUID, payload: CourseIn, db: Session = Depends(get_db),
                  ctx: AuditContext = Depends(request_context), user: User = Depends(require_permission(EDIT))):
    c = _owned(db, m.Course, course_id, "Course")
    before = audit.snapshot(c)
    for k, v in payload.model_dump().items():
        setattr(c, k, _blank(v))
    c.code, c.updated_by = c.code.upper(), user.id
    audit.record(db, ctx, action="update", module="school", entity="school_course", entity_id=c.id,
                 company_id=c.company_id, old_values=before, new_values=audit.snapshot(c))
    _save(db, "course")
    return _course(c)


# ------------------------------------------------------------------ batches

class BatchIn(BaseModel):
    course_id: str
    batch_code: str | None = Field(default=None, max_length=40)
    start_date: date
    end_date: date
    class_days: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    trainer_employee_id: str | None = None
    trainer_name: str | None = Field(default=None, max_length=150)
    venue: str | None = Field(default=None, max_length=150)
    capacity: int | None = Field(default=None, gt=0)
    fee: Decimal | None = Field(default=None, ge=0)
    status: Literal["PLANNED", "RUNNING", "COMPLETED", "CANCELLED"] = "PLANNED"
    notes: str | None = None


def _batch_rows(db: Session, rows: list[m.Batch]) -> list[dict]:
    company_id = active_company_id(db)
    courses = {c.id: c for c in db.scalars(select(m.Course).where(m.Course.company_id == company_id))}
    trainers = dict(db.execute(select(Employee.id, Employee.full_name).where(Employee.company_id == company_id)).all())
    ids = [b.id for b in rows]
    enrolled = dict(db.execute(select(m.Enrollment.batch_id, func.count()).where(
        m.Enrollment.batch_id.in_(ids), m.Enrollment.status != "DROPPED").group_by(m.Enrollment.batch_id)).all()) if ids else {}
    out = []
    for b in rows:
        c = courses.get(b.course_id)
        out.append({
            "id": str(b.id), "batch_code": b.batch_code, "course_id": str(b.course_id),
            "course_name": c.name if c else None, "course_code": c.code if c else None,
            "start_date": b.start_date, "end_date": b.end_date, "class_days": b.class_days,
            "start_time": _hhmm(b.start_time), "end_time": _hhmm(b.end_time),
            "trainer_employee_id": str(b.trainer_employee_id) if b.trainer_employee_id else None,
            "trainer": trainers.get(b.trainer_employee_id) or b.trainer_name, "trainer_name": b.trainer_name,
            "venue": b.venue, "capacity": b.capacity, "fee": _num(b.fee), "status": b.status, "notes": b.notes,
            "enrolled": enrolled.get(b.id, 0),
        })
    return out


@router.get("/batches")
def list_batches(search: str | None = None, course_id: uuid.UUID | None = None,
                 status_filter: list[str] = Query(default=[], alias="status"),
                 page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=5000),
                 db: Session = Depends(get_db), user: User = Depends(require_permission(VIEW))):
    company_id = active_company_id(db)
    stmt = select(m.Batch).where(m.Batch.company_id == company_id)
    if course_id:
        stmt = stmt.where(m.Batch.course_id == course_id)
    if status_filter:
        stmt = stmt.where(m.Batch.status.in_([s.upper() for s in status_filter]))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(m.Batch.batch_code.ilike(like), m.Batch.trainer_name.ilike(like),
                              m.Batch.course_id.in_(select(m.Course.id).where(m.Course.name.ilike(like)))))
    total, rows = _page(db, stmt.order_by(m.Batch.start_date.desc()), page, page_size)
    return {"items": _batch_rows(db, rows), "total": total}


def _apply_batch(db: Session, b: m.Batch, payload: BatchIn) -> None:
    company_id = active_company_id(db)
    course = _owned(db, m.Course, uuid.UUID(payload.course_id), "Course")
    if payload.end_date < payload.start_date:
        raise HTTPException(400, "The batch ends before it starts.")
    if payload.start_time and payload.end_time and payload.end_time <= payload.start_time:
        raise HTTPException(400, "The class ends before it starts.")
    trainer_id = uuid.UUID(payload.trainer_employee_id) if payload.trainer_employee_id else None
    if trainer_id:
        _owned(db, Employee, trainer_id, "Trainer")
    b.course_id, b.start_date, b.end_date = course.id, payload.start_date, payload.end_date
    b.class_days = ",".join(d.strip().upper() for d in (payload.class_days or "").split(",") if d.strip()) or None
    b.start_time, b.end_time = payload.start_time, payload.end_time
    b.trainer_employee_id, b.trainer_name = trainer_id, None if trainer_id else _blank(payload.trainer_name)
    b.venue, b.capacity, b.status, b.notes = _blank(payload.venue), payload.capacity, payload.status, _blank(payload.notes)
    b.fee = payload.fee if payload.fee is not None else course.fee
    if not b.batch_code:
        b.batch_code = (_blank(payload.batch_code) or "").upper() or \
            f"{course.code}-{payload.start_date:%y%m}-{int(next_number(db, company_id, f'school_batch_{course.code}', 'ALL')):02d}"


@router.post("/batches", status_code=201)
def create_batch(payload: BatchIn, db: Session = Depends(get_db), ctx: AuditContext = Depends(request_context),
                 user: User = Depends(require_permission(CREATE))):
    b = m.Batch(company_id=active_company_id(db), created_by=user.id)
    _apply_batch(db, b, payload)
    db.add(b)
    db.flush()
    audit.record(db, ctx, action="create", module="school", entity="school_batch", entity_id=b.id,
                 company_id=b.company_id, new_values=audit.snapshot(b))
    _save(db, "batch")
    return _batch_rows(db, [b])[0]


@router.put("/batches/{batch_id}")
def update_batch(batch_id: uuid.UUID, payload: BatchIn, db: Session = Depends(get_db),
                 ctx: AuditContext = Depends(request_context), user: User = Depends(require_permission(EDIT))):
    b = _owned(db, m.Batch, batch_id, "Batch")
    before = audit.snapshot(b)
    _apply_batch(db, b, payload)
    if payload.batch_code:
        b.batch_code = payload.batch_code.strip().upper()
    b.updated_by = user.id
    audit.record(db, ctx, action="update", module="school", entity="school_batch", entity_id=b.id,
                 company_id=b.company_id, old_values=before, new_values=audit.snapshot(b))
    _save(db, "batch")
    return _batch_rows(db, [b])[0]


# ------------------------------------------------------------------ students

class StudentIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    father_name: str | None = Field(default=None, max_length=200)
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    date_of_birth: date | None = None
    cnic: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=150)
    address: str | None = None
    city: str | None = Field(default=None, max_length=80)
    education: str | None = Field(default=None, max_length=150)
    organization: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    is_active: bool = True


def _student_rows(db: Session, rows: list[m.Student]) -> list[dict]:
    ids = [s.id for s in rows]
    enrollments = db.scalars(select(m.Enrollment).options(selectinload(m.Enrollment.payments))
                             .where(m.Enrollment.student_id.in_(ids))).all() if ids else []
    by_student: dict = {}
    for e in enrollments:
        by_student.setdefault(e.student_id, []).append(e)
    out = []
    for s in rows:
        mine = [e for e in by_student.get(s.id, []) if e.status != "DROPPED"]
        out.append({**{c.key: getattr(s, c.key) for c in m.Student.__table__.columns},
                    "id": str(s.id), "company_id": str(s.company_id),
                    "courses": len(by_student.get(s.id, [])),
                    "balance": _num(sum((max(e.net_fee - e.paid, ZERO) for e in mine), ZERO))})
    return out


@router.get("/students")
def list_students(search: str | None = None, active_only: bool = False,
                  page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=5000),
                  db: Session = Depends(get_db), user: User = Depends(require_permission(VIEW))):
    company_id = active_company_id(db)
    stmt = select(m.Student).where(m.Student.company_id == company_id)
    if active_only:
        stmt = stmt.where(m.Student.is_active)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(m.Student.student_no.ilike(like), m.Student.full_name.ilike(like),
                              m.Student.cnic.ilike(like), m.Student.phone.ilike(like),
                              m.Student.organization.ilike(like)))
    total, rows = _page(db, stmt.order_by(m.Student.student_no.desc()), page, page_size)
    return {"items": _student_rows(db, rows), "total": total}


@router.post("/students", status_code=201)
def create_student(payload: StudentIn, db: Session = Depends(get_db), ctx: AuditContext = Depends(request_context),
                   user: User = Depends(require_permission(CREATE))):
    company_id = active_company_id(db)
    s = m.Student(company_id=company_id, created_by=user.id, student_no=_number(db, company_id, "student", "ST"),
                  **{k: _blank(v) for k, v in payload.model_dump().items()})
    db.add(s)
    db.flush()
    audit.record(db, ctx, action="create", module="school", entity="school_student", entity_id=s.id,
                 company_id=company_id, new_values=audit.snapshot(s))
    _save(db, "student")
    return _student_rows(db, [s])[0]


@router.put("/students/{student_id}")
def update_student(student_id: uuid.UUID, payload: StudentIn, db: Session = Depends(get_db),
                   ctx: AuditContext = Depends(request_context), user: User = Depends(require_permission(EDIT))):
    s = _owned(db, m.Student, student_id, "Student")
    before = audit.snapshot(s)
    for k, v in payload.model_dump().items():
        setattr(s, k, _blank(v))
    s.updated_by = user.id
    audit.record(db, ctx, action="update", module="school", entity="school_student", entity_id=s.id,
                 company_id=s.company_id, old_values=before, new_values=audit.snapshot(s))
    _save(db, "student")
    return _student_rows(db, [s])[0]


# ------------------------------------------------------------------ enrollments

class EnrollmentIn(BaseModel):
    student_id: str
    batch_id: str
    enroll_date: date
    fee: Decimal | None = Field(default=None, ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    status: Literal["ENROLLED", "COMPLETED", "DROPPED"] = "ENROLLED"
    completion_date: date | None = None
    result: str | None = Field(default=None, max_length=60)
    certificate_no: str | None = Field(default=None, max_length=40)
    notes: str | None = None


def _enrollment_rows(db: Session, rows: list[m.Enrollment]) -> list[dict]:
    company_id = active_company_id(db)
    students = {s.id: s for s in db.scalars(select(m.Student).where(m.Student.id.in_({e.student_id for e in rows})))} if rows else {}
    batches = {b["id"]: b for b in _batch_rows(db, db.scalars(select(m.Batch).where(
        m.Batch.id.in_({e.batch_id for e in rows}))).all())} if rows else {}
    attendance = attendance_counts(db, [e.id for e in rows])
    out = []
    for e in rows:
        s, b = students.get(e.student_id), batches.get(str(e.batch_id), {})
        paid = e.paid
        out.append({
            "id": str(e.id), "student_id": str(e.student_id), "batch_id": str(e.batch_id),
            "student_no": s.student_no if s else None, "student_name": s.full_name if s else None,
            "batch_code": b.get("batch_code"), "course_name": b.get("course_name"),
            "batch_start": b.get("start_date"), "batch_end": b.get("end_date"),
            "enroll_date": e.enroll_date, "fee": _num(e.fee), "discount": _num(e.discount),
            "net_fee": _num(e.net_fee), "paid": _num(paid),
            "balance": _num(max(e.net_fee - paid, ZERO)) if e.status != "DROPPED" else 0.0,
            "status": e.status, "completion_date": e.completion_date, "result": e.result,
            "certificate_no": e.certificate_no, "notes": e.notes,
            "attendance_percent": attendance_percent(attendance.get(e.id, {})),
            "classes_marked": sum(attendance.get(e.id, {}).values()),
            "payments": [{"id": str(p.id), "receipt_no": p.receipt_no, "payment_date": p.payment_date,
                          "amount": _num(p.amount), "method": p.method, "reference": p.reference,
                          "status": p.status, "cancel_reason": p.cancel_reason} for p in e.payments],
        })
    return out


@router.get("/enrollments")
def list_enrollments(search: str | None = None, student_id: uuid.UUID | None = None, batch_id: uuid.UUID | None = None,
                     status_filter: list[str] = Query(default=[], alias="status"), owing: bool = False,
                     page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=5000),
                     db: Session = Depends(get_db), user: User = Depends(require_permission(VIEW))):
    company_id = active_company_id(db)
    stmt = (select(m.Enrollment).options(selectinload(m.Enrollment.payments))
            .where(m.Enrollment.company_id == company_id))
    if student_id:
        stmt = stmt.where(m.Enrollment.student_id == student_id)
    if batch_id:
        stmt = stmt.where(m.Enrollment.batch_id == batch_id)
    if status_filter:
        stmt = stmt.where(m.Enrollment.status.in_([s.upper() for s in status_filter]))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            m.Enrollment.student_id.in_(select(m.Student.id).where(or_(m.Student.full_name.ilike(like),
                                                                       m.Student.student_no.ilike(like)))),
            m.Enrollment.batch_id.in_(select(m.Batch.id).where(m.Batch.batch_code.ilike(like))),
            m.Enrollment.certificate_no.ilike(like)))
    stmt = stmt.order_by(m.Enrollment.enroll_date.desc())
    if owing:
        # A computed balance: filter after loading, then page by hand.
        rows = [r for r in _enrollment_rows(db, list(db.scalars(stmt).unique())) if r["balance"] > 0]
        return {"items": rows[(page - 1) * page_size: page * page_size], "total": len(rows)}
    total, rows = _page(db, stmt, page, page_size)
    return {"items": _enrollment_rows(db, rows), "total": total}


def _apply_enrollment(db: Session, e: m.Enrollment, payload: EnrollmentIn) -> None:
    student = _owned(db, m.Student, uuid.UUID(payload.student_id), "Student")
    batch = _owned(db, m.Batch, uuid.UUID(payload.batch_id), "Batch")
    if batch.status == "CANCELLED" and e.batch_id != batch.id:
        raise HTTPException(400, f"Batch {batch.batch_code} is cancelled.")
    fee = payload.fee if payload.fee is not None else batch.fee
    if payload.discount > fee:
        raise HTTPException(400, "The discount is more than the fee.")
    if e.batch_id != batch.id and batch.capacity:
        taken = db.scalar(select(func.count()).where(m.Enrollment.batch_id == batch.id,
                                                      m.Enrollment.status != "DROPPED")) or 0
        if taken >= batch.capacity:
            raise HTTPException(400, f"Batch {batch.batch_code} is full ({batch.capacity} seats).")
    paid = e.paid if e.payments else ZERO
    if fee - payload.discount < paid:
        raise HTTPException(400, f"{paid:,.0f} has already been paid; the fee less discount cannot be below that.")
    e.student_id, e.batch_id, e.enroll_date = student.id, batch.id, payload.enroll_date
    e.fee, e.discount, e.status = fee, payload.discount, payload.status
    e.completion_date = (payload.completion_date or date.today()) if payload.status == "COMPLETED" else None
    e.result, e.certificate_no, e.notes = _blank(payload.result), _blank(payload.certificate_no), _blank(payload.notes)


@router.post("/enrollments", status_code=201)
def create_enrollment(payload: EnrollmentIn, db: Session = Depends(get_db), ctx: AuditContext = Depends(request_context),
                      user: User = Depends(require_permission(CREATE))):
    e = m.Enrollment(company_id=active_company_id(db), created_by=user.id)
    e.payments = []
    _apply_enrollment(db, e, payload)
    db.add(e)
    db.flush()
    audit.record(db, ctx, action="create", module="school", entity="school_enrollment", entity_id=e.id,
                 company_id=e.company_id, new_values=audit.snapshot(e))
    _save(db, "enrollment")
    return _enrollment_rows(db, [e])[0]


@router.put("/enrollments/{enrollment_id}")
def update_enrollment(enrollment_id: uuid.UUID, payload: EnrollmentIn, db: Session = Depends(get_db),
                      ctx: AuditContext = Depends(request_context), user: User = Depends(require_permission(EDIT))):
    e = _owned(db, m.Enrollment, enrollment_id, "Enrollment", selectinload(m.Enrollment.payments))
    before = audit.snapshot(e)
    _apply_enrollment(db, e, payload)
    e.updated_by = user.id
    audit.record(db, ctx, action="update", module="school", entity="school_enrollment", entity_id=e.id,
                 company_id=e.company_id, old_values=before, new_values=audit.snapshot(e))
    _save(db, "enrollment")
    return _enrollment_rows(db, [e])[0]


# ------------------------------------------------------------------ fee payments

class PaymentIn(BaseModel):
    enrollment_id: str
    payment_date: date
    amount: Decimal = Field(gt=0)
    method: Literal["CASH", "BANK", "CHEQUE", "ONLINE"] = "CASH"
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class CancelIn(BaseModel):
    reason: str = Field(min_length=3)


def _payment_rows(db: Session, rows: list[m.FeePayment]) -> list[dict]:
    enrollments = {r["id"]: r for r in _enrollment_rows(db, db.scalars(
        select(m.Enrollment).options(selectinload(m.Enrollment.payments))
        .where(m.Enrollment.id.in_({p.enrollment_id for p in rows}))).all())} if rows else {}
    out = []
    for p in rows:
        e = enrollments.get(str(p.enrollment_id), {})
        out.append({"id": str(p.id), "receipt_no": p.receipt_no, "enrollment_id": str(p.enrollment_id),
                    "student_name": e.get("student_name"), "student_no": e.get("student_no"),
                    "batch_code": e.get("batch_code"), "course_name": e.get("course_name"),
                    "payment_date": p.payment_date, "amount": _num(p.amount), "method": p.method,
                    "reference": p.reference, "notes": p.notes, "status": p.status,
                    "cancel_reason": p.cancel_reason, "balance_after": e.get("balance")})
    return out


@router.get("/payments")
def list_payments(search: str | None = None, date_from: date | None = None, date_to: date | None = None,
                  page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=5000),
                  db: Session = Depends(get_db), user: User = Depends(require_permission(VIEW))):
    company_id = active_company_id(db)
    stmt = select(m.FeePayment).where(m.FeePayment.company_id == company_id)
    if date_from:
        stmt = stmt.where(m.FeePayment.payment_date >= date_from)
    if date_to:
        stmt = stmt.where(m.FeePayment.payment_date <= date_to)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(m.FeePayment.receipt_no.ilike(like), m.FeePayment.reference.ilike(like),
                              m.FeePayment.enrollment_id.in_(select(m.Enrollment.id).where(
                                  m.Enrollment.student_id.in_(select(m.Student.id).where(
                                      m.Student.full_name.ilike(like)))))))
    total, rows = _page(db, stmt.order_by(m.FeePayment.payment_date.desc(), m.FeePayment.receipt_no.desc()), page, page_size)
    return {"items": _payment_rows(db, rows), "total": total}


@router.post("/payments", status_code=201)
def create_payment(payload: PaymentIn, db: Session = Depends(get_db), ctx: AuditContext = Depends(request_context),
                   user: User = Depends(require_permission(CREATE))):
    company_id = active_company_id(db)
    e = _owned(db, m.Enrollment, uuid.UUID(payload.enrollment_id), "Enrollment", selectinload(m.Enrollment.payments))
    if e.status == "DROPPED":
        raise HTTPException(400, "This student dropped the course; no fee is due.")
    due = e.net_fee - e.paid
    if payload.amount > due:
        raise HTTPException(400, f"Only {due:,.0f} is due on this enrollment; {payload.amount:,.0f} is more than that.")
    if payload.payment_date > date.today():
        raise HTTPException(400, "The payment date cannot be in the future.")
    p = m.FeePayment(company_id=company_id, created_by=user.id, receipt_no=_number(db, company_id, "receipt", "FR"),
                     enrollment_id=e.id, payment_date=payload.payment_date, amount=payload.amount,
                     method=payload.method, reference=_blank(payload.reference), notes=_blank(payload.notes))
    db.add(p)
    db.flush()
    db.refresh(e)
    audit.record(db, ctx, action="create", module="school", entity="school_fee_payment", entity_id=p.id,
                 company_id=company_id, new_values=audit.snapshot(p))
    _save(db, "receipt")
    return _payment_rows(db, [p])[0]


@router.post("/payments/{payment_id}/cancel")
def cancel_payment(payment_id: uuid.UUID, payload: CancelIn, db: Session = Depends(get_db),
                   ctx: AuditContext = Depends(request_context), user: User = Depends(require_permission(CANCEL))):
    p = _owned(db, m.FeePayment, payment_id, "Payment")
    if p.status == "CANCELLED":
        raise HTTPException(400, f"Receipt {p.receipt_no} is already cancelled.")
    p.status, p.cancelled_at, p.cancel_reason = "CANCELLED", datetime.now(timezone.utc), payload.reason.strip()
    p.updated_by = user.id
    audit.record(db, ctx, action="cancel", module="school", entity="school_fee_payment", entity_id=p.id,
                 company_id=p.company_id, old_values={"status": "RECEIVED"},
                 new_values={"status": "CANCELLED", "reason": p.cancel_reason})
    _save(db, "receipt")
    return _payment_rows(db, [p])[0]


# ------------------------------------------------------------------ attendance
#
# Marked per batch and class date (owner, 24-Oct-2026). Late counts as
# attended; leave is excused and left out of the percentage.

WEEKDAY_CODES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


class MarkIn(BaseModel):
    enrollment_id: str
    status: Literal["PRESENT", "ABSENT", "LATE", "LEAVE"] | None = None
    remarks: str | None = Field(default=None, max_length=200)


class AttendanceIn(BaseModel):
    batch_id: str
    class_date: date
    marks: list[MarkIn]


def attendance_percent(counts: dict) -> float | None:
    held = counts.get("PRESENT", 0) + counts.get("LATE", 0) + counts.get("ABSENT", 0)
    return round((counts.get("PRESENT", 0) + counts.get("LATE", 0)) * 100 / held, 1) if held else None


def attendance_counts(db: Session, enrollment_ids) -> dict:
    """{enrollment_id: {"PRESENT": n, ...}}."""
    ids = list(enrollment_ids)
    out: dict = {}
    if not ids:
        return out
    for eid, status, n in db.execute(select(m.Attendance.enrollment_id, m.Attendance.status, func.count())
                                     .where(m.Attendance.enrollment_id.in_(ids))
                                     .group_by(m.Attendance.enrollment_id, m.Attendance.status)):
        out.setdefault(eid, {})[status] = n
    return out


def _roster(db: Session, batch: m.Batch) -> list[m.Enrollment]:
    return list(db.scalars(select(m.Enrollment).where(m.Enrollment.batch_id == batch.id,
                                                      m.Enrollment.status != "DROPPED")))


@router.get("/attendance")
def attendance_sheet(batch_id: uuid.UUID, class_date: date, db: Session = Depends(get_db),
                     user: User = Depends(require_permission(VIEW))):
    """The batch's students with their mark for one class date."""
    batch = _owned(db, m.Batch, batch_id, "Batch")
    enrollments = _roster(db, batch)
    students = {s.id: s for s in db.scalars(select(m.Student).where(
        m.Student.id.in_({e.student_id for e in enrollments})))} if enrollments else {}
    marks = {a.enrollment_id: a for a in db.scalars(select(m.Attendance).where(
        m.Attendance.batch_id == batch.id, m.Attendance.class_date == class_date))}
    counts = attendance_counts(db, [e.id for e in enrollments])
    rows = []
    for e in sorted(enrollments, key=lambda x: students[x.student_id].full_name if x.student_id in students else ""):
        s, a = students.get(e.student_id), marks.get(e.id)
        rows.append({"enrollment_id": str(e.id), "student_no": s.student_no if s else None,
                     "student_name": s.full_name if s else None,
                     "status": a.status if a else None, "remarks": a.remarks if a else None,
                     "percent": attendance_percent(counts.get(e.id, {}))})
    class_days = (batch.class_days or "").split(",")
    return {"batch_code": batch.batch_code, "class_date": class_date, "start_date": batch.start_date,
            "end_date": batch.end_date, "class_days": batch.class_days,
            "is_class_day": not batch.class_days or WEEKDAY_CODES[class_date.weekday()] in class_days,
            "marked": len(marks), "rows": rows}


@router.put("/attendance")
def mark_attendance(payload: AttendanceIn, db: Session = Depends(get_db),
                    ctx: AuditContext = Depends(request_context), user: User = Depends(require_permission(EDIT))):
    batch = _owned(db, m.Batch, uuid.UUID(payload.batch_id), "Batch")
    if payload.class_date > date.today():
        raise HTTPException(400, "Attendance cannot be marked for a future date.")
    if not batch.start_date <= payload.class_date <= batch.end_date:
        raise HTTPException(400, f"Batch {batch.batch_code} runs {batch.start_date:%d-%b-%Y} to "
                                 f"{batch.end_date:%d-%b-%Y}; {payload.class_date:%d-%b-%Y} is outside it.")
    roster = {e.id for e in _roster(db, batch)}
    existing = {a.enrollment_id: a for a in db.scalars(select(m.Attendance).where(
        m.Attendance.batch_id == batch.id, m.Attendance.class_date == payload.class_date))}
    saved = cleared = 0
    for mark in payload.marks:
        eid = uuid.UUID(mark.enrollment_id)
        if eid not in roster:
            raise HTTPException(400, "One of the students is not in this batch.")
        row = existing.get(eid)
        if mark.status is None:
            if row is not None:      # unmarked again: the class mark is withdrawn
                db.delete(row)
                cleared += 1
            continue
        if row is None:
            row = m.Attendance(company_id=batch.company_id, batch_id=batch.id, enrollment_id=eid,
                               class_date=payload.class_date, created_by=user.id)
            db.add(row)
        row.status, row.remarks, row.updated_by = mark.status, _blank(mark.remarks), user.id
        saved += 1
    audit.record(db, ctx, action="attendance", module="school", entity="school_batch", entity_id=batch.id,
                 company_id=batch.company_id,
                 new_values={"class_date": payload.class_date, "marked": saved, "cleared": cleared})
    _save(db, "attendance")
    return attendance_sheet(batch.id, payload.class_date, db=db, user=user)


@router.get("/attendance/register")
def attendance_register(batch_id: uuid.UUID, db: Session = Depends(get_db),
                        user: User = Depends(require_permission(VIEW))):
    """Per student: classes present, late, absent, on leave, and the percentage."""
    batch = _owned(db, m.Batch, batch_id, "Batch")
    enrollments = _roster(db, batch)
    students = {s.id: s for s in db.scalars(select(m.Student).where(
        m.Student.id.in_({e.student_id for e in enrollments})))} if enrollments else {}
    counts = attendance_counts(db, [e.id for e in enrollments])
    dates = [d for (d,) in db.execute(select(m.Attendance.class_date).where(m.Attendance.batch_id == batch.id)
                                      .group_by(m.Attendance.class_date).order_by(m.Attendance.class_date))]
    rows = []
    for e in sorted(enrollments, key=lambda x: students[x.student_id].full_name if x.student_id in students else ""):
        s, c = students.get(e.student_id), counts.get(e.id, {})
        rows.append({"enrollment_id": str(e.id), "student_no": s.student_no if s else None,
                     "student_name": s.full_name if s else None,
                     "present": c.get("PRESENT", 0), "late": c.get("LATE", 0), "absent": c.get("ABSENT", 0),
                     "leave": c.get("LEAVE", 0), "percent": attendance_percent(c)})
    return {"batch_code": batch.batch_code, "classes_marked": len(dates), "dates": dates, "rows": rows}
