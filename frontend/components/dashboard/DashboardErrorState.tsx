import { ErrorState } from "@/components/common/ErrorState";

export function DashboardErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return <ErrorState title="No se pudo cargar el dashboard" message={message || "El dashboard avanzado aun no esta disponible en el backend."} onRetry={onRetry} />;
}
