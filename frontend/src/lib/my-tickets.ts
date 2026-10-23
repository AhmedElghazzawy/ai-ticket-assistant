// The student's own tickets, remembered in THIS browser only (never sent anywhere else), so they
// can come back for the status and the staff reply without copying the secret code by hand.

const KEY = "my-tickets";
const MAX_TICKETS = 20;

export interface MyTicket {
  id: number;
  code: string; // the secret code from the API: only this browser and the database's hash know it
  question: string; // a short preview, so the student recognizes the ticket
  createdAt: string; // ISO time
}

export function loadMyTickets(): MyTicket[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? (parsed as MyTicket[]) : [];
  } catch {
    return []; // private window, blocked storage or a broken value: start empty
  }
}

export function rememberTicket(id: number, code: string, question: string): void {
  const ticket = {
    id,
    code,
    question: question.slice(0, 120),
    createdAt: new Date().toISOString(),
  };
  try {
    const others = loadMyTickets().filter((existing) => existing.id !== id);
    localStorage.setItem(KEY, JSON.stringify([ticket, ...others].slice(0, MAX_TICKETS)));
  } catch {
    // storage unavailable: the page still works, the ticket just is not remembered
  }
}
