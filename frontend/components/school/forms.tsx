"use client";

import { useEffect, useState } from "react";
import { Combobox, Field, Modal, Select, TextArea, TextInput, Toggle } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { errorText } from "@/lib/finance";
import {
  WEEKDAYS, pkr, type Batch, type Course, type Enrollment, type SchoolLookups, type Student,
} from "@/lib/school";

const todayIso = () => new Date().toISOString().slice(0, 10);

/** The school's dropdown data: courses, batches and trainers. */
export function useSchoolLookups() {
  const [data, setData] = useState<SchoolLookups | null>(null);
  useEffect(() => { api.get<SchoolLookups>("/school/lookups").then(setData).catch(() => setData(null)); }, []);
  return data;
}

async function saveTo(path: string, id: string | undefined, body: unknown) {
  return id ? api.put(`${path}/${id}`, body) : api.post(path, body);
}

/* ---------------------------------------------------------------- course */

export function CourseForm({ course, onClose, onSaved }: { course: Course | null; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({
    code: course?.code ?? "", name: course?.name ?? "", description: course?.description ?? "",
    duration_value: course ? String(course.duration_value) : "", duration_unit: course?.duration_unit ?? "WEEKS",
    fee: course ? String(course.fee) : "", is_active: course?.is_active ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const save = async () => {
    setSaving(true); setError(null);
    try {
      await saveTo("/school/courses", course?.id, { ...f, duration_value: Number(f.duration_value) || 0, fee: f.fee || "0" });
      onSaved();
    } catch (err) { setError(errorText(err, "Could not save the course.")); } finally { setSaving(false); }
  };
  return (
    <Modal title={course ? `Course ${course.code}` : "New course"} open width="lg" saving={saving} error={error}
      onClose={onClose} onSave={save}>
      <div className="grid grid-cols-[160px_1fr] gap-4 max-sm:grid-cols-1">
        <Field label="Code" required><TextInput value={f.code} placeholder="e.g. CAD1" onChange={(e) => setF({ ...f, code: e.target.value })} /></Field>
        <Field label="Course name" required><TextInput value={f.name} placeholder="e.g. Gerber AccuMark CAD Basics" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-4 max-sm:grid-cols-1">
        <Field label="Duration" required><TextInput inputMode="numeric" value={f.duration_value} onChange={(e) => setF({ ...f, duration_value: e.target.value.replace(/\D/g, "") })} /></Field>
        <Field label="In">
          <Select value={f.duration_unit} onChange={(e) => setF({ ...f, duration_unit: e.target.value })}
            options={[{ value: "DAYS", label: "Days" }, { value: "WEEKS", label: "Weeks" }, { value: "MONTHS", label: "Months" }]} />
        </Field>
        <Field label="Standard fee (PKR)" required><TextInput inputMode="decimal" value={f.fee} onChange={(e) => setF({ ...f, fee: e.target.value })} /></Field>
      </div>
      <div className="mt-4"><Field label="What it covers"><TextArea rows={3} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field></div>
      <div className="mt-4"><Toggle label="Offered (new batches can be opened)" checked={f.is_active} onChange={(v) => setF({ ...f, is_active: v })} /></div>
    </Modal>
  );
}

/* ---------------------------------------------------------------- batch */

export function BatchForm({ batch, lookups, onClose, onSaved }: {
  batch: Batch | null; lookups: SchoolLookups | null; onClose: () => void; onSaved: () => void;
}) {
  const [f, setF] = useState({
    course_id: batch?.course_id ?? "", batch_code: batch?.batch_code ?? "",
    start_date: batch?.start_date ?? "", end_date: batch?.end_date ?? "",
    days: (batch?.class_days ?? "").split(",").filter(Boolean),
    start_time: batch?.start_time ?? "", end_time: batch?.end_time ?? "",
    trainer_employee_id: batch?.trainer_employee_id ?? "", trainer_name: batch?.trainer_name ?? "",
    venue: batch?.venue ?? "", capacity: batch?.capacity ? String(batch.capacity) : "",
    fee: batch ? String(batch.fee) : "", status: batch?.status ?? "PLANNED", notes: batch?.notes ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const course = lookups?.courses.find((c) => c.id === f.course_id);
  const save = async () => {
    if (!f.course_id) { setError("Choose the course."); return; }
    if (!f.start_date || !f.end_date) { setError("Give the start and end dates."); return; }
    setSaving(true); setError(null);
    try {
      await saveTo("/school/batches", batch?.id, {
        course_id: f.course_id, batch_code: f.batch_code || null, start_date: f.start_date, end_date: f.end_date,
        class_days: f.days.join(","), start_time: f.start_time || null, end_time: f.end_time || null,
        trainer_employee_id: f.trainer_employee_id || null, trainer_name: f.trainer_employee_id ? null : f.trainer_name || null,
        venue: f.venue || null, capacity: f.capacity ? Number(f.capacity) : null,
        fee: f.fee === "" ? null : f.fee, status: f.status, notes: f.notes || null,
      });
      onSaved();
    } catch (err) { setError(errorText(err, "Could not save the batch.")); } finally { setSaving(false); }
  };
  return (
    <Modal title={batch ? `Batch ${batch.batch_code}` : "New batch"} open width="lg" saving={saving} error={error}
      onClose={onClose} onSave={save}>
      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        <Field label="Course" required>
          <Combobox value={f.course_id} placeholder="Choose a course…"
            options={(lookups?.courses ?? []).filter((c) => c.is_active || c.id === f.course_id)
              .map((c) => ({ value: c.id, label: `${c.code}  ${c.name} (${c.duration})` }))}
            onChange={(v) => setF({ ...f, course_id: v })} />
        </Field>
        <Field label="Batch code"><TextInput value={f.batch_code} placeholder="Made automatically, e.g. CAD1-2611-01"
          onChange={(e) => setF({ ...f, batch_code: e.target.value })} /></Field>
        <Field label="Starts" required><TextInput type="date" value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value })} /></Field>
        <Field label="Ends" required><TextInput type="date" value={f.end_date} min={f.start_date || undefined} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></Field>
      </div>
      <div className="mt-4">
        <div className="mb-1.5 text-[12px] font-medium text-muted">Class days</div>
        <div className="flex flex-wrap gap-1.5">
          {WEEKDAYS.map((d) => (
            <button key={d} type="button" onClick={() => setF({ ...f, days: f.days.includes(d) ? f.days.filter((x) => x !== d) : [...f.days, d] })}
              className={`rounded-lg px-3 py-1.5 text-[12px] font-medium ${f.days.includes(d) ? "bg-primary text-on-primary" : "bg-hover text-muted"}`}>
              {d.charAt(0) + d.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-4 grid grid-cols-4 gap-4 max-sm:grid-cols-2">
        <Field label="Class from"><TextInput type="time" value={f.start_time} onChange={(e) => setF({ ...f, start_time: e.target.value })} /></Field>
        <Field label="Class to"><TextInput type="time" value={f.end_time} onChange={(e) => setF({ ...f, end_time: e.target.value })} /></Field>
        <Field label="Seats"><TextInput inputMode="numeric" value={f.capacity} placeholder="No limit" onChange={(e) => setF({ ...f, capacity: e.target.value.replace(/\D/g, "") })} /></Field>
        <Field label="Fee (PKR)"><TextInput inputMode="decimal" value={f.fee} placeholder={course ? pkr(course.fee) : "Course fee"}
          onChange={(e) => setF({ ...f, fee: e.target.value })} /></Field>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        <Field label="Trainer (employee)">
          <Combobox value={f.trainer_employee_id} placeholder="Choose an employee, or type an outside trainer below"
            options={(lookups?.trainers ?? []).map((t) => ({ value: t.id, label: t.label }))}
            onChange={(v) => setF({ ...f, trainer_employee_id: v })} />
        </Field>
        <Field label="Outside trainer">
          <TextInput value={f.trainer_name} disabled={Boolean(f.trainer_employee_id)} placeholder="Name, if not an employee"
            onChange={(e) => setF({ ...f, trainer_name: e.target.value })} />
        </Field>
        <Field label="Venue"><TextInput value={f.venue} placeholder="e.g. JEZ FSD training room" onChange={(e) => setF({ ...f, venue: e.target.value })} /></Field>
        <Field label="Status">
          <Select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}
            options={[["PLANNED", "Planned"], ["RUNNING", "Running"], ["COMPLETED", "Completed"], ["CANCELLED", "Cancelled"]].map(([value, label]) => ({ value, label }))} />
        </Field>
      </div>
      <div className="mt-4"><Field label="Notes"><TextArea rows={2} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field></div>
      <p className="mb-0 mt-2 text-[11px] text-faint">Leave the fee empty to charge the course's standard fee.</p>
    </Modal>
  );
}

/* ---------------------------------------------------------------- student */

export function StudentForm({ student, onClose, onSaved }: { student: Student | null; onClose: () => void; onSaved: (s: Student) => void }) {
  const fields = ["full_name", "father_name", "gender", "date_of_birth", "cnic", "phone", "email", "address", "city",
                  "education", "organization", "notes"] as const;
  const [f, setF] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((k) => [k, (student?.[k] as string | null) ?? ""])));
  const [active, setActive] = useState(student?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (k: string, v: string) => setF((x) => ({ ...x, [k]: v }));
  const text = (k: string, label: string, placeholder?: string, required = false) => (
    <Field label={label} required={required}><TextInput value={f[k]} placeholder={placeholder} onChange={(e) => set(k, e.target.value)} /></Field>
  );
  const save = async () => {
    if (f.full_name.trim().length < 2) { setError("Give the student's name."); return; }
    setSaving(true); setError(null);
    try {
      const body = { ...Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v.trim() || null])), is_active: active };
      onSaved(await saveTo("/school/students", student?.id, body) as Student);
    } catch (err) { setError(errorText(err, "Could not save the student.")); } finally { setSaving(false); }
  };
  return (
    <Modal title={student ? `Student ${student.student_no}` : "New student"} open width="lg" saving={saving} error={error}
      onClose={onClose} onSave={save}>
      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        {text("full_name", "Full name", "", true)}
        {text("father_name", "Father's name")}
        <Field label="Gender">
          <Select value={f.gender} placeholder="—" onChange={(e) => set("gender", e.target.value)}
            options={[{ value: "MALE", label: "Male" }, { value: "FEMALE", label: "Female" }, { value: "OTHER", label: "Other" }]} />
        </Field>
        <Field label="Date of birth"><TextInput type="date" value={f.date_of_birth} onChange={(e) => set("date_of_birth", e.target.value)} /></Field>
        {text("cnic", "CNIC", "35202-1234567-1")}
        {text("phone", "Phone / mobile", "0300-1234567")}
        {text("email", "Email")}
        {text("city", "City")}
        {text("education", "Education", "e.g. BS Textile, Intermediate")}
        {text("organization", "Works / studies at", "e.g. a customer's company or college")}
      </div>
      <div className="mt-4 grid gap-4">
        <Field label="Address"><TextArea rows={2} value={f.address} onChange={(e) => set("address", e.target.value)} /></Field>
        <Field label="Notes"><TextArea rows={2} value={f.notes} onChange={(e) => set("notes", e.target.value)} /></Field>
        <Toggle label="Active student" checked={active} onChange={setActive} />
      </div>
    </Modal>
  );
}

/* ---------------------------------------------------------------- enrollment */

export function EnrollmentForm({ enrollment, studentId, studentLabel, lookups, onClose, onSaved }: {
  enrollment: Enrollment | null; studentId?: string; studentLabel?: string; lookups: SchoolLookups | null;
  onClose: () => void; onSaved: () => void;
}) {
  const [students, setStudents] = useState<{ value: string; label: string }[]>([]);
  const [f, setF] = useState({
    student_id: enrollment?.student_id ?? studentId ?? "", batch_id: enrollment?.batch_id ?? "",
    enroll_date: enrollment?.enroll_date ?? todayIso(), fee: enrollment ? String(enrollment.fee) : "",
    discount: enrollment ? String(enrollment.discount) : "0", status: enrollment?.status ?? "ENROLLED",
    completion_date: enrollment?.completion_date ?? "", result: enrollment?.result ?? "",
    certificate_no: enrollment?.certificate_no ?? "", notes: enrollment?.notes ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.get<{ items: Student[] }>("/school/students?page_size=5000&active_only=true")
      .then((d) => setStudents(d.items.map((s) => ({ value: s.id, label: `${s.student_no}  ${s.full_name}` })))).catch(() => {});
  }, []);
  const options = [...students];
  const known = enrollment ? `${enrollment.student_no}  ${enrollment.student_name}` : studentLabel;
  if (f.student_id && known && !options.some((o) => o.value === f.student_id)) options.unshift({ value: f.student_id, label: known });
  const batch = lookups?.batches.find((b) => b.id === f.batch_id);
  const fee = f.fee === "" ? batch?.fee ?? 0 : Number(f.fee) || 0;
  const save = async () => {
    if (!f.student_id || !f.batch_id) { setError("Choose the student and the batch."); return; }
    setSaving(true); setError(null);
    try {
      await saveTo("/school/enrollments", enrollment?.id, {
        ...f, fee: f.fee === "" ? null : f.fee, discount: f.discount || "0",
        completion_date: f.completion_date || null, result: f.result || null, certificate_no: f.certificate_no || null, notes: f.notes || null,
      });
      onSaved();
    } catch (err) { setError(errorText(err, "Could not save the enrollment.")); } finally { setSaving(false); }
  };
  return (
    <Modal title={enrollment ? `Enrollment — ${enrollment.student_name}` : "Enroll a student"} open width="lg" saving={saving} error={error}
      onClose={onClose} onSave={save}>
      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        <Field label="Student" required>
          <Combobox value={f.student_id} options={options} placeholder="Type a name or ST- number…"
            disabled={Boolean(studentId) && !enrollment} onChange={(v) => setF({ ...f, student_id: v })} />
        </Field>
        <Field label="Batch" required>
          <Combobox value={f.batch_id} placeholder="Choose a batch…"
            options={(lookups?.batches ?? []).filter((b) => b.status !== "CANCELLED" || b.id === f.batch_id)
              .map((b) => ({ value: b.id, label: `${b.batch_code}  ${b.course ?? ""} — ${b.status.toLowerCase()}` }))}
            onChange={(v) => setF({ ...f, batch_id: v, fee: "" })} />
        </Field>
        <Field label="Enrolled on" required><TextInput type="date" value={f.enroll_date} onChange={(e) => setF({ ...f, enroll_date: e.target.value })} /></Field>
        <Field label="Status">
          <Select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}
            options={[["ENROLLED", "Enrolled"], ["COMPLETED", "Completed"], ["DROPPED", "Dropped out"]].map(([value, label]) => ({ value, label }))} />
        </Field>
        <Field label="Fee (PKR)"><TextInput inputMode="decimal" value={f.fee} placeholder={batch ? `${pkr(batch.fee)} (batch fee)` : "Batch fee"}
          onChange={(e) => setF({ ...f, fee: e.target.value })} /></Field>
        <Field label="Discount (PKR)"><TextInput inputMode="decimal" value={f.discount} onChange={(e) => setF({ ...f, discount: e.target.value })} /></Field>
      </div>
      <p className="mb-0 mt-3 rounded-lg bg-hover/60 px-3 py-2 text-[12.5px]">
        Fee to pay: <b>PKR {pkr(Math.max(fee - (Number(f.discount) || 0), 0))}</b>
        {enrollment && <> · paid {pkr(enrollment.paid)} · <b className={enrollment.balance > 0 ? "text-rose" : "text-success"}>balance {pkr(enrollment.balance)}</b></>}
      </p>
      {f.status === "COMPLETED" && (
        <div className="mt-4 grid grid-cols-3 gap-4 max-sm:grid-cols-1">
          <Field label="Completed on"><TextInput type="date" value={f.completion_date} onChange={(e) => setF({ ...f, completion_date: e.target.value })} /></Field>
          <Field label="Result / grade"><TextInput value={f.result} placeholder="e.g. Passed, A" onChange={(e) => setF({ ...f, result: e.target.value })} /></Field>
          <Field label="Certificate no."><TextInput value={f.certificate_no} onChange={(e) => setF({ ...f, certificate_no: e.target.value })} /></Field>
        </div>
      )}
      <div className="mt-4"><Field label="Notes"><TextArea rows={2} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field></div>
    </Modal>
  );
}

/* ---------------------------------------------------------------- payment */

export function PaymentForm({ enrollment, onClose, onSaved }: { enrollment: Enrollment; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({ payment_date: todayIso(), amount: String(enrollment.balance || ""), method: "CASH", reference: "", notes: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const save = async () => {
    if (!(Number(f.amount) > 0)) { setError("Enter the amount received."); return; }
    setSaving(true); setError(null);
    try {
      await api.post("/school/payments", { enrollment_id: enrollment.id, ...f, reference: f.reference || null, notes: f.notes || null });
      onSaved();
    } catch (err) { setError(errorText(err, "Could not save the payment.")); } finally { setSaving(false); }
  };
  return (
    <Modal title={`Fee received — ${enrollment.student_name}`} open width="md" saving={saving} error={error}
      onClose={onClose} onSave={save} saveLabel="Save receipt">
      <p className="m-0 mb-4 text-[12.5px] text-muted">
        {enrollment.batch_code} · {enrollment.course_name} — fee {pkr(enrollment.net_fee)}, paid {pkr(enrollment.paid)},
        <b className="text-rose"> due {pkr(enrollment.balance)}</b>
      </p>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Date" required><TextInput type="date" value={f.payment_date} max={todayIso()} onChange={(e) => setF({ ...f, payment_date: e.target.value })} /></Field>
        <Field label="Amount (PKR)" required><TextInput inputMode="decimal" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></Field>
        <Field label="Received by">
          <Select value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })}
            options={[["CASH", "Cash"], ["BANK", "Bank transfer"], ["CHEQUE", "Cheque"], ["ONLINE", "Online / wallet"]].map(([value, label]) => ({ value, label }))} />
        </Field>
        <Field label="Reference"><TextInput value={f.reference} placeholder="Cheque / transaction no." onChange={(e) => setF({ ...f, reference: e.target.value })} /></Field>
      </div>
      <div className="mt-4"><Field label="Notes"><TextInput value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field></div>
    </Modal>
  );
}
