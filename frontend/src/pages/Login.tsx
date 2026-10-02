import { useEffect, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import * as api from "../services/api";
import { Button, Card, Field, Input, Select } from "../components/ui";

type Mode = "login" | "signup" | "forgot-email" | "forgot-answer";

export default function Login() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<Mode>("login");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [securityQuestions, setSecurityQuestions] = useState<string[]>([]);
  const [securityQuestion, setSecurityQuestion] = useState("");
  const [securityAnswer, setSecurityAnswer] = useState("");

  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotQuestion, setForgotQuestion] = useState<string | null>(null);
  const [forgotAnswer, setForgotAnswer] = useState("");
  const [newPassword, setNewPassword] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (mode === "signup" && securityQuestions.length === 0) {
      api.getSecurityQuestions().then((qs) => {
        setSecurityQuestions(qs);
        setSecurityQuestion(qs[0] || "");
      });
    }
  }, [mode, securityQuestions.length]);

  function resetMessages() {
    setError(null);
    setInfo(null);
  }

  async function handleLoginOrSignup(e: React.FormEvent) {
    e.preventDefault();
    resetMessages();
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(name, email, password, securityQuestion, securityAnswer);
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleForgotEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    resetMessages();
    setSubmitting(true);
    try {
      const res = await api.forgotPassword(forgotEmail);
      if (!res.security_question) {
        setError("We couldn't find a recovery question for that email. Double-check the address, or it may not have one set up.");
      } else {
        setForgotQuestion(res.security_question);
        setMode("forgot-answer");
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResetSubmit(e: React.FormEvent) {
    e.preventDefault();
    resetMessages();
    setSubmitting(true);
    try {
      await api.resetPassword(forgotEmail, forgotAnswer, newPassword);
      setInfo("Password reset! You can now log in with your new password.");
      setMode("login");
      setEmail(forgotEmail);
      setPassword("");
    } catch (err: any) {
      setError(err.message || "That answer didn't match. Try again.");
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
          {(mode === "login" || mode === "signup") && (
            <>
              <div className="inline-flex bg-slate-100 rounded-xl p-1 mb-5 w-full">
                <button
                  type="button"
                  onClick={() => {
                    setMode("login");
                    resetMessages();
                  }}
                  className={`flex-1 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    mode === "login" ? "bg-white shadow-sm text-ink" : "text-slate-500"
                  }`}
                >
                  Log in
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMode("signup");
                    resetMessages();
                  }}
                  className={`flex-1 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    mode === "signup" ? "bg-white shadow-sm text-ink" : "text-slate-500"
                  }`}
                >
                  Sign up
                </button>
              </div>

              <form onSubmit={handleLoginOrSignup}>
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

                {mode === "signup" && (
                  <>
                    <Field label="Security question" hint="Used if you ever forget your password">
                      <Select value={securityQuestion} onChange={(e) => setSecurityQuestion(e.target.value)} required>
                        {securityQuestions.map((q) => (
                          <option key={q} value={q}>
                            {q}
                          </option>
                        ))}
                      </Select>
                    </Field>
                    <Field label="Your answer">
                      <Input value={securityAnswer} onChange={(e) => setSecurityAnswer(e.target.value)} required />
                    </Field>
                  </>
                )}

                {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
                {info && <p className="text-sm text-brand-600 mb-3">{info}</p>}

                <Button type="submit" disabled={submitting} className="w-full">
                  {submitting ? "Please wait..." : mode === "login" ? "Log in" : "Create account"}
                </Button>
              </form>

              {mode === "login" && (
                <button
                  type="button"
                  onClick={() => {
                    resetMessages();
                    setForgotEmail(email);
                    setMode("forgot-email");
                  }}
                  className="text-xs text-slate-500 hover:text-brand-600 mt-4 block mx-auto"
                >
                  Forgot your password?
                </button>
              )}
            </>
          )}

          {mode === "forgot-email" && (
            <form onSubmit={handleForgotEmailSubmit}>
              <p className="text-sm text-slate-600 mb-4">Enter your account email to retrieve your security question.</p>
              <Field label="Email">
                <Input type="email" value={forgotEmail} onChange={(e) => setForgotEmail(e.target.value)} required autoFocus />
              </Field>
              {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
              <Button type="submit" disabled={submitting} className="w-full mb-3">
                {submitting ? "Checking..." : "Continue"}
              </Button>
              <button type="button" onClick={() => setMode("login")} className="text-xs text-slate-500 hover:text-brand-600 block mx-auto">
                Back to log in
              </button>
            </form>
          )}

          {mode === "forgot-answer" && (
            <form onSubmit={handleResetSubmit}>
              <Field label={forgotQuestion || "Security question"}>
                <Input value={forgotAnswer} onChange={(e) => setForgotAnswer(e.target.value)} required autoFocus />
              </Field>
              <Field label="New password" hint="At least 8 characters">
                <Input type="password" minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
              </Field>
              {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
              <Button type="submit" disabled={submitting} className="w-full mb-3">
                {submitting ? "Resetting..." : "Reset password"}
              </Button>
              <button type="button" onClick={() => setMode("login")} className="text-xs text-slate-500 hover:text-brand-600 block mx-auto">
                Back to log in
              </button>
            </form>
          )}
        </Card>

        <p className="text-xs text-slate-400 text-center mt-4">
          Your data is private to your account — no one else can see your budgets or expenses.
        </p>
      </div>
    </div>
  );
}
