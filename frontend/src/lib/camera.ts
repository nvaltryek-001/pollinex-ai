/** Browser camera helpers with explicit, user-readable error mapping. */
export type CameraErrorKind = "insecure" | "unsupported" | "denied" | "not_found" | "busy" | "unknown";

export class CameraError extends Error {
  constructor(public kind: CameraErrorKind, message: string) { super(message); }
}

export function cameraError(e: unknown): CameraError {
  const name = (e as { name?: string })?.name ?? "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return new CameraError("denied", "Camera permission was denied. Allow camera access in your browser settings, or use image upload.");
  if (name === "NotFoundError" || name === "OverconstrainedError")
    return new CameraError("not_found", "No suitable camera was found on this device. Use image upload instead.");
  if (name === "NotReadableError" || name === "AbortError")
    return new CameraError("busy", "The camera is in use by another application or could not be started.");
  return new CameraError("unknown", `Could not start the camera (${name || "unknown error"}).`);
}

export async function openCamera(opts: { deviceId?: string; facing?: "environment" | "user" }): Promise<MediaStream> {
  if (typeof window !== "undefined" && !window.isSecureContext)
    throw new CameraError("insecure", "Camera access needs HTTPS (or http://localhost). Open the app over HTTPS on your phone, or use image upload.");
  if (!navigator.mediaDevices?.getUserMedia)
    throw new CameraError("unsupported", "This browser does not support camera access. Use image upload instead.");
  const video: MediaTrackConstraints = { width: { ideal: 1280 }, height: { ideal: 720 } };
  if (opts.deviceId) video.deviceId = { exact: opts.deviceId };
  else video.facingMode = { ideal: opts.facing ?? "environment" };
  try {
    return await navigator.mediaDevices.getUserMedia({ video, audio: false });
  } catch (e) {
    throw cameraError(e);
  }
}

export async function listCameras(): Promise<MediaDeviceInfo[]> {
  if (!navigator.mediaDevices?.enumerateDevices) return [];
  return (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
}

export function stopStream(s: MediaStream | null) {
  s?.getTracks().forEach((t) => t.stop());
}

/** Grab the current video frame as JPEG (downscaled to maxSide). */
export function captureFrame(video: HTMLVideoElement, maxSide = 1280, quality = 0.85): Promise<Blob> {
  const w = video.videoWidth, h = video.videoHeight;
  if (!w || !h) return Promise.reject(new Error("camera not ready"));
  const s = Math.min(1, maxSide / Math.max(w, h));
  const c = document.createElement("canvas");
  c.width = Math.round(w * s);
  c.height = Math.round(h * s);
  c.getContext("2d")!.drawImage(video, 0, 0, c.width, c.height);
  return new Promise((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error("capture failed"))), "image/jpeg", quality));
}

export function blobToBase64(b: Blob): Promise<string> {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(String(r.result).split(",")[1] ?? "");
    r.onerror = () => rej(r.error);
    r.readAsDataURL(b);
  });
}
