"use client";

import { useState } from "react";
import { ListScreen, type ListColumn } from "@/components/calibration/ListScreen";
import { ComplaintForm } from "@/components/hrms/ComplaintForm";
import { HrBadge } from "@/components/hrms/ui";
import { gridDate } from "@/components/ui/grid";
import { COMPLAINT_STATUSES, label, type Complaint } from "@/lib/hrms";

const COLUMNS: ListColumn<Complaint>[] = [
  { key: "complaint_number", label: "No." },
  { key: "complaint_date", label: "Date", render: (r) => <span className="whitespace-nowrap">{gridDate(r.complaint_date)}</span> },
  { key: "employee_name", label: "Employee", value: (r) => r.employee_name ?? "",
    render: (r) => (
      <span className="whitespace-nowrap">
        <span className="text-faint">{r.employee_code}</span> <b className="font-medium">{r.employee_name}</b>
        {r.employee_status && ["RESIGNED", "TERMINATED"].includes(r.employee_status) &&
          <span className="ml-1.5 text-[10.5px] text-rose">(left)</span>}
      </span>) },
  { key: "subject", label: "Subject", render: (r) => <span className="block max-w-[320px] truncate" title={r.subject}>{r.subject}</span> },
  { key: "raised_by", label: "Raised by", value: (r) => r.raised_by,
    render: (r) => <span className="whitespace-nowrap">{r.raised_by}{r.raised_by_designation ? <span className="text-faint"> · {r.raised_by_designation}</span> : ""}</span> },
  { key: "category", label: "Category", value: (r) => label(r.category), render: (r) => label(r.category) },
  { key: "severity", label: "Severity", value: (r) => label(r.severity), render: (r) => <HrBadge status={r.severity} /> },
  { key: "status", label: "Status", value: (r) => label(r.status), render: (r) => <HrBadge status={r.status} /> },
  { key: "resolved_on", label: "Closed on", render: (r) => (r.resolved_on ? gridDate(r.resolved_on) : "—") },
];

export default function ComplaintsPage() {
  const [editing, setEditing] = useState<Complaint | "new" | null>(null);
  const [reload, setReload] = useState(0);
  const [status, setStatus] = useState("");

  return (
    <ListScreen<Complaint> title="Employee Complaints"
      subtitle="Complaints about an employee raised by senior management, with the action taken. Former employees included."
      endpoint="/hrms/complaints" storageKey="hrms.complaints" columns={COLUMNS}
      onCreate={() => setEditing("new")} onEdit={(r) => setEditing(r)} reloadKey={reload}
      noun="Complaint" createLabel="Log complaint" query={status ? `&status=${status}` : ""}
      toolbar={
        <div className="flex flex-wrap gap-1.5">
          {["", ...COMPLAINT_STATUSES].map((s) => (
            <button key={s || "all"} onClick={() => setStatus(s)}
              className={`rounded-lg px-2.5 py-1.5 text-[11.5px] font-medium transition-colors ${status === s
                ? "bg-primary text-on-primary" : "bg-hover text-muted hover:text-text"}`}>
              {s ? label(s) : "All"}
            </button>
          ))}
        </div>
      }
      footnote={<>Confidential: only Administrators can see or log complaints. A complaint is never deleted — set a withdrawn
        or baseless one to <b>Dismissed</b>.</>}>
      {editing && <ComplaintForm complaint={editing === "new" ? null : editing} onClose={() => setEditing(null)}
        onSaved={() => { setEditing(null); setReload((n) => n + 1); }} />}
    </ListScreen>
  );
}
