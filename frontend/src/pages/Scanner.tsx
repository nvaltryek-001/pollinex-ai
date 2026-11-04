import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Camera, CameraOff, Pause, Play, RefreshCw, ScanLine, SwitchCamera, Upload } from "lucide-react";
import { DetectionOverlay } from "../components/DetectionOverlay";
import { ScanResults } from "../components/ScanResults";
import { Card, ErrorBanner, Loading, MethodBadge, Notice, PageHeader } from "../components/ui";
import { api, tokenStore, wsUrl } from "../lib/api";
import { blobToBase64, captureFrame, CameraError, listCameras, openCamera, stopStream } from "../lib/camera";
import { useApi } from "../lib/hooks";
import { toast } from "../lib/toast";
import type { EnvRecord, LiveResult, Page, Plant, Scan, SpeciesKB } from "../lib/types";

type Tab = "upload" | "camera";
const ACCEPT = "image/jpeg,image/png,image/webp,image/bmp";
const MAX_MB = 15;

export default function Scanner() {
  const [tab, setTab] = useState<Tab>("upload");
  const [mode, setMode] = useState("auto");
  const [speciesHint, setSpeciesHint] = useState("");
  const [envId, setEnvId] = useState("");
  const [plantId, setPlantId] = useState("");
  const [result, setResult] = useState<Scan | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const kb = useApi<{ species: SpeciesKB[] }>("/ai/species");
  const envs = useApi<Page<EnvRecord>>("/environment?page_size=20");
  const plants = useApi<Page<Plant>>("/plants?page_size=100");

  const analyse = useCallback(async (blob: Blob, name: string, source: "upload" | "camera") => {
    setError(null);
    if (blob.size > MAX_MB * 1024 * 1024) { setError(`File is larger than ${MAX_MB} MB.`); return; }
    setBusy(true);
    setResult(null);
    const fd = new FormData();
    fd.append("file", blob, name);
    fd.append("mode", mode);
    fd.append("source", source);
    if (speciesHint) fd.append("species_hint", speciesHint);
    if (envId) fd.append("environment_id", envId);
    if (plantId) fd.append("plant_id", plantId);
    try {
      const s = await api.upload<Scan>("/scans", fd);
      setResult(s);
      toast.success(`Scan #${s.id} saved · ${s.flower_count} flower${s.flower_count === 1 ? "" : "s"} found`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [mode, speciesHint, envId, plantId]);

  const onFile = (f: File | undefined) => {
    if (!f) return;
    if (!ACCEPT.split(",").includes(f.type)) { setError(`Unsupported file type "${f.type || "unknown"}". Use JPEG, PNG, WEBP or BMP.`); return; }
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(f));
    void analyse(f, f.name, "upload");
  };

  return (
    <div>
      <PageHeader kicker="Module 1-7 · live pipeline" title="Flower scanner">
        Upload a photo or use your camera. Every result is computed by the backend models and saved to your history.
      </PageHeader>

      <div className="mb-4 grid gap-3 md:grid-cols-[auto_1fr]">
        <div role="tablist" className="inline-flex rounded-lg border border-line bg-surface p-1">
          {(["upload", "camera"] as Tab[]).map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
              className={`flex items-center gap-2 rounded-md px-4 py-1.5 text-sm ${tab === t ? "bg-ink text-paper" : "text-muted"}`}>
              {t === "upload" ? <Upload size={15} /> : <Camera size={15} />}{t === "upload" ? "Upload" : "Camera"}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <select aria-label="Analysis mode" className="input" value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="auto">Mode: auto (field image, falls back to close-up)</option>
            <option value="scene">Mode: field image (many flowers)</option>
            <option value="closeup">Mode: close-up (one flower - recommended for species)</option>
          </select>
          <select aria-label="Species hint" className="input" value={speciesHint} onChange={(e) => setSpeciesHint(e.target.value)}>
            <option value="">Species: let the model decide</option>
            {kb.data?.species.map((s) => <option key={s.id} value={s.id}>I know it is: {s.common_name}</option>)}
          </select>
          <select aria-label="Environment record" className="input" value={envId} onChange={(e) => setEnvId(e.target.value)}>
            <option value="">No environment record</option>
            {envs.data?.items.map((e) => <option key={e.id} value={e.id}>{new Date(e.observed_at).toLocaleString()} · {e.temperature_c ?? "?"}°C · {e.source}</option>)}
          </select>
          <select aria-label="Plant" className="input" value={plantId} onChange={(e) => setPlantId(e.target.value)}>
            <option value="">No plant link</option>
            {plants.data?.items.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </div>
      </div>

      {tab === "upload" ? (
        <Card>
          <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-line px-6 py-10 text-center hover:bg-raised/50"
            onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); onFile(e.dataTransfer.files[0]); }}>
            <Upload className="text-muted" />
            <span className="font-display text-xl">Drop a flower photo, or tap to choose</span>
            <span className="text-xs text-muted">JPEG · PNG · WEBP · BMP, up to {MAX_MB} MB. On phones this can open the camera directly.</span>
            <input data-testid="file-input" type="file" accept={ACCEPT} capture="environment" className="sr-only" onChange={(e) => onFile(e.target.files?.[0])} />
          </label>
        </Card>
      ) : (
        <LiveCamera onCapture={(b) => { if (preview) URL.revokeObjectURL(preview); setPreview(URL.createObjectURL(b)); void analyse(b, "capture.jpg", "camera"); }} speciesHint={speciesHint} />
      )}

      <div className="mt-5 space-y-4">
        <ErrorBanner error={error} />
        {busy && <Card><Loading text="Running detection, species, stage, structure, health and readiness analysis" /></Card>}
        {result && (
          <>
            <div className="flex items-center justify-between">
              <h2 className="font-display text-2xl">Results</h2>
              <Link className="btn-ghost" to={`/app/scans/${result.id}`}>Open scan page</Link>
            </div>
            <ScanResults scan={result} localPreview={preview} />
          </>
        )}
      </div>
    </div>
  );
}

function LiveCamera({ onCapture, speciesHint }: { onCapture: (b: Blob) => void; speciesHint: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const inFlight = useRef(false);
  const timer = useRef<number | null>(null);
  const [cams, setCams] = useState<MediaDeviceInfo[]>([]);
  const [camIdx, setCamIdx] = useState(0);
  const [facing, setFacing] = useState<"environment" | "user">("environment");
  const [on, setOn] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [interval, setIntervalMs] = useState(1500);
  const [live, setLive] = useState<LiveResult | null>(null);
  const [stats, setStats] = useState({ frames: 0, dropped: 0, transport: "—" });
  const [err, setErr] = useState<string | null>(null);
  const [dims, setDims] = useState<[number, number]>([1280, 720]);

  const stopScan = useCallback(() => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = null;
    wsRef.current?.close();
    wsRef.current = null;
    inFlight.current = false;
    setScanning(false);
  }, []);

  const stopCam = useCallback(() => {
    stopScan();
    stopStream(streamRef.current);
    streamRef.current = null;
    setOn(false);
    setLive(null);
  }, [stopScan]);

  useEffect(() => () => stopCam(), [stopCam]);

  const start = async (deviceId?: string) => {
    setErr(null);
    stopStream(streamRef.current);
    try {
      const s = await openCamera({ deviceId, facing });
      streamRef.current = s;
      const v = videoRef.current!;
      v.srcObject = s;
      await v.play();
      setDims([v.videoWidth || 1280, v.videoHeight || 720]);
      setOn(true);
      setCams(await listCameras()); // labels only available after permission
    } catch (e) {
      setErr(e instanceof CameraError ? e.message : (e as Error).message);
      setOn(false);
    }
  };

  const switchCam = async () => {
    if (cams.length > 1) {
      const next = (camIdx + 1) % cams.length;
      setCamIdx(next);
      await start(cams[next].deviceId);
    } else {
      setFacing((f) => (f === "environment" ? "user" : "environment"));
      await start();
    }
  };

  const sendFrame = useCallback(async () => {
    const v = videoRef.current;
    if (!v || inFlight.current) { setStats((s) => ({ ...s, dropped: s.dropped + 1 })); return; }
    inFlight.current = true;
    try {
      const blob = await captureFrame(v, 960, 0.8);
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ frame_id: Date.now(), image: await blobToBase64(blob) }));
        return; // inFlight cleared on message
      }
      const fd = new FormData();
      fd.append("file", blob, "frame.jpg");
      if (speciesHint) fd.append("species_hint", speciesHint);
      const r = await api.upload<LiveResult>("/scans/live/frame", fd);
      setLive(r);
      setStats((s) => ({ ...s, frames: s.frames + 1, transport: "HTTP" }));
      inFlight.current = false;
    } catch (e) {
      inFlight.current = false;
      setErr((e as Error).message);
    }
  }, [speciesHint]);

  const startScan = () => {
    setErr(null);
    setStats({ frames: 0, dropped: 0, transport: "connecting" });
    try {
      const ws = new WebSocket(wsUrl("/scans/live/ws"));
      ws.onopen = () => ws.send(JSON.stringify({ token: tokenStore.get() }));
      ws.onmessage = (ev) => {
        const m = JSON.parse(ev.data);
        if (m.type === "ready") setStats((s) => ({ ...s, transport: "WebSocket" }));
        else if (m.type === "result") { setLive(m); inFlight.current = false; setStats((s) => ({ ...s, frames: s.frames + 1 })); }
        else if (m.type === "error") { inFlight.current = false; setErr(m.detail); }
      };
      ws.onerror = () => { wsRef.current = null; setStats((s) => ({ ...s, transport: "HTTP" })); };
      ws.onclose = () => { if (wsRef.current === ws) wsRef.current = null; inFlight.current = false; };
      wsRef.current = ws;
    } catch {
      wsRef.current = null;
    }
    timer.current = window.setInterval(() => void sendFrame(), interval);
    setScanning(true);
  };

  useEffect(() => {
    if (!scanning) return;
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(() => void sendFrame(), interval);
  }, [interval, scanning, sendFrame]);

  return (
    <Card>
      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <div>
          <div className="relative overflow-hidden rounded-xl bg-black" style={{ aspectRatio: `${dims[0]} / ${dims[1]}` }}>
            <video ref={videoRef} playsInline muted className="absolute inset-0 h-full w-full object-fill" aria-label="Camera preview" />
            {!on && <div className="absolute inset-0 grid place-items-center text-sm text-white/70">Camera is off</div>}
            {on && live && (
              <DetectionOverlay width={live.image_size[0]} height={live.image_size[1]}
                boxes={live.detections.map((d) => ({ box: d.box, score: d.score, low_confidence: d.low_confidence, label: d.species !== "unknown" ? d.species : undefined }))} />
            )}
            {scanning && <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1 text-xs text-white"><span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />sampling every {(interval / 1000).toFixed(1)} s</div>}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {!on ? <button className="btn-primary" onClick={() => start()}><Camera size={16} />Start camera</button>
              : <button className="btn-ghost" onClick={stopCam}><CameraOff size={16} />Stop camera</button>}
            <button className="btn-ghost" onClick={switchCam} disabled={!on}><SwitchCamera size={16} />Switch</button>
            {!scanning ? <button className="btn-ghost" disabled={!on} onClick={startScan}><Play size={16} />Start live scan</button>
              : <button className="btn-ghost" onClick={stopScan}><Pause size={16} />Stop live scan</button>}
            <button className="btn-accent" disabled={!on} onClick={async () => { if (videoRef.current) onCapture(await captureFrame(videoRef.current, 2048, 0.92)); }}>
              <ScanLine size={16} />Capture & analyse
            </button>
          </div>
        </div>
        <div className="space-y-3">
          <ErrorBanner error={err} onRetry={on ? undefined : () => start()} />
          <div>
            <label className="label" htmlFor="interval">Frame sampling interval: {(interval / 1000).toFixed(1)} s</label>
            <input id="interval" type="range" min={500} max={5000} step={250} value={interval} onChange={(e) => setIntervalMs(+e.target.value)} className="w-full accent-[rgb(var(--pollen))]" />
            <p className="mt-1 text-xs text-muted">Frames are only sent when the previous one has finished; slower devices should use longer intervals. This is sampled inference, not continuous real-time video.</p>
          </div>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted">Flowers in last frame</dt><dd className="font-mono">{live?.flower_count ?? "—"}</dd>
            <dt className="text-muted">Backend latency</dt><dd className="font-mono">{live ? `${live.latency_ms.toFixed(0)} ms` : "—"}</dd>
            <dt className="text-muted">Frames analysed</dt><dd className="font-mono" data-testid="frames-analysed">{stats.frames}</dd>
            <dt className="text-muted">Skipped (busy)</dt><dd className="font-mono">{stats.dropped}</dd>
            <dt className="text-muted">Transport</dt><dd className="font-mono">{stats.transport}</dd>
          </dl>
          <div className="flex items-center gap-2 text-xs"><MethodBadge method="trained_model" /> live boxes come from the backend detector (fast mode).</div>
          {live?.warnings.map((w, i) => <Notice key={i}>{w}</Notice>)}
          <Notice>Phones need HTTPS for camera access. On a LAN, run the dev server with HTTPS or use image upload. <RefreshCw size={12} className="inline" /> Live frames are not saved; use “Capture & analyse” to store a full analysis.</Notice>
        </div>
      </div>
    </Card>
  );
}
