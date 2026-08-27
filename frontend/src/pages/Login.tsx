import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { Button, Card, Field, Input } from "../components/ui";

export default function Login() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(name, email, password);
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="w-9 h-9 rounded-lg bg-brand-600 text-white flex items-center justify-center font-display font-bold">
            ₹
          </div>
          <span className="font-display font-bold text-xl text-ink">Finch</span>
        </div>

        <Card>
          <div className="inline-flex bg-slate-100 rounded-xl p-1 mb-5 w-full">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={`flex-1 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                mode === "login" ? "bg-white shadow-sm text-ink" : "text-slate-500"
              }`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => setMode("signup")}
              className={`flex-1 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                mode === "signup" ? "bg-white shadow-sm text-ink" : "text-slate-500"
              }`}
            >
              Sign up
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {mode === "signup" && (
              <Field label="Name">
                <Input value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
              </Field>
            )}
            <Field label="Email">
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </Field>
            <Field label="Password" hint={mode === "signup" ? "At least 8 characters" : undefined}>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={mode === "signup" ? 8 : undefined}
                required
              />
            </Field>

            {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}

            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Please wait..." : mode === "login" ? "Log in" : "Create account"}
            </Button>
          </form>
        </Card>

        <p className="text-xs text-slate-400 text-center mt-4">
          Your data is private to your account — no one else can see your budgets or expenses.
        </p>
      </div>
    </div>
  );
}
