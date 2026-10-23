import { CircleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { usePreferences } from "@/app/preferences";
import { createTicket } from "@/client";
import { AppHeader } from "@/components/app-header";
import { rememberTicket } from "@/lib/my-tickets";
import type { TicketOut } from "@/lib/types";
import { AnswerCard } from "./answer-card";
import { Composer } from "./composer";
import { EmptyState } from "./empty-state";
import { Thinking } from "./thinking";

interface Turn {
  id: number;
  question: string;
  result?: TicketOut; // undefined while the pipeline is working
  error?: string; // shown instead of an answer
}

export function ChatPage() {
  const { language, t } = usePreferences();
  const [turns, setTurns] = useState<Turn[]>([]);
  const bottom = useRef<HTMLDivElement>(null);
  const busy = turns.some((turn) => !turn.result && !turn.error);

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll whenever the conversation changes
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  async function ask(question: string) {
    const id = Date.now();
    setTurns((current) => [...current, { id, question }]);
    const update = (change: Partial<Turn>) =>
      setTurns((current) =>
        current.map((turn) => (turn.id === id ? { ...turn, ...change } : turn)),
      );
    try {
      const { data, response } = await createTicket({ body: { text: question, language } });
      if (data) {
        update({ result: data });
        rememberTicket(data.ticket_id, data.access_code, question); // for "Taleplerim"
      } else update({ error: response?.status === 429 ? t.tooMany : t.error }); // 429: rate limit
    } catch {
      update({ error: t.error }); // the network itself failed
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader onNewChat={() => setTurns([])} />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4">
        {turns.length === 0 ? (
          <EmptyState onSend={ask} busy={busy} />
        ) : (
          <div className="space-y-6 py-8">
            {turns.map((turn) => (
              <div key={turn.id} className="space-y-3">
                <div className="flex justify-end">
                  <p className="max-w-[85%] rounded-2xl rounded-br-md border bg-secondary px-4 py-2.5 text-[0.95rem] whitespace-pre-wrap text-secondary-foreground">
                    {turn.question}
                  </p>
                </div>
                {turn.result && <AnswerCard result={turn.result} />}
                {turn.error && (
                  <p className="flex items-center gap-2 text-sm text-destructive">
                    <CircleAlert className="size-4" /> {turn.error}
                  </p>
                )}
                {!turn.result && !turn.error && <Thinking />}
              </div>
            ))}
            <div ref={bottom} />
          </div>
        )}
      </main>
      {turns.length > 0 && (
        // The start screen has its own input box in the middle; this one appears once a chat starts.
        <div className="sticky bottom-0 bg-linear-to-t from-background via-background to-background/0 pt-6 pb-4">
          <div className="mx-auto max-w-3xl px-4">
            <Composer onSend={ask} busy={busy} />
          </div>
        </div>
      )}
    </div>
  );
}
