import { ArrowUp } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useState } from "react";
import { usePreferences } from "@/app/preferences";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const MAX_LENGTH = 2000; // same limit as the API (TicketIn.text)

export function Composer({ onSend, busy }: { onSend: (text: string) => void; busy: boolean }) {
  const { t } = usePreferences();
  const [text, setText] = useState("");
  const ready = text.trim().length > 0 && !busy;

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!ready) return;
    onSend(text.trim());
    setText("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter adds a new line (and never send while typing Turkish characters
    // through an input method: isComposing)
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) submit(event);
  }

  return (
    <form onSubmit={submit} className="space-y-2">
      <div className="relative rounded-2xl border bg-card shadow-sm transition-shadow focus-within:border-ring/50 focus-within:ring-3 focus-within:ring-ring/15">
        <Textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t.placeholder}
          maxLength={MAX_LENGTH}
          rows={1}
          aria-label={t.placeholder}
          className="max-h-48 min-h-14 resize-none border-0 bg-transparent py-4 pr-14 pl-4 text-[0.95rem] shadow-none focus-visible:ring-0 dark:bg-transparent"
        />
        <Button
          type="submit"
          size="icon"
          disabled={!ready}
          aria-label={t.send}
          className="absolute right-2.5 bottom-2.5 rounded-xl"
        >
          <ArrowUp />
        </Button>
      </div>
      <p className="flex justify-between gap-4 px-1 text-xs text-muted-foreground">
        <span>{t.disclaimer}</span>
        {text.length > MAX_LENGTH * 0.8 && (
          <span className="tabular-nums">
            {text.length}/{MAX_LENGTH}
          </span>
        )}
      </p>
    </form>
  );
}
