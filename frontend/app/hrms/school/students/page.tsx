"use client";

import { useState } from "react";
import { ListScreen, type ListColumn } from "@/components/calibration/ListScreen";
import { StudentForm } from "@/components/school/forms";
import { SchoolSummary, StudentProfile } from "@/components/school/ui";
import { pkr, type Student } from "@/lib/school";

const COLUMNS: ListColumn<Student>[] = [
  { key: "student_no", label: "Student No." },
  { key: "full_name", label: "Name", render: (r) => <b className="font-medium">{r.full_name}</b> },
  { key: "phone", label: "Phone", render: (r) => r.phone ?? "—" },
  { key: "organization", label: "Works / studies at", render: (r) => r.organization ?? "—" },
  { key: "city", label: "City", render: (r) => r.city ?? "—" },
  { key: "courses", label: "Courses", numeric: true },
  { key: "balance", label: "Fees due", numeric: true,
    render: (r) => (r.balance > 0 ? <b className="text-rose">{pkr(r.balance)}</b> : <span className="text-faint">0</span>) },
  { key: "is_active", label: "Active", value: (r) => (r.is_active ? "Yes" : "No"),
    render: (r) => (r.is_active ? <span className="text-primary">Yes</span> : <span className="text-faint">No</span>) },
];

/** JOSE — Jezseem School of Excellence: the students (owner, 24-Oct-2026). */
export default function SchoolStudentsPage() {
  const [editing, setEditing] = useState<"new" | null>(null);
  const [open, setOpen] = useState<Student | null>(null);
  const [reload, setReload] = useState(0);
  const refresh = () => setReload((n) => n + 1);
  return (
    <ListScreen<Student> title="JOSE Students" subtitle="Jezseem School of Excellence — students, their courses and fees."
      endpoint="/school/students" storageKey="school.students" columns={COLUMNS} reloadKey={reload}
      onCreate={() => setEditing("new")} onEdit={(r) => setOpen(r)} noun="Student" createLabel="New student"
      toolbar={<SchoolSummary key={reload} />}
      footnote={<>Open a student to enroll them in a batch and record fees received. Fees are kept here in the school, not posted to the accounts.</>}>
      {editing && <StudentForm student={null} onClose={() => setEditing(null)}
        onSaved={(s) => { setEditing(null); refresh(); setOpen(s); }} />}
      {open && <StudentProfile student={open} onClose={() => setOpen(null)} onChanged={refresh} />}
    </ListScreen>
  );
}
