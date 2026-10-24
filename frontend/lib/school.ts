/** JOSE — Jezseem School of Excellence, run by HR (owner, 24-Oct-2026). */

export interface Course {
  id: string; code: string; name: string; description: string | null;
  duration_value: number; duration_unit: string; fee: number; is_active: boolean; batches: number;
}

export interface Batch {
  id: string; batch_code: string; course_id: string; course_name: string | null; course_code: string | null;
  start_date: string; end_date: string; class_days: string | null; start_time: string | null; end_time: string | null;
  trainer_employee_id: string | null; trainer: string | null; trainer_name: string | null;
  venue: string | null; capacity: number | null; fee: number; status: string; notes: string | null; enrolled: number;
}

export interface Student {
  id: string; student_no: string; full_name: string; father_name: string | null; gender: string | null;
  date_of_birth: string | null; cnic: string | null; phone: string | null; email: string | null;
  address: string | null; city: string | null; education: string | null; organization: string | null;
  notes: string | null; is_active: boolean; courses: number; balance: number;
}

export interface Payment {
  id: string; receipt_no: string; enrollment_id?: string; student_name?: string | null; student_no?: string | null;
  batch_code?: string | null; course_name?: string | null; payment_date: string; amount: number; method: string;
  reference: string | null; notes?: string | null; status: string; cancel_reason: string | null; balance_after?: number;
}

export interface Enrollment {
  id: string; student_id: string; batch_id: string; student_no: string | null; student_name: string | null;
  batch_code: string | null; course_name: string | null; batch_start: string | null; batch_end: string | null;
  enroll_date: string; fee: number; discount: number; net_fee: number; paid: number; balance: number;
  status: string; completion_date: string | null; result: string | null; certificate_no: string | null;
  notes: string | null; payments: Payment[];
  attendance_percent: number | null; classes_marked: number;
}

export interface SchoolLookups {
  courses: { id: string; code: string; name: string; fee: number; is_active: boolean; duration: string }[];
  batches: { id: string; batch_code: string; course: string | null; fee: number; status: string; start_date: string; end_date: string }[];
  trainers: { id: string; label: string }[];
}

export const WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

export const SCHOOL_TONE: Record<string, string> = {
  PLANNED: "bg-sky/15 text-sky",
  RUNNING: "bg-success/15 text-success",
  COMPLETED: "bg-violet/15 text-violet",
  CANCELLED: "bg-hover text-faint",
  ENROLLED: "bg-success/15 text-success",
  DROPPED: "bg-rose/10 text-rose",
  RECEIVED: "bg-success/15 text-success",
};

/** 45000 -> "45,000". */
export const pkr = (n: number | null | undefined) =>
  (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 2 });
