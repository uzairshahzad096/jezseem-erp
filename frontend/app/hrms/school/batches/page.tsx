"use client";

import { useState } from "react";
import { ListScreen, type ListColumn } from "@/components/calibration/ListScreen";
import { BatchForm, useSchoolLookups } from "@/components/school/forms";
import { SchoolBadge } from "@/components/school/ui";
import { gridDate } from "@/components/ui/grid";
import { pkr, type Batch } from "@/lib/school";

const days = (s: string | null) => (s ? s.split(",").map((d) => d.charAt(0) + d.slice(1).toLowerCase()).join(", ") : "—");

const COLUMNS: ListColumn<Batch>[] = [
  { key: "batch_code", label: "Batch" },
  { key: "course_name", label: "Course", render: (r) => <b className="font-medium">{r.course_name}</b> },
  { key: "start_date", label: "Period", render: (r) => <span className="whitespace-nowrap">{gridDate(r.start_date)} – {gridDate(r.end_date)}</span> },
  { key: "class_days", label: "Class days", value: (r) => days(r.class_days), render: (r) => days(r.class_days) },
  { key: "start_time", label: "Time", render: (r) => (r.start_time ? `${r.start_time}–${r.end_time ?? ""}` : "—") },
  { key: "trainer", label: "Trainer", render: (r) => r.trainer ?? "—" },
  { key: "enrolled", label: "Students", numeric: true, render: (r) => (r.capacity ? `${r.enrolled} / ${r.capacity}` : String(r.enrolled)) },
  { key: "fee", label: "Fee", numeric: true, render: (r) => pkr(r.fee) },
  { key: "status", label: "Status", render: (r) => <SchoolBadge status={r.status} /> },
];

export default function SchoolBatchesPage() {
  const lookups = useSchoolLookups();
  const [editing, setEditing] = useState<Batch | "new" | null>(null);
  const [reload, setReload] = useState(0);
  const [status, setStatus] = useState("");
  return (
    <ListScreen<Batch> title="JOSE Batches" subtitle="Each run of a course: dates, class days and times, trainer and seats."
      endpoint="/school/batches" storageKey="school.batches" columns={COLUMNS} reloadKey={reload}
      onCreate={() => setEditing("new")} onEdit={(r) => setEditing(r)} noun="Batch" createLabel="New batch"
      query={status ? `&status=${status}` : ""}
      toolbar={
        <div className="flex flex-wrap gap-1.5">
          {["", "PLANNED", "RUNNING", "COMPLETED", "CANCELLED"].map((s) => (
            <button key={s || "all"} onClick={() => setStatus(s)}
              className={`rounded-lg px-2.5 py-1.5 text-[11.5px] font-medium ${status === s ? "bg-primary text-on-primary" : "bg-hover text-muted hover:text-text"}`}>
              {s ? s.charAt(0) + s.slice(1).toLowerCase() : "All"}
            </button>
          ))}
        </div>
      }>
      {editing && <BatchForm batch={editing === "new" ? null : editing} lookups={lookups} onClose={() => setEditing(null)}
        onSaved={() => { setEditing(null); setReload((n) => n + 1); }} />}
    </ListScreen>
  );
}
