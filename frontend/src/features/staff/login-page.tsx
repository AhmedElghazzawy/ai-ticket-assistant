import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { ArrowLeft, LockKeyhole } from "lucide-react";
import { type FormEvent, useId, useState } from "react";
import { usePreferences } from "@/app/preferences";
import { logIn } from "@/client";
import { meQueryKey } from "@/client/@tanstack/react-query.gen";
import { BrandMark, LanguageSwitch, ThemeMenu } from "@/components/app-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LoginPage() {
  const { t } = usePreferences();
  const { redirect } = useSearch({ from: "/staff/login" });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const emailId = useId(); // unique ids connect each label to its input (screen readers)
  const passwordId = useId();

  const login = useMutation({
    mutationFn: async () => {
      const { data, response } = await logIn({ body: { email, password } });
      if (response?.status === 429) throw new Error(t.staff.tooManyLogins);
      if (response?.status === 401) throw new Error(t.staff.wrongLogin);
      if (!data) throw new Error(t.staff.loginError);
      return data;
    },
    onSuccess: (staff) => {
      queryClient.setQueryData(meQueryKey(), staff); // the staff pages know who is logged in
      setPassword("");
      void navigate({ to: redirect ?? "/staff" });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    login.mutate();
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="flex items-center justify-between px-4 py-4">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> {t.staff.studentView}
        </Link>
        <div className="flex items-center gap-1.5">
          <LanguageSwitch />
          <ThemeMenu />
        </div>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 pb-16">
        <form
          onSubmit={submit}
          className="w-full max-w-sm space-y-6 rounded-2xl border bg-card p-6 shadow-sm sm:p-8"
        >
          <div className="space-y-3">
            <BrandMark />
            <h1 className="flex items-center gap-2 font-heading text-xl font-bold">
              <LockKeyhole className="size-5 text-muted-foreground" /> {t.staff.loginTitle}
            </h1>
            <p className="text-sm text-muted-foreground">{t.staff.loginText}</p>
          </div>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor={emailId} className="text-sm font-medium">
                {t.staff.email}
              </label>
              <Input
                id={emailId}
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor={passwordId} className="text-sm font-medium">
                {t.staff.password}
              </label>
              <Input
                id={passwordId}
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
          </div>
          {login.isError && (
            <p role="alert" className="text-sm text-destructive">
              {login.error.message}
            </p>
          )}
          <Button type="submit" className="w-full" size="lg" disabled={login.isPending}>
            {t.staff.logIn}
          </Button>
        </form>
      </main>
    </div>
  );
}
