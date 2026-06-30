import { redirect } from "next/navigation";

export default function WorkerOrderDetailRedirectPage() {
  redirect("/worker/dashboard");
}
