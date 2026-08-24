import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const REAL = "#0f7b5f";
const PLAN = "#4c6ef5";

interface Point {
  ts: number;
  real?: number;
  plan?: number;
}

function fmtDay(ts: number | string) {
  return new Date(Number(ts)).toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

function toTs(iso: string) {
  return new Date(iso + "T00:00:00").getTime();
}

export default function WeightChart({
  real,
  expected,
}: {
  real: { date: string; weight_kg: number }[];
  expected: { date: string; weight_kg: number }[];
}) {
  const byDate = new Map<number, Point>();
  for (const p of expected) {
    byDate.set(toTs(p.date), { ts: toTs(p.date), plan: p.weight_kg });
  }
  for (const p of real) {
    const ts = toTs(p.date);
    const cur = byDate.get(ts) ?? { ts };
    cur.real = p.weight_kg;
    byDate.set(ts, cur);
  }
  const data = [...byDate.values()].sort((a, b) => a.ts - b.ts);

  const values = data.flatMap((p) => [p.real, p.plan]).filter((v): v is number => v != null);
  const min = Math.floor(Math.min(...values)) - 1;
  const max = Math.ceil(Math.max(...values)) + 1;

  return (
    <div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={fmtDay}
            tick={{ fontSize: 11, fill: "var(--ink-3)", fontFamily: "IBM Plex Mono" }}
            tickLine={false}
            axisLine={{ stroke: "var(--line)" }}
            minTickGap={40}
          />
          <YAxis
            domain={[min, max]}
            tick={{ fontSize: 11, fill: "var(--ink-3)", fontFamily: "IBM Plex Mono" }}
            tickLine={false}
            axisLine={false}
            width={52}
            unit=" kg"
          />
          <Tooltip
            labelFormatter={(label) => fmtDay(Number(label))}
            formatter={(value, name) => [
              `${Number(value).toFixed(1)} kg`,
              name === "real" ? "Peso real" : "Previsto",
            ]}
            contentStyle={{
              borderRadius: 10,
              border: "1px solid var(--line)",
              fontFamily: "Barlow",
              fontSize: 13,
            }}
          />
          <Line
            dataKey="plan"
            name="plan"
            stroke={PLAN}
            strokeWidth={2}
            strokeDasharray="6 5"
            dot={false}
            connectNulls
          />
          <Line
            dataKey="real"
            name="real"
            stroke={REAL}
            strokeWidth={2}
            dot={{ r: 3, fill: REAL, strokeWidth: 0 }}
            activeDot={{ r: 5, stroke: "var(--surface)", strokeWidth: 2 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="legend-row">
        <span className="key">
          <span className="swatch" style={{ background: REAL }} /> Peso real
        </span>
        <span className="key">
          <span
            className="swatch"
            style={{
              background:
                "repeating-linear-gradient(90deg, #4c6ef5 0 4px, transparent 4px 7px)",
            }}
          />
          Previsto por el plan
        </span>
      </div>
    </div>
  );
}
