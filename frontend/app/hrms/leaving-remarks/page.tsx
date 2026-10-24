"use client";

import { useState } from "react";
import { ListScreen, type ListColumn } from "@/components/calibration/ListScreen";
import { ExitReviewForm, Stars } from "@/components/hrms/ExitReviewForm";
import { HrBadge } from "@/components/hrms/ui";
import { gridDate } from "@/components/ui/grid";
import { REHIRE_LABEL, label, type ExitReview } from "@/lib/hrms";

const COLUMNS: ListColumn<ExitReview>[] = [
  { key: "employee_name", label: "Employee", value: (r) => r.employee_name ?? "",
    render: (r) => <span className="whitespace-nowrap"><span className="text-faint">{r.employee_code}</span> <b className="font-medium">{r.employee_name}</b></span> },
  { key: "employee_status", label: "Left as", value: (r) => label(r.employee_status),
    render: (r) => <span className="whitespace-nowrap">{label(r.employee_status)}{r.separation_date ? <span className="text-faint"> · {gridDate(r.separation_date)}</span> : ""}</span> },
  { key: "average", label: "Overall", numeric: true,
    render: (r) => (r.average ? <span className="inline-flex items-center gap-1.5"><Stars value={Math.round(r.average)} size={13} /> {r.average}</span> : "—") },
  { key: "rehire", label: "Rehire?", value: (r) => REHIRE_LABEL[r.rehire], render: (r) => <HrBadge status={r.rehire} text={REHIRE_LABEL[r.rehire]} /> },
  { key: "comments", label: "Comments", render: (r) => <span className="block max-w-[360px] truncate" title={r.comments}>{r.comments}</span> },
  { key: "reviewer_name", label: "Given by", value: (r) => r.reviewer_name,
    render: (r) => <span className="whitespace-nowrap">{r.reviewer_name}{r.reviewer_designation ? <span className="text-faint"> · {r.reviewer_designation}</span> : ""}</span> },
  { key: "review_date", label: "Date", render: (r) => <span className="whitespace-nowrap">{gridDate(r.review_date)}</span> },
];

export default function LeavingRemarksPage() {
  const [editing, setEditing] = useState<ExitReview | "new" | null>(null);
  const [reload, setReload] = useState(0);
  const [rehire, setRehire] = useState("");

  return (
    <ListScreen<ExitReview> title="Leaving Remarks"
      subtitle="Senior management's comments on people who resigned or were terminated — behaviour, discipline and whether to take them back."
      endpoint="/hrms/exit-reviews" storageKey="hrms.exit-reviews" columns={COLUMNS}
      onCreate={() => setEditing("new")} onEdit={(r) => setEditing(r)} reloadKey={reload}
      noun="Remark" createLabel="Add remarks" query={rehire ? `&rehire=${rehire}` : ""}
      toolbar={
        <div className="flex flex-wrap gap-1.5">
          {["", "YES", "CONDITIONAL", "NO"].map((v) => (
            <button key={v || "all"} onClick={() => setRehire(v)}
              className={`rounded-lg px-2.5 py-1.5 text-[11.5px] font-medium transition-colors ${rehire === v
                ? "bg-primary text-on-primary" : "bg-hover text-muted hover:text-text"}`}>
              {v ? REHIRE_LABEL[v] : "All"}
            </button>
          ))}
        </div>
      }
      footnote={<>Confidential: only Administrators see these. Remarks can be given only for someone recorded as having left
        (Employees → profile → Record leaving).</>}>
      {editing && <ExitReviewForm review={editing === "new" ? null : editing} onClose={() => setEditing(null)}
        onSaved={() => { setEditing(null); setReload((n) => n + 1); }} />}
    </ListScreen>
  );
}
