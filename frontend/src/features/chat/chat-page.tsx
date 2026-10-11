import { CircleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { usePreferences } from "@/app/preferences";
import { AppHeader } from "@/components/app-header";
import type { TicketOut } from "@/lib/types";
import { mockAsk } from "@/mocks/ask";
import { AnswerCard } from "./answer-card";
import { Composer } from "./composer";
import { EmptyState } from "./empty-state";
import { Thinking } from "./thinking";

interface Turn {
  id: number;
  question: string;
  result?: TicketOut; // undefined while the pipeline is working
  failed?: boolean;
}

export function ChatPage() {
  const { language, t } = usePreferences();
  const [turns, setTurns] = useState<Turn[]>([]);
  const bottom = useRef<HTMLDivElement>(null);
  const busy = turns.some((turn) => !turn.result && !turn.failed);

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll whenever the conversation changes
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  async function ask(question: string) {
    const id = Date.now();
    setTurns((current) => [...current, { id, question }]);
    try {
      const result = await mockAsk(question, language);
      setTurns((current) => current.map((turn) => (turn.id === id ? { ...turn, result } : turn)));
    } catch {
      setTurns((current) =>
        current.map((turn) => (turn.id === id ? { ...turn, failed: true } : turn)),
      );
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader onNewChat={() => setTurns([])} />
      <main className="mx-auto w-full max-w-3xl flex-1 px-4">
        {turns.length === 0 ? (
          <EmptyState onPick={ask} />
        ) : (
          <div className="space-y-6 py-8">
            {turns.map((turn) => (
              <div key={turn.id} className="space-y-3">
                <div className="flex justify-end">
                  <p className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-[0.95rem] whitespace-pre-wrap text-primary-foreground">
                    {turn.question}
                  </p>
                </div>
                {turn.result && <AnswerCard result={turn.result} />}
                {turn.failed && (
                  <p className="flex items-center gap-2 text-sm text-destructive">
                    <CircleAlert className="size-4" /> {t.error}
                  </p>
                )}
                {!turn.result && !turn.failed && <Thinking />}
              </div>
            ))}
            <div ref={bottom} />
          </div>
        )}
      </main>
      <div className="sticky bottom-0 bg-linear-to-t from-background via-background to-background/0 pt-6 pb-4">
        <div className="mx-auto max-w-3xl px-4">
          <Composer onSend={ask} busy={busy} />
        </div>
      </div>
    </div>
  );
}
