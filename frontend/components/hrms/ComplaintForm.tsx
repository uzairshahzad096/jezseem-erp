"use client";

import { useEffect, useState } from "react";
import { Combobox, Field, Modal, Select, TextArea, TextInput } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import {
  COMPLAINT_CATEGORIES, COMPLAINT_STATUSES, errorText, label, todayIso, type Complaint, type Employee,
} from "@/lib/hrms";

/**
 * Log or update a complaint about an employee raised by senior management
 * (owner, 24-Oct-2026). Former employees can be chosen too, so their record
 * stays complete. A complaint is never deleted: one withdrawn or found
 * baseless is set to Dismissed.
 */
export function ComplaintForm({ complaint, employeeId, employeeLabel, onClose, onSaved }: {
  complaint: Complaint | null;
  /** Opened from an employee's profile: that employee, fixed. */
  employeeId?: string;
  /** Shown for that employee before the full list has loaded. */
  employeeLabel?: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [f, setF] = useState({
    employee_id: complaint?.employee_id ?? employeeId ?? "",
    complaint_date: complaint?.complaint_date ?? todayIso(),
    raised_by: complaint?.raised_by ?? "",
    raised_by_designation: complaint?.raised_by_designation ?? "",
    category: complaint?.category ?? "CONDUCT",
    severity: complaint?.severity ?? "MEDIUM",
    subject: complaint?.subject ?? "",
    details: complaint?.details ?? "",
    action_taken: complaint?.action_taken ?? "",
    status: complaint?.status ?? "OPEN",
    resolved_on: complaint?.resolved_on ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (key: keyof typeof f, value: string) => setF((x) => ({ ...x, [key]: value }));
  const closed = f.status === "RESOLVED" || f.status === "DISMISSED";

  useEffect(() => {
    // Everyone on file, including those who have left.
    api.get<{ items: Employee[] }>("/hrms/employees?page_size=5000&sort=full_name&direction=asc")
      .then((d) => setEmployees(d.items)).catch(() => setEmployees([]));
  }, []);

  const save = async () => {
    if (!f.employee_id) { setError("Choose the employee the complaint is about."); return; }
    if (f.raised_by.trim().length < 2) { setError("Say who in senior management raised it."); return; }
    if (f.subject.trim().length < 3) { setError("Give the complaint a short subject."); return; }
    setSaving(true); setError(null);
    const body = {
      ...f, raised_by: f.raised_by.trim(), subject: f.subject.trim(),
      raised_by_designation: f.raised_by_designation.trim() || null,
      details: f.details.trim() || null, action_taken: f.action_taken.trim() || null,
      resolved_on: closed ? f.resolved_on || null : null,
    };
    try {
      if (complaint) await api.put(`/hrms/complaints/${complaint.id}`, body);
      else await api.post("/hrms/complaints", body);
      onSaved();
    } catch (err) { setError(errorText(err, "Could not save the complaint.")); } finally { setSaving(false); }
  };

  const options = employees.map((e) => ({
    value: e.id,
    label: `${e.employee_code}  ${e.full_name}${["RESIGNED", "TERMINATED"].includes(e.status) ? "  (left)" : ""}`,
  }));
  const known = complaint ? `${complaint.employee_code}  ${complaint.employee_name}` : employeeLabel;
  if (f.employee_id && known && !options.some((o) => o.value === f.employee_id)) {
    options.unshift({ value: f.employee_id, label: known });
  }

  return (
    <Modal title={complaint ? `Complaint ${complaint.complaint_number}` : "Log a complaint"} open width="lg"
      saving={saving} error={error} onClose={onClose} onSave={save} saveLabel={complaint ? "Save changes" : "Log complaint"}>
      <div className="grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        <Field label="Employee" required>
          <Combobox value={f.employee_id} options={options} placeholder="Type a name or code…"
            disabled={Boolean(employeeId) && !complaint} onChange={(v) => set("employee_id", v)} />
        </Field>
        <Field label="Complaint date" required>
          <TextInput type="date" value={f.complaint_date} max={todayIso()} onChange={(e) => set("complaint_date", e.target.value)} />
        </Field>
        <Field label="Raised by (senior management)" required>
          <TextInput value={f.raised_by} placeholder="e.g. Imran Ali" onChange={(e) => set("raised_by", e.target.value)} />
        </Field>
        <Field label="Their designation">
          <TextInput value={f.raised_by_designation} placeholder="e.g. CEO, GM Sales"
            onChange={(e) => set("raised_by_designation", e.target.value)} />
        </Field>
        <Field label="Category">
          <Select value={f.category} onChange={(e) => set("category", e.target.value)}
            options={COMPLAINT_CATEGORIES.map((c) => ({ value: c, label: label(c) }))} />
        </Field>
        <Field label="Severity">
          <Select value={f.severity} onChange={(e) => set("severity", e.target.value)}
            options={["LOW", "MEDIUM", "HIGH"].map((c) => ({ value: c, label: label(c) }))} />
        </Field>
      </div>
      <div className="mt-4 grid gap-4">
        <Field label="Subject" required>
          <TextInput value={f.subject} placeholder="One line, e.g. Rude to a customer at the Lahore visit"
            onChange={(e) => set("subject", e.target.value)} />
        </Field>
        <Field label="Details">
          <TextArea rows={4} value={f.details} onChange={(e) => set("details", e.target.value)} />
        </Field>
        <Field label="Action taken">
          <TextArea rows={3} value={f.action_taken} placeholder="Warning letter, meeting, fine…"
            onChange={(e) => set("action_taken", e.target.value)} />
        </Field>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 max-sm:grid-cols-1">
        <Field label="Status">
          <Select value={f.status} onChange={(e) => set("status", e.target.value)}
            options={COMPLAINT_STATUSES.map((c) => ({ value: c, label: label(c) }))} />
        </Field>
        {closed && (
          <Field label={f.status === "RESOLVED" ? "Resolved on" : "Dismissed on"}>
            <TextInput type="date" value={f.resolved_on} min={f.complaint_date} max={todayIso()}
              onChange={(e) => set("resolved_on", e.target.value)} />
          </Field>
        )}
      </div>
      <p className="mb-0 mt-3 text-[11px] text-faint">
        Complaints are confidential: only Administrators see them. They are never deleted — set a withdrawn or
        baseless one to Dismissed. Resolving needs the action taken filled in.
      </p>
    </Modal>
  );
}
