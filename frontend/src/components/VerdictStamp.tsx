const STAMPS: Record<string, { text: string; cls: string }> = {
  on_track: { text: "En objetivo", cls: "good" },
  at_risk: { text: "En riesgo", cls: "warn" },
  off_track: { text: "Retrasado", cls: "bad" },
  no_data: { text: "Sin datos", cls: "neutral" },
};

/** The coach's rubber stamp — the app's signature verdict element. */
export default function VerdictStamp({ status }: { status: string }) {
  const stamp = STAMPS[status] ?? STAMPS.no_data;
  return <span className={`stamp ${stamp.cls}`}>{stamp.text}</span>;
}
