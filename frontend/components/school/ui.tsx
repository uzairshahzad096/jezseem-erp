"use client";

import { useEffect, useState } from "react";
import { Ban, Plus, Wallet } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { ReasonDialog } from "@/components/finance/ui";
import { gridDate } from "@/components/ui/grid";
import { api } from "@/lib/api";
import { SCHOOL_TONE, pkr, type Enrollment, type Payment, type Student } from "@/lib/school";
import { EnrollmentForm, PaymentForm, StudentForm, useSchoolLookups } from "./forms";

export function SchoolBadge({ status, text }: { status: string; text?: string }) {
  return (
    <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-[3px] text-[11px] font-semibold ${SCHOOL_TONE[status] ?? "bg-hover text-muted"}`}>
      {text ?? status.charAt(0) + status.slice(1).toLowerCase()}
    </span>
  );
}

/** The school's key figures, for the top of the Students page. */
export function SchoolSummary() {
  const [s, setS] = useState<{ students: number; running_batches: number; enrolled_now: number; collected_month: number; outstanding: number } | null>(null);
  useEffect(() => { api.get<typeof s>("/school/summary").then(setS).catch(() => setS(null)); }, []);
  if (!s) return null;
  const item = (label: string, value: string, tone = "") => (
    <span className="whitespace-nowrap rounded-lg bg-hover/70 px-3 py-1.5 text-[11.5px] text-muted">{label} <b className={`text-[12.5px] ${tone || "text-text"}`}>{value}</b></span>
  );
  return (
    <div className="flex flex-wrap gap-1.5">
      {item("Students", String(s.students))}
      {item("Running batches", String(s.running_batches))}
      {item("Studying now", String(s.enrolled_now))}
      {item("Fees this month", `PKR ${pkr(s.collected_month)}`, "text-success")}
      {item("Fees due", `PKR ${pkr(s.outstanding)}`, s.outstanding > 0 ? "text-rose" : "")}
    </div>
  );
}

/** A receipt that can be cancelled (with a reason), never deleted. */
export function CancelReceipt({ payment, onDone }: { payment: Payment; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  if (payment.status === "CANCELLED") return null;
  return (
    <>
      <button onClick={() => setOpen(true)} title="Cancel this receipt" aria-label="Cancel receipt"
        className="rounded-md p-1 text-faint hover:bg-rose/10 hover:text-rose"><Ban size={13} /></button>
      {open && (
        <ReasonDialog open title={`Cancel receipt ${payment.receipt_no}`} confirmLabel="Cancel receipt" label="Why is it being cancelled?"
          onClose={() => setOpen(false)}
          onConfirm={async (reason) => { await api.post(`/school/payments/${payment.id}/cancel`, { reason }); setOpen(false); onDone(); }}>
          <p className="m-0 text-[12.5px] text-muted">PKR {pkr(payment.amount)} received on {gridDate(payment.payment_date)} will no longer count. The receipt stays on record as cancelled.</p>
        </ReasonDialog>
      )}
    </>
  );
}

/** One student's file: details, courses, fees paid and due. */
export function StudentProfile({ student, onClose, onChanged }: { student: Student; onClose: () => void; onChanged: () => void }) {
  const lookups = useSchoolLookups();
  const [current, setCurrent] = useState(student);
  const [rows, setRows] = useState<Enrollment[] | null>(null);
  const [mode, setMode] = useState<null | "edit" | "enroll" | { edit: Enrollment } | { pay: Enrollment }>(null);
  const load = () => api.get<{ items: Enrollment[] }>(`/school/enrollments?student_id=${student.id}&page_size=200`)
    .then((d) => setRows(d.items)).catch(() => setRows([]));
  useEffect(() => { load(); }, [student.id]);  // eslint-disable-line react-hooks/exhaustive-deps
  const done = () => { setMode(null); load(); onChanged(); };
  const due = (rows ?? []).reduce((t, e) => t + e.balance, 0);
  const fact = (label: string, value: string | null | undefined) => (
    <div><div className="text-[11px] text-faint">{label}</div><div className="text-[12.8px]">{value || "—"}</div></div>
  );
  return (
    <>
      <Modal title={`${current.student_no}  ${current.full_name}`} open={mode === null} width="lg" onClose={onClose}>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button onClick={() => setMode("edit")} className="rounded-lg bg-hover px-3 py-1.5 text-[12.5px] font-medium text-muted hover:text-text">Edit details</button>
          <button onClick={() => setMode("enroll")} className="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-[12.5px] font-medium text-on-primary"><Plus size={13} /> Enroll in a batch</button>
          {due > 0 && <span className="ml-auto text-[12.5px]">Fees due <b className="text-rose">PKR {pkr(due)}</b></span>}
        </div>
        <div className="grid grid-cols-3 gap-x-6 gap-y-3 rounded-xl border border-line p-4 max-sm:grid-cols-1">
          {fact("Father's name", current.father_name)}
          {fact("CNIC", current.cnic)}
          {fact("Phone", current.phone)}
          {fact("Email", current.email)}
          {fact("City", current.city)}
          {fact("Education", current.education)}
          {fact("Works / studies at", current.organization)}
          {fact("Date of birth", current.date_of_birth ? gridDate(current.date_of_birth) : null)}
          {fact("Status", current.is_active ? "Active" : "Not active")}
        </div>

        <h4 className="mb-2 mt-5 text-[13px] font-semibold">Courses and fees</h4>
        {rows === null ? <p className="text-[12px] text-faint">Loading…</p> : rows.length === 0 ? (
          <p className="m-0 rounded-xl border border-line px-4 py-3 text-[12px] text-faint">Not enrolled in any batch yet.</p>
        ) : rows.map((e) => (
          <div key={e.id} className="mb-3 rounded-xl border border-line">
            <div className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5 text-[12.5px]">
              <b>{e.batch_code}</b> <span>{e.course_name}</span>
              <span className="text-faint">{e.batch_start ? gridDate(e.batch_start) : ""} – {e.batch_end ? gridDate(e.batch_end) : ""}</span>
              <SchoolBadge status={e.status} />
              {e.certificate_no && <span className="text-faint">Certificate {e.certificate_no}{e.result ? ` · ${e.result}` : ""}</span>}
              <span className="ml-auto flex items-center gap-2">
                <button onClick={() => setMode({ edit: e })} className="text-[12px] text-primary hover:underline">Edit</button>
                {e.balance > 0 && (
                  <button onClick={() => setMode({ pay: e })}
                    className="flex items-center gap-1 rounded-md bg-primary/10 px-2 py-1 text-[11.5px] font-medium text-primary hover:bg-primary/20">
                    <Wallet size={12} /> Fee received</button>
                )}
              </span>
            </div>
            <div className="flex flex-wrap gap-x-6 px-4 py-2 text-[12px] text-muted">
              <span>Fee {pkr(e.fee)}{e.discount ? ` − discount ${pkr(e.discount)}` : ""} = <b className="text-text">{pkr(e.net_fee)}</b></span>
              <span>Paid <b className="text-success">{pkr(e.paid)}</b></span>
              <span>Due <b className={e.balance > 0 ? "text-rose" : "text-text"}>{pkr(e.balance)}</b></span>
              <span>Attendance <b className={e.attendance_percent == null ? "text-faint" : e.attendance_percent >= 75 ? "text-success" : "text-rose"}>
                {e.attendance_percent == null ? "not marked yet" : `${e.attendance_percent}%`}</b>
                {e.classes_marked > 0 && <span className="text-faint"> ({e.classes_marked} classes)</span>}</span>
            </div>
            {e.payments.length > 0 && (
              <table className="w-full border-collapse border-t border-line text-[12px]">
                <tbody>
                  {e.payments.map((p) => (
                    <tr key={p.id} className={`border-b border-line last:border-0 ${p.status === "CANCELLED" ? "text-faint line-through" : ""}`}>
                      <td className="px-4 py-1.5 font-medium">{p.receipt_no}</td>
                      <td className="px-2 py-1.5">{gridDate(p.payment_date)}</td>
                      <td className="px-2 py-1.5">{p.method.charAt(0) + p.method.slice(1).toLowerCase()}{p.reference ? ` · ${p.reference}` : ""}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums">{pkr(p.amount)}</td>
                      <td className="w-10 px-2 py-1.5 text-right">{p.status === "CANCELLED"
                        ? <span title={p.cancel_reason ?? ""} className="no-underline">cancelled</span>
                        : <CancelReceipt payment={p} onDone={done} />}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ))}
      </Modal>
      {mode === "edit" && <StudentForm student={current} onClose={() => setMode(null)}
        onSaved={(s) => { setCurrent(s); setMode(null); onChanged(); }} />}
      {mode === "enroll" && <EnrollmentForm enrollment={null} studentId={current.id} studentLabel={`${current.student_no}  ${current.full_name}`}
        lookups={lookups} onClose={() => setMode(null)} onSaved={done} />}
      {mode && typeof mode === "object" && "edit" in mode && <EnrollmentForm enrollment={mode.edit} lookups={lookups}
        onClose={() => setMode(null)} onSaved={done} />}
      {mode && typeof mode === "object" && "pay" in mode && <PaymentForm enrollment={mode.pay} onClose={() => setMode(null)} onSaved={done} />}
    </>
  );
}
