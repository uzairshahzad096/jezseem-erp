"use client";

import { useState } from "react";
import { Wallet } from "lucide-react";
import { ListScreen, type ListColumn } from "@/components/calibration/ListScreen";
import { EnrollmentForm, PaymentForm, useSchoolLookups } from "@/components/school/forms";
import { SchoolBadge } from "@/components/school/ui";
import { gridDate } from "@/components/ui/grid";
import { pkr, type Enrollment } from "@/lib/school";

const COLUMNS: ListColumn<Enrollment>[] = [
  { key: "student_name", label: "Student", render: (r) => <span className="whitespace-nowrap"><span className="text-faint">{r.student_no}</span> <b className="font-medium">{r.student_name}</b></span> },
  { key: "batch_code", label: "Batch" },
  { key: "course_name", label: "Course" },
  { key: "enroll_date", label: "Enrolled", render: (r) => gridDate(r.enroll_date) },
  { key: "net_fee", label: "Fee", numeric: true, render: (r) => pkr(r.net_fee) },
  { key: "paid", label: "Paid", numeric: true, render: (r) => <span className="text-success">{pkr(r.paid)}</span> },
  { key: "balance", label: "Due", numeric: true, render: (r) => (r.balance > 0 ? <b className="text-rose">{pkr(r.balance)}</b> : <span className="text-faint">0</span>) },
  { key: "attendance_percent", label: "Attendance", numeric: true,
    render: (r) => (r.attendance_percent == null ? <span className="text-faint">—</span>
      : <b className={r.attendance_percent >= 75 ? "text-success" : "text-rose"}>{r.attendance_percent}%</b>) },
  { key: "status", label: "Status", render: (r) => <SchoolBadge status={r.status} /> },
  { key: "certificate_no", label: "Certificate", render: (r) => r.certificate_no ?? "—" },
];

export default function SchoolEnrollmentsPage() {
  const lookups = useSchoolLookups();
  const [editing, setEditing] = useState<Enrollment | "new" | null>(null);
  const [paying, setPaying] = useState<Enrollment | null>(null);
  const [reload, setReload] = useState(0);
  const [filter, setFilter] = useState("");
  const refresh = () => setReload((n) => n + 1);
  const query = filter === "OWING" ? "&owing=true" : filter ? `&status=${filter}` : "";
  return (
    <ListScreen<Enrollment> title="JOSE Enrollments" subtitle="Which student is in which batch, the fee agreed, what is paid and what is due."
      endpoint="/school/enrollments" storageKey="school.enrollments" columns={COLUMNS} reloadKey={reload} query={query}
      onCreate={() => setEditing("new")} onEdit={(r) => setEditing(r)} noun="Enrollment" createLabel="Enroll a student"
      actionsLabel="Fee"
      rowActions={(r) => (r.balance > 0 ? (
        <button onClick={() => setPaying(r)} className="flex items-center gap-1 whitespace-nowrap rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary hover:bg-primary/20">
          <Wallet size={12} /> Received</button>) : null)}
      toolbar={
        <div className="flex flex-wrap gap-1.5">
          {[["", "All"], ["ENROLLED", "Enrolled"], ["COMPLETED", "Completed"], ["DROPPED", "Dropped"], ["OWING", "Fee due"]].map(([v, t]) => (
            <button key={v || "all"} onClick={() => setFilter(v)}
              className={`rounded-lg px-2.5 py-1.5 text-[11.5px] font-medium ${filter === v ? "bg-primary text-on-primary" : "bg-hover text-muted hover:text-text"}`}>{t}</button>
          ))}
        </div>
      }>
      {editing && <EnrollmentForm enrollment={editing === "new" ? null : editing} lookups={lookups}
        onClose={() => setEditing(null)} onSaved={() => { setEditing(null); refresh(); }} />}
      {paying && <PaymentForm enrollment={paying} onClose={() => setPaying(null)} onSaved={() => { setPaying(null); refresh(); }} />}
    </ListScreen>
  );
}
