"use client";

import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import { Combobox, Field, Modal, TextArea, TextInput } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import {
  REHIRE_LABEL, REVIEW_AREAS, errorText, fmtDate, label, todayIso, type Employee, type ExitReview,
} from "@/lib/hrms";

type Area = (typeof REVIEW_AREAS)[number][0];

/** Five stars; clicking the lit star again clears the rating. */
export function Stars({ value, onChange, size = 18 }: { value: number | null; onChange?: (v: number | null) => void; size?: number }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" disabled={!onChange} aria-label={`${n} of 5`}
          onClick={() => onChange?.(value === n ? null : n)}
          className={onChange ? "cursor-pointer" : "cursor-default"}>
          <Star size={size} className={value && n <= value ? "fill-amber text-amber" : "text-line"} />
        </button>
      ))}
    </span>
  );
}

/**
 * Senior management's remarks on an employee who resigned or was terminated
 * (owner, 24-Oct-2026): a 1-5 rating for behaviour, discipline, punctuality,
 * work quality and honesty, whether they would be taken back, and comments.
 */
export function ExitReviewForm({ review, employeeId, employeeLabel, onClose, onSaved }: {
  review: ExitReview | null;
  employeeId?: string;
  employeeLabel?: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [leavers, setLeavers] = useState<Employee[]>([]);
  const [f, setF] = useState({
    employee_id: review?.employee_id ?? employeeId ?? "",
    review_date: review?.review_date ?? todayIso(),
    reviewer_name: review?.reviewer_name ?? "",
    reviewer_designation: review?.reviewer_designation ?? "",
    rehire: review?.rehire ?? "",
    comments: review?.comments ?? "",
  });
  const [ratings, setRatings] = useState<Record<Area, number | null>>(() => Object.fromEntries(
    REVIEW_AREAS.map(([k]) => [k, review ? review[k] : null])) as Record<Area, number | null>);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (key: keyof typeof f, value: string) => setF((x) => ({ ...x, [key]: value }));

  useEffect(() => {
    // Only people who have left can be reviewed.
    api.get<{ items: Employee[] }>("/hrms/employees?page_size=5000&status=RESIGNED&status=TERMINATED&sort=full_name&direction=asc")
      .then((d) => setLeavers(d.items)).catch(() => setLeavers([]));
  }, []);

  const options = leavers.map((e) => ({
    value: e.id, label: `${e.employee_code}  ${e.full_name} — ${label(e.status)} ${fmtDate(e.separation_date)}`,
  }));
  const known = review ? `${review.employee_code}  ${review.employee_name}` : employeeLabel;
  if (f.employee_id && known && !options.some((o) => o.value === f.employee_id)) {
    options.unshift({ value: f.employee_id, label: known });
  }

  const save = async () => {
    if (!f.employee_id) { setError("Choose the employee who left."); return; }
    if (f.reviewer_name.trim().length < 2) { setError("Say who in senior management is giving the remarks."); return; }
    if (!f.rehire) { setError("Say whether the company would take this person back."); return; }
    if (f.comments.trim().length < 5) { setError("Write the comments about this person."); return; }
    setSaving(true); setError(null);
    const body = { ...f, ...ratings, reviewer_name: f.reviewer_name.trim(),
                   reviewer_designation: f.reviewer_designation.trim() || null, comments: f.comments.trim() };
    try {
      if (review) await api.put(`/hrms/exit-reviews/${review.id}`, body);
      else await api.post("/hrms/exit-reviews", body);
      onSaved();
    } catch (err) { setError(errorText(err, "Could not save the remarks.")); } finally { setSaving(false); }
  };

  return (
    <Modal title={review ? "Leaving remarks" : "Add leaving remarks"} open width="lg" saving={saving} error={error}
      onClose={onClose} onSave={save} saveLabel={review ? "Save changes" : "Save remarks"}>
      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        <Field label="Employee who left" required>
          <Combobox value={f.employee_id} options={options} placeholder="Type a name or code…"
            emptyMessage="No one has been recorded as leaving yet."
            disabled={Boolean(employeeId) && !review} onChange={(v) => set("employee_id", v)} />
        </Field>
        <Field label="Date" required>
          <TextInput type="date" value={f.review_date} max={todayIso()} onChange={(e) => set("review_date", e.target.value)} />
        </Field>
        <Field label="Given by (senior management)" required>
          <TextInput value={f.reviewer_name} placeholder="e.g. Imran Ali" onChange={(e) => set("reviewer_name", e.target.value)} />
        </Field>
        <Field label="Their designation">
          <TextInput value={f.reviewer_designation} placeholder="e.g. CEO, Director"
            onChange={(e) => set("reviewer_designation", e.target.value)} />
        </Field>
      </div>

      <div className="mt-5 rounded-xl border border-line">
        <div className="border-b border-line px-4 py-2.5 text-[12.5px] font-semibold">
          Ratings <span className="font-normal text-faint">— 1 poor to 5 excellent; leave blank if not known</span>
        </div>
        <div className="grid grid-cols-2 gap-x-8 gap-y-2.5 px-4 py-3 max-sm:grid-cols-1">
          {REVIEW_AREAS.map(([key, text]) => (
            <div key={key} className="flex items-center justify-between gap-3 text-[12.8px]">
              <span>{text}</span>
              <Stars value={ratings[key]} onChange={(v) => setRatings((r) => ({ ...r, [key]: v }))} />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <div className="mb-1.5 text-[12px] font-medium text-muted">Would the company take this person back? <span className="text-rose">*</span></div>
        <div className="flex flex-wrap gap-2">
          {(["YES", "CONDITIONAL", "NO"] as const).map((v) => (
            <button key={v} type="button" onClick={() => set("rehire", v)}
              className={`rounded-lg border px-3.5 py-2 text-[12.5px] font-medium transition-colors ${f.rehire === v
                ? v === "YES" ? "border-success bg-success/10 text-success"
                  : v === "NO" ? "border-rose bg-rose/10 text-rose" : "border-amber bg-amber/10 text-amber"
                : "border-line text-muted hover:bg-hover"}`}>
              {REHIRE_LABEL[v]}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <Field label="Comments — behaviour, discipline, conduct, anything to remember" required>
          <TextArea rows={5} value={f.comments} onChange={(e) => set("comments", e.target.value)} />
        </Field>
      </div>
      <p className="mb-0 mt-3 text-[11px] text-faint">
        Confidential: only Administrators see leaving remarks. Each manager can add their own; remarks are kept, not deleted.
      </p>
    </Modal>
  );
}
