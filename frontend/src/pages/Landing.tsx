import { Link } from "react-router-dom";
import { ArrowRight, Boxes, Camera, Gauge, ShieldCheck } from "lucide-react";
import { useAuth } from "../lib/auth";

const CROPS = ["Hibiscus", "Tomato", "Sunflower", "Apple", "Peach", "Pear", "Strawberry", "Brinjal", "Chilli"];

export default function Landing() {
  const { user } = useAuth();
  return (
    <div className="min-h-full bg-paper">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <div className="flex items-center gap-2.5">
          <img src="/favicon.svg" alt="" className="h-8 w-8" />
          <span className="font-display text-xl">Pollinex AI</span>
        </div>
        <nav className="flex items-center gap-2">
          {user ? <Link to="/app" className="btn-primary">Open dashboard <ArrowRight size={16} /></Link> : (
            <>
              <Link to="/login" className="btn-ghost">Sign in</Link>
              <Link to="/register" className="btn-primary">Create account</Link>
            </>
          )}
        </nav>
      </header>

      <section className="mx-auto grid max-w-6xl gap-10 px-5 pb-16 pt-8 md:grid-cols-[1.2fr_1fr] md:pt-16">
        <div className="animate-rise">
          <div className="kicker mb-4">Research platform · software only · runs on a laptop</div>
          <h1 className="font-display text-4xl leading-[1.05] md:text-6xl">
            Read the flower.<br /><span className="text-leaf">Respect the biology.</span>
          </h1>
          <p className="mt-5 max-w-xl text-base text-muted">
            Pollinex detects flowers in phone and orchard photos, recognises species with an open-set gallery, estimates
            visible developmental stage, and turns species-specific pollination knowledge into explainable, uncertainty-aware
            recommendations — with a virtual simulator for pollen transfer.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link to={user ? "/app/scanner" : "/register"} className="btn-accent"><Camera size={16} />Start scanning</Link>
            <a href="#honesty" className="btn-ghost">How we label evidence</a>
          </div>
          <div className="mt-8 flex flex-wrap gap-1.5">
            {CROPS.map((c) => <span key={c} className="rounded-full border border-line px-3 py-1 text-xs">{c}</span>)}
          </div>
        </div>
        <FlowerDiagram />
      </section>

      <section className="border-y border-line bg-surface">
        <div className="mx-auto grid max-w-6xl gap-px bg-line md:grid-cols-3">
          {[
            { icon: <Camera />, t: "Live scanner", d: "Upload or use your phone camera. Frames are sampled at a rate your laptop can actually sustain — no fake real-time." },
            { icon: <Gauge />, t: "Species-specific readiness", d: "Vibration for tomato and brinjal, compatible cross-pollen for apple and pear. Never one universal method." },
            { icon: <Boxes />, t: "Virtual pollination", d: "Three.js particle simulation of pollen transfer, alignment and capture — clearly labelled as computation, not fertilisation." },
          ].map((f) => (
            <div key={f.t} className="bg-surface p-7">
              <div className="mb-3 text-pollen">{f.icon}</div>
              <div className="font-display text-xl">{f.t}</div>
              <p className="mt-2 text-sm text-muted">{f.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="honesty" className="mx-auto max-w-6xl px-5 py-16">
        <div className="grid gap-8 md:grid-cols-[1fr_1.4fr]">
          <div>
            <ShieldCheck className="mb-3 text-leaf" />
            <h2 className="font-display text-3xl">Every output says where it came from.</h2>
          </div>
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            {[
              ["Trained model", "YOLO11 flower detector trained and evaluated on held-out CC-BY-4.0 data (apple, peach, pear, sunflower)."],
              ["Reference gallery", "Open-set species matching; answers ‘unknown’ instead of forcing a label."],
              ["Heuristic", "Stage, centre-region and visible-health cues. Interpretable, not trained on labels that do not yet exist."],
              ["Rule engine / simulation", "Readiness rules from cited literature; simulated transfer is never reported as fruit set."],
            ].map(([t, d]) => (
              <div key={t} className="card p-4"><dt className="font-semibold">{t}</dt><dd className="mt-1 text-muted">{d}</dd></div>
            ))}
          </dl>
        </div>
      </section>
      <footer className="border-t border-line py-6 text-center text-xs text-muted">
        Pollinex AI · training data: Dias, Tabb & Medeiros (2018), USDA Ag Data Commons, CC BY 4.0
      </footer>
    </div>
  );
}

function FlowerDiagram() {
  const petals = Array.from({ length: 5 }, (_, i) => (i * 72 * Math.PI) / 180);
  return (
    <svg viewBox="0 0 400 400" className="mx-auto w-full max-w-md" role="img" aria-label="Annotated flower diagram">
      <circle cx="200" cy="200" r="190" fill="rgb(var(--raised))" />
      {petals.map((a, i) => (
        <ellipse key={i} cx={200 + 78 * Math.cos(a - Math.PI / 2)} cy={200 + 78 * Math.sin(a - Math.PI / 2)} rx="62" ry="40"
          transform={`rotate(${(a * 180) / Math.PI} ${200 + 78 * Math.cos(a - Math.PI / 2)} ${200 + 78 * Math.sin(a - Math.PI / 2)})`}
          fill="rgb(var(--surface))" stroke="rgb(var(--line))" />
      ))}
      {Array.from({ length: 14 }, (_, i) => {
        const a = (i / 14) * Math.PI * 2;
        return <circle key={i} cx={200 + 26 * Math.cos(a)} cy={200 + 26 * Math.sin(a)} r="5" fill="rgb(var(--pollen))" />;
      })}
      <circle cx="200" cy="200" r="9" fill="rgb(var(--leaf))" />
      <rect x="92" y="92" width="216" height="216" fill="none" stroke="rgb(var(--leaf))" strokeWidth="2" strokeDasharray="6 4" />
      <g fontFamily="IBM Plex Mono, monospace" fontSize="11" fill="rgb(var(--ink))">
        <text x="96" y="86">flower · 0.91 · trained model</text>
        <line x1="200" y1="200" x2="320" y2="330" stroke="rgb(var(--muted))" />
        <text x="250" y="348">centre region · heuristic</text>
        <line x1="226" y1="200" x2="330" y2="150" stroke="rgb(var(--muted))" />
        <text x="270" y="140">pollen-like cluster</text>
      </g>
    </svg>
  );
}
