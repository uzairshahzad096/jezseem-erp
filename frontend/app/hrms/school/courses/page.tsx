"use client";

import { useState } from "react";
import { ListScreen, type ListColumn } from "@/components/calibration/ListScreen";
import { CourseForm } from "@/components/school/forms";
import { pkr, type Course } from "@/lib/school";

const COLUMNS: ListColumn<Course>[] = [
  { key: "code", label: "Code" },
  { key: "name", label: "Course", render: (r) => <b className="font-medium">{r.name}</b> },
  { key: "duration_value", label: "Duration", value: (r) => `${r.duration_value} ${r.duration_unit.toLowerCase()}`,
    render: (r) => `${r.duration_value} ${r.duration_unit.toLowerCase()}` },
  { key: "fee", label: "Standard fee", numeric: true, render: (r) => pkr(r.fee) },
  { key: "batches", label: "Batches", numeric: true },
  { key: "description", label: "What it covers", render: (r) => <span className="block max-w-[380px] truncate" title={r.description ?? ""}>{r.description ?? "—"}</span> },
  { key: "is_active", label: "Offered", value: (r) => (r.is_active ? "Yes" : "No"),
    render: (r) => (r.is_active ? <span className="text-primary">Yes</span> : <span className="text-faint">No</span>) },
];

export default function SchoolCoursesPage() {
  const [editing, setEditing] = useState<Course | "new" | null>(null);
  const [reload, setReload] = useState(0);
  return (
    <ListScreen<Course> title="JOSE Courses" subtitle="What the school teaches: duration and standard fee."
      endpoint="/school/courses" storageKey="school.courses" columns={COLUMNS} reloadKey={reload}
      onCreate={() => setEditing("new")} onEdit={(r) => setEditing(r)} noun="Course" createLabel="New course">
      {editing && <CourseForm course={editing === "new" ? null : editing} onClose={() => setEditing(null)}
        onSaved={() => { setEditing(null); setReload((n) => n + 1); }} />}
    </ListScreen>
  );
}
