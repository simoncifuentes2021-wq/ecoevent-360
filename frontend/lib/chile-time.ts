export const CHILE_TIME_ZONE = "America/Santiago";
export const CHILE_LOCALE = "es-CL";

export function chileToday(date: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: CHILE_TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
}

export function formatChileDate(value: string | Date, options: Intl.DateTimeFormatOptions = {}): string {
  const date = typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T12:00:00-04:00`) : new Date(value);
  return new Intl.DateTimeFormat(CHILE_LOCALE, { timeZone: CHILE_TIME_ZONE, dateStyle: "medium", ...options }).format(date);
}

export function formatChileDateTime(value: string | Date, options: Intl.DateTimeFormatOptions = {}): string {
  return new Intl.DateTimeFormat(CHILE_LOCALE, { timeZone: CHILE_TIME_ZONE, dateStyle: "short", timeStyle: "short", ...options }).format(new Date(value));
}

/** Converts a datetime-local value entered as Chilean wall time into an ISO UTC instant. */
export function chileLocalToIso(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) throw new Error("Fecha y hora inválidas");
  const [day, clock] = value.split("T");
  const [year, month, date] = day.split("-").map(Number);
  const [hour, minute, second = 0] = clock.split(":").map(Number);
  const desiredUtc = Date.UTC(year, month - 1, date, hour, minute, second);
  let candidate = new Date(desiredUtc + 4 * 60 * 60 * 1000);
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const parts = new Intl.DateTimeFormat("en-CA", { timeZone: CHILE_TIME_ZONE, year:"numeric", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit", second:"2-digit", hourCycle:"h23" }).formatToParts(candidate);
    const shown = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    const shownUtc = Date.UTC(Number(shown.year), Number(shown.month)-1, Number(shown.day), Number(shown.hour), Number(shown.minute), Number(shown.second));
    const delta = desiredUtc - shownUtc;
    if (!delta) return candidate.toISOString();
    candidate = new Date(candidate.getTime() + delta);
  }
  throw new Error("La hora indicada no existe en Chile por el cambio de horario");
}

export function isoToChileLocalInput(value: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: CHILE_TIME_ZONE, year:"numeric", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit", hourCycle:"h23" }).formatToParts(new Date(value));
  const shown = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${shown.year}-${shown.month}-${shown.day}T${shown.hour}:${shown.minute}`;
}
