"use client";

import { useEffect, useState } from "react";
import { CheckCheck, Loader2 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Combobox } from "@/components/ui/Modal";
import { useSchoolLookups } from "@/components/school/forms";
import { gridDate } from "@/components/ui/grid";
import { api } from "@/lib/api";
import { errorText } from "@/lib/finance";

type Mark = "PRESENT" | "ABSENT" | "LATE" | "LEAVE";
interface SheetRow { enrollment_id: string; student_no: string | null; student_name: string | null; status: Mark | null; remarks: string | null; percent: number | null }
interface Sheet { batch_code: string; start_date: string; end_date: string; class_days: string | null; is_class_day: boolean; marked: number; rows: SheetRow[] }
interface RegisterRow { enrollment_id: string; student_no: string | null; student_name: string | null; present: number; late: number; absent: number; leave: number; percent: number | null }
interface Register { batch_code: string; classes_marked: number; dates: string[]; rows: RegisterRow[] }

const MARKS: [Mark, string, string][] = [
  ["PRESENT", "Present", "bg-success text-white"],
  ["LATE", "Late", "bg-amber text-white"],
  ["ABSENT", "Absent", "bg-rose text-white"],
  ["LEAVE", "Leave", "bg-sky text-white"],
];
const todayIso = () => new Date().toISOString().slice(0, 10);
const pct = (p: number | null) => (p == null ? "—" : `${p}%`);
const pctTone = (p: number | null) => (p == null ? "text-faint" : p >= 75 ? "text-success" : p >= 50 ? "text-amber" : "text-rose");

/** JOSE student attendance: mark a batch's class, and the batch's register (owner, 24-Oct-2026). */
export default function SchoolAttendancePage() {
  const lookups = useSchoolLookups();
  const [batchId, setBatchId] = useState("");
  const [day, setDay] = useState(todayIso());
  const [sheet, setSheet] = useState<Sheet | null>(null);
  const [marks, setMarks] = useState<Record<string, { status: Mark | null; remarks: string }>>({});
  const [register, setRegister] = useState<Register | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Running batches first: those are the ones marked day to day.
  const batches = [...(lookups?.batches ?? [])].filter((b) => b.status !== "CANCELLED")
    .sort((a, b) => Number(b.status === "RUNNING") - Number(a.status === "RUNNING"));
  useEffect(() => {
    if (!batchId && batches.length) setBatchId((batches.find((b) => b.status === "RUNNING") ?? batches[0]).id);
  }, [batches.length]);  // eslint-disable-line react-hooks/exhaustive-deps

  const load = async () => {
    if (!batchId || !day) return;
    setBusy(true); setError(null); setSaved(false);
    try {
      const [s, reg] = await Promise.all([
        api.get<Sheet>(`/school/attendance?batch_id=${batchId}&class_date=${day}`),
        api.get<Register>(`/school/attendance/register?batch_id=${batchId}`),
      ]);
      setSheet(s); setRegister(reg);
      setMarks(Object.fromEntries(s.rows.map((r) => [r.enrollment_id, { status: r.status, remarks: r.remarks ?? "" }])));
    } catch (err) { setError(errorText(err, "Could not load the attendance.")); } finally { setBusy(false); }
  };
  useEffect(() => { load(); }, [batchId, day]);  // eslint-disable-line react-hooks/exhaustive-deps

  const set = (id: string, status: Mark | null) => { setSaved(false); setMarks((m) => ({ ...m, [id]: { ...m[id], status } })); };
  const save = async () => {
    setBusy(true); setError(null);
    try {
      await api.put("/school/attendance", { batch_id: batchId, class_date: day,
        marks: Object.entries(marks).map(([enrollment_id, v]) => ({ enrollment_id, status: v.status, remarks: v.remarks || null })) });
      await load(); setSaved(true);
    } catch (err) { setError(errorText(err, "Could not save the attendance.")); setBusy(false); }
  };
  const unmarked = sheet ? sheet.rows.filter((r) => !marks[r.enrollment_id]?.status).length : 0;

  return (
    <AppShell title="JOSE Attendance">
      <div className="mb-5 flex flex-wrap items-end gap-4">
        <div>
          <h1 className="m-0 text-[19px] font-semibold">Student Attendance</h1>
          <p className="m-0 text-[12px] text-muted">Mark each class of a batch. Late counts as attended; leave is excused and left out of the %.</p>
        </div>
      </div>

      <section className="mb-5 rounded-[14px] border border-line bg-surface p-5 shadow-panel">
        <div className="flex flex-wrap items-end gap-4">
          <label className="min-w-[320px] flex-1 text-[12px] font-medium text-muted">Batch
            <div className="mt-1.5"><Combobox value={batchId} placeholder="Choose a batch…"
              options={batches.map((b) => ({ value: b.id, label: `${b.batch_code}  ${b.course ?? ""} — ${b.status.toLowerCase()}` }))}
              onChange={setBatchId} /></div>
          </label>
          <label className="text-[12px] font-medium text-muted">Class date
            <input type="date" value={day} max={todayIso()} onChange={(e) => setDay(e.target.value)}
              className="mt-1.5 block rounded-lg border border-line bg-bg px-3 py-2 text-[13px] text-text outline-none focus:border-primary" />
          </label>
          {sheet && (
            <div className="pb-2 text-[12px] text-muted">
              Runs {gridDate(sheet.start_date)} – {gridDate(sheet.end_date)}{sheet.class_days ? ` · ${sheet.class_days.split(",").map((d) => d.charAt(0) + d.slice(1).toLowerCase()).join(", ")}` : ""}
              {!sheet.is_class_day && <span className="ml-2 rounded bg-amber/15 px-1.5 py-0.5 text-amber">not a usual class day</span>}
            </div>
          )}
        </div>
      </section>

      {error && <p className="mb-4 rounded-lg bg-rose/10 px-4 py-3 text-[12.8px] text-rose">{error}</p>}

      {sheet && (
        <section className="mb-5 rounded-[14px] border border-line bg-surface shadow-panel">
          <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-3.5">
            <h2 className="m-0 text-[15px] font-semibold">{sheet.batch_code} — {gridDate(day)}</h2>
            <span className="text-[12px] text-faint">{sheet.rows.length} students{unmarked ? ` · ${unmarked} not marked` : ""}</span>
            <button onClick={() => sheet.rows.forEach((r) => set(r.enrollment_id, "PRESENT"))} disabled={!sheet.rows.length}
              className="ml-auto flex items-center gap-1.5 rounded-lg bg-hover px-3 py-1.5 text-[12.5px] font-medium text-muted hover:text-text disabled:opacity-40">
              <CheckCheck size={14} /> Mark all present</button>
            <button onClick={save} disabled={busy || !sheet.rows.length}
              className="flex items-center gap-1.5 rounded-lg bg-gradient-to-br from-primary to-primary-dark px-4 py-1.5 text-[12.8px] font-medium text-on-primary disabled:opacity-50">
              {busy && <Loader2 size={14} className="animate-spin" />} Save attendance</button>
            {saved && <span className="text-[12px] text-success">Saved</span>}
          </div>
          {sheet.rows.length === 0 ? (
            <p className="m-0 px-5 py-8 text-center text-[12.8px] text-faint">No students are enrolled in this batch yet.</p>
          ) : (
            <table className="w-full border-collapse text-left text-[12.8px]">
              <thead>
                <tr className="border-b border-line bg-primary/[0.07] text-[12px] font-semibold text-primary">
                  <th className="px-5 py-2.5">Student</th><th className="px-3 py-2.5">Mark</th>
                  <th className="px-3 py-2.5">Remarks</th><th className="px-5 py-2.5 text-right">Attendance so far</th>
                </tr>
              </thead>
              <tbody>
                {sheet.rows.map((r) => {
                  const cur = marks[r.enrollment_id]?.status ?? null;
                  return (
                    <tr key={r.enrollment_id} className="border-b border-line last:border-0">
                      <td className="whitespace-nowrap px-5 py-2"><span className="text-faint">{r.student_no}</span> <b className="font-medium">{r.student_name}</b></td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          {MARKS.map(([value, text, on]) => (
                            <button key={value} onClick={() => set(r.enrollment_id, cur === value ? null : value)}
                              className={`rounded-md px-2.5 py-1 text-[11.5px] font-medium transition-colors ${cur === value ? on : "bg-hover text-muted hover:text-text"}`}>
                              {text}</button>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <input value={marks[r.enrollment_id]?.remarks ?? ""} placeholder="Optional"
                          onChange={(e) => { setSaved(false); setMarks((m) => ({ ...m, [r.enrollment_id]: { ...m[r.enrollment_id], remarks: e.target.value } })); }}
                          className="w-full rounded-md border border-line bg-bg px-2 py-1 text-[12px] outline-none focus:border-primary" />
                      </td>
                      <td className={`px-5 py-2 text-right font-semibold tabular-nums ${pctTone(r.percent)}`}>{pct(r.percent)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      )}

      {register && register.rows.length > 0 && (
        <section className="rounded-[14px] border border-line bg-surface shadow-panel">
          <div className="border-b border-line px-5 py-3.5">
            <h2 className="m-0 text-[15px] font-semibold">Attendance register — {register.batch_code}</h2>
            <p className="m-0 text-[12px] text-faint">{register.classes_marked} classes marked so far</p>
          </div>
          <table className="w-full border-collapse text-left text-[12.8px]">
            <thead>
              <tr className="border-b border-line bg-primary/[0.07] text-[12px] font-semibold text-primary">
                <th className="px-5 py-2.5">Student</th>
                {["Present", "Late", "Absent", "Leave", "Attendance"].map((h) => <th key={h} className="px-3 py-2.5 text-right">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {register.rows.map((r) => (
                <tr key={r.enrollment_id} className="border-b border-line last:border-0">
                  <td className="whitespace-nowrap px-5 py-2"><span className="text-faint">{r.student_no}</span> <b className="font-medium">{r.student_name}</b></td>
                  <td className="px-3 py-2 text-right tabular-nums text-success">{r.present}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-amber">{r.late}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-rose">{r.absent}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-sky">{r.leave}</td>
                  <td className={`px-3 py-2 text-right font-semibold tabular-nums ${pctTone(r.percent)}`}>{pct(r.percent)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </AppShell>
  );
}
