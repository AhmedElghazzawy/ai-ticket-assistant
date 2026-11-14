import { CircleCheck, UserRound } from "lucide-react";
import { useState } from "react";
import { usePreferences } from "@/app/preferences";
import { askForAPerson } from "@/client";
import { Button } from "@/components/ui/button";
import type { OfficeId } from "@/lib/types";

type Props = {
  ticketId: number;
  code: string; // the ticket's secret code: only this student can send it on
  office: OfficeId; // chosen by the backend from the category, never by the model
  onSent?: () => void;
};

/** "Still need help?": the automatic answer did not solve it, so a person takes over
 *  (docs/decisions/0016). The ticket keeps its AI answer; staff see that the student asked. */
export function AskSpecialist({ ticketId, code, office, onSent }: Props) {
  const { t } = usePreferences();
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function send() {
    setState("sending");
    const { error } = await askForAPerson({ path: { ticket_id: ticketId }, body: { code } });
    setState(error ? "error" : "sent");
    if (!error) onSent?.();
  }

  if (state === "sent") {
    return (
      <p role="status" className="flex items-start gap-1.5 text-sm font-medium text-success">
        <CircleCheck className="mt-0.5 size-4 shrink-0" /> {t.askSpecialistSent}
      </p>
    );
  }
  return (
    <div className="space-y-2 rounded-lg border bg-muted/40 p-3.5">
      <p className="text-sm font-semibold">{t.needHelp}</p>
      <p className="text-xs text-muted-foreground">{t.askSpecialistText(t.offices[office])}</p>
      <Button size="sm" variant="outline" disabled={state === "sending"} onClick={send}>
        <UserRound /> {t.askSpecialist}
      </Button>
      {state === "error" && (
        <p role="alert" className="text-xs text-destructive">
          {t.askSpecialistError}
        </p>
      )}
    </div>
  );
}
