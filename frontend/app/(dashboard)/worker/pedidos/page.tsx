import { redirect } from "next/navigation";

export default function WorkerOrdersRedirectPage() {
  redirect("/worker/dashboard");
}
