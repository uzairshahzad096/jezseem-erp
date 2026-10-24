"use client";

import { useState } from "react";
import { ListScreen, type ListColumn } from "@/components/calibration/ListScreen";
import { CancelReceipt, SchoolBadge } from "@/components/school/ui";
import { gridDate } from "@/components/ui/grid";
import { pkr, type Payment } from "@/lib/school";

const COLUMNS: ListColumn<Payment>[] = [
  { key: "receipt_no", label: "Receipt" },
  { key: "payment_date", label: "Date", render: (r) => gridDate(r.payment_date) },
  { key: "student_name", label: "Student", render: (r) => <span className="whitespace-nowrap"><span className="text-faint">{r.student_no}</span> <b className="font-medium">{r.student_name}</b></span> },
  { key: "batch_code", label: "Batch" },
  { key: "course_name", label: "Course" },
  { key: "method", label: "Received by", render: (r) => r.method.charAt(0) + r.method.slice(1).toLowerCase() + (r.reference ? ` · ${r.reference}` : "") },
  { key: "amount", label: "Amount", numeric: true,
    render: (r) => <span className={r.status === "CANCELLED" ? "text-faint line-through" : "font-medium"}>{pkr(r.amount)}</span> },
  { key: "status", label: "Status", render: (r) => <span title={r.cancel_reason ?? ""}><SchoolBadge status={r.status} /></span> },
];

/** Fees received for JOSE courses. Recorded from a student's file or the Enrollments list. */
export default function SchoolPaymentsPage() {
  const [reload, setReload] = useState(0);
  return (
    <ListScreen<Payment> title="JOSE Fee Payments" subtitle="Every fee receipt. A wrong one is cancelled with a reason, never deleted."
      endpoint="/school/payments" storageKey="school.payments" columns={COLUMNS} reloadKey={reload}
      noun="Receipt" actionsLabel="Cancel"
      rowActions={(r) => <CancelReceipt payment={r} onDone={() => setReload((n) => n + 1)} />}
      footnote={<>To record a fee, open the student (Students) or use <b>Received</b> on the Enrollments list.</>} />
  );
}
