import { redirect } from "next/navigation";

/** HRMS > JOSE School opens on the students. */
export default function SchoolHome() {
  redirect("/hrms/school/students");
}
