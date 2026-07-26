import type { LogbookAssignment, LogbookResponse } from "@/types/logbook";

export function activeEvidenceCount(response?: LogbookResponse): number {
  return response?.evidences.filter((evidence) => !evidence.deleted_at).length || 0;
}

export function participantAssignment<T extends LogbookAssignment>(
  assignments: T[],
  userId?: string,
): T | undefined {
  if (!userId) return undefined;
  return assignments.find((assignment) => assignment.user_id === userId);
}

export class SingleFlight {
  private running = false;

  async run<T>(operation: () => Promise<T>): Promise<{ started: boolean; value?: T }> {
    if (this.running) return { started: false };
    this.running = true;
    try {
      return { started: true, value: await operation() };
    } finally {
      this.running = false;
    }
  }
}
