import { useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { ErrorBoundary } from "./ErrorBoundary";
import {
  Activity, BarChart3, BookOpen, Boxes, Camera, CloudSun, Database, FileDown, Flower2, Gauge, HeartPulse, History,
  LayoutDashboard, LogOut, Map as MapIcon, Menu, Microscope, Moon, ScanSearch, Settings, LifeBuoy, UserCog, Sprout, Sun, Timer, X,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import type { Role } from "../lib/types";

interface Item { to: string; label: string; icon: ReactNode; roles?: Role[] }
const NAV: { group: string; items: Item[] }[] = [
  { group: "Field", items: [
    { to: "/app", label: "Dashboard", icon: <LayoutDashboard size={16} /> },
    { to: "/app/scanner", label: "Flower scanner", icon: <Camera size={16} /> },
    { to: "/app/history", label: "Pollination history", icon: <History size={16} /> },
    { to: "/app/fields", label: "Field management", icon: <MapIcon size={16} /> },
    { to: "/app/inventory", label: "Flower inventory", icon: <Sprout size={16} /> },
    { to: "/app/environment", label: "Environment", icon: <CloudSun size={16} /> },
  ]},
  { group: "Analysis", items: [
    { to: "/app/species", label: "Species recognition", icon: <Flower2 size={16} /> },
    { to: "/app/structure", label: "Flower structure", icon: <Microscope size={16} /> },
    { to: "/app/maturity", label: "Maturity stages", icon: <Timer size={16} /> },
    { to: "/app/readiness", label: "Pollination readiness", icon: <Gauge size={16} /> },
    { to: "/app/health", label: "Plant health", icon: <HeartPulse size={16} /> },
    { to: "/app/simulator", label: "Virtual simulator", icon: <Boxes size={16} /> },
  ]},
  { group: "Research", items: [
    { to: "/app/analytics", label: "Analytics", icon: <BarChart3 size={16} /> },
    { to: "/app/evaluation", label: "Model evaluation", icon: <Activity size={16} /> },
    { to: "/app/research", label: "Research centre", icon: <BookOpen size={16} /> },
    { to: "/app/datasets", label: "Datasets", icon: <Database size={16} /> },
    { to: "/app/reports", label: "Reports", icon: <FileDown size={16} /> },
    { to: "/app/admin", label: "Admin settings", icon: <Settings size={16} />, roles: ["admin"] },
    { to: "/app/settings", label: "User settings", icon: <UserCog size={16} /> },
    { to: "/app/help", label: "Help & documentation", icon: <LifeBuoy size={16} /> },
  ]},
];

export function Layout() {
  const { user, logout, hasRole } = useAuth();
  const { theme, toggle } = useTheme();
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  const nav = (
    <nav className="flex flex-col gap-5 px-3 py-4" aria-label="Main">
      {NAV.map((g) => (
        <div key={g.group}>
          <div className="kicker px-2 pb-1">{g.group}</div>
          <ul className="flex flex-col gap-0.5">
            {g.items.filter((i) => !i.roles || hasRole(...i.roles)).map((i) => (
              <li key={i.to}>
                <NavLink to={i.to} end={i.to === "/app"} onClick={() => setOpen(false)}
                  className={({ isActive }) => `flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm transition-colors ${isActive ? "bg-ink text-paper" : "text-ink/80 hover:bg-raised"}`}>
                  {i.icon}{i.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-full">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 overflow-y-auto border-r border-line bg-surface lg:block">
        <Brand />
        {nav}
      </aside>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 overflow-y-auto bg-surface shadow-xl">
            <div className="flex items-center justify-between pr-3"><Brand /><button aria-label="Close menu" onClick={() => setOpen(false)}><X size={18} /></button></div>
            {nav}
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-paper/85 px-4 backdrop-blur">
          <button className="lg:hidden" aria-label="Open menu" onClick={() => setOpen(true)}><Menu size={20} /></button>
          <div className="kicker hidden sm:block">{loc.pathname.replace("/app", "") || "/dashboard"}</div>
          <div className="ml-auto flex items-center gap-2">
            <NavLink to="/app/scanner" className="btn-accent !py-1.5 lg:hidden"><ScanSearch size={16} />Scan</NavLink>
            <button className="btn-ghost !px-2 !py-1.5" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <div className="hidden text-right text-xs sm:block">
              <div className="font-medium">{user?.full_name || user?.email}</div>
              <div className="font-mono uppercase text-muted">{user?.role}</div>
            </div>
            <button className="btn-ghost !px-2 !py-1.5" onClick={logout} aria-label="Log out"><LogOut size={16} /></button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 md:px-8"><ErrorBoundary resetKey={loc.pathname}><Outlet /></ErrorBoundary></main>
      </div>
    </div>
  );
}

function Brand() {
  return (
    <NavLink to="/" className="flex items-center gap-2.5 px-5 py-4">
      <img src="/favicon.svg" alt="" className="h-7 w-7" />
      <div>
        <div className="font-display text-lg leading-none">Pollinex</div>
        <div className="kicker !text-[9px]">flower intelligence</div>
      </div>
    </NavLink>
  );
}
