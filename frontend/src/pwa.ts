/* Install-prompt plumbing: Chrome fires beforeinstallprompt before React
   mounts, so it is captured at module scope and handed to whoever asks. */

export type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

let deferredPrompt: InstallPromptEvent | null = null;
const listeners = new Set<() => void>();

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e as InstallPromptEvent;
  listeners.forEach((fn) => fn());
});

window.addEventListener("appinstalled", () => {
  deferredPrompt = null;
  listeners.forEach((fn) => fn());
});

export function getInstallPrompt(): InstallPromptEvent | null {
  return deferredPrompt;
}

export function clearInstallPrompt() {
  deferredPrompt = null;
  listeners.forEach((fn) => fn());
}

export function onInstallChange(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function isStandalone(): boolean {
  return window.matchMedia("(display-mode: standalone)").matches;
}
