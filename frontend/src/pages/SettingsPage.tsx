import { useState, type FormEvent } from "react";
import { Card, ErrorBanner, PageHeader, Pill } from "../components/ui";
import { useAuth } from "../lib/auth";
import { when } from "../lib/hooks";
import { useTheme } from "../lib/theme";
import { toast } from "../lib/toast";

export default function SettingsPage() {
  const { user, updateProfile, changePassword } = useAuth();
  const { theme, toggle } = useTheme();
  const [name, setName] = useState(user?.full_name ?? "");
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault(); setErr(null); setBusy(true);
    try { await updateProfile(name); toast.success("Profile saved"); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  const savePassword = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    if (pw.next !== pw.confirm) { setErr("The new passwords do not match."); return; }
    setBusy(true);
    try {
      await changePassword(pw.current, pw.next);
      setPw({ current: "", next: "", confirm: "" });
      toast.success("Password changed. Other sessions were signed out.");
    } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader kicker="Account" title="User settings">Your profile, password and display preferences.</PageHeader>
      <ErrorBanner error={err} />
      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <Card title="Profile">
          <dl className="mb-4 grid grid-cols-[110px_1fr] gap-y-1.5 text-sm">
            <dt className="text-muted">Email</dt><dd>{user?.email}</dd>
            <dt className="text-muted">Role</dt><dd><Pill tone="info">{user?.role}</Pill></dd>
            <dt className="text-muted">Member since</dt><dd>{user ? when(user.created_at) : ""}</dd>
          </dl>
          <form onSubmit={saveProfile} className="space-y-2">
            <label htmlFor="full-name" className="text-xs text-muted">Display name</label>
            <input id="full-name" className="input" maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
            <button className="btn-primary" disabled={busy}>Save profile</button>
          </form>
        </Card>
        <Card title="Change password" subtitle="At least 10 characters with an uppercase letter and a digit. Other sessions are signed out.">
          <form onSubmit={savePassword} className="space-y-2">
            <label htmlFor="pw-current" className="text-xs text-muted">Current password</label>
            <input id="pw-current" type="password" autoComplete="current-password" className="input" required value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />
            <label htmlFor="pw-new" className="text-xs text-muted">New password</label>
            <input id="pw-new" type="password" autoComplete="new-password" className="input" required minLength={10} value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />
            <label htmlFor="pw-confirm" className="text-xs text-muted">Confirm new password</label>
            <input id="pw-confirm" type="password" autoComplete="new-password" className="input" required minLength={10} value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
            <button className="btn-primary" disabled={busy}>Change password</button>
          </form>
        </Card>
        <Card title="Display">
          <div className="flex items-center justify-between text-sm">
            <span>Theme: <strong>{theme}</strong></span>
            <button className="btn-ghost" onClick={toggle}>Switch to {theme === "dark" ? "light" : "dark"}</button>
          </div>
          <p className="mt-2 text-xs text-muted">Saved in this browser only.</p>
        </Card>
      </div>
    </div>
  );
}
