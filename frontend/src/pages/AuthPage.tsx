import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { ErrorBanner } from "../components/ui";
import { useAuth } from "../lib/auth";

export default function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { user, login, register } = useAuth();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={loc.state?.from ?? "/app"} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name);
      nav(loc.state?.from ?? "/app", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-full place-items-center px-4 py-10">
      <div className="w-full max-w-sm animate-rise">
        <Link to="/" className="mb-6 flex items-center gap-2"><img src="/favicon.svg" alt="" className="h-7 w-7" /><span className="font-display text-lg">Pollinex AI</span></Link>
        <form onSubmit={submit} className="card space-y-4 p-6" aria-label={mode === "login" ? "Sign in form" : "Registration form"}>
          <h1 className="font-display text-2xl">{mode === "login" ? "Sign in" : "Create your account"}</h1>
          <ErrorBanner error={error} />
          {mode === "register" && (
            <div><label className="label" htmlFor="name">Full name</label>
              <input id="name" className="input" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" /></div>
          )}
          <div><label className="label" htmlFor="email">Email</label>
            <input id="email" type="email" required className="input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></div>
          <div><label className="label" htmlFor="password">Password</label>
            <input id="password" type="password" required minLength={mode === "register" ? 10 : 1} className="input" value={password}
              onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} />
            {mode === "register" && <p className="mt-1 text-xs text-muted">At least 10 characters, one uppercase letter and one digit.</p>}
          </div>
          <button className="btn-primary w-full" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
          <p className="text-center text-xs text-muted">
            {mode === "login" ? <>No account? <Link className="underline" to="/register">Register</Link></> : <>Have an account? <Link className="underline" to="/login">Sign in</Link></>}
          </p>
          {mode === "register" && <p className="text-xs text-muted">The first account on a fresh installation becomes the administrator.</p>}
        </form>
      </div>
    </div>
  );
}
