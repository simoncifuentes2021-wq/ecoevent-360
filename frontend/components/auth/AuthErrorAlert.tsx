import { AlertCircle } from "lucide-react";

export function AuthErrorAlert({ message }: { message: string }) {
  return (
    <div className="flex gap-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
