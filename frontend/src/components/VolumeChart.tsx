import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const BRAND = "#0f7b5f";

interface Week {
  week_start: string;
  sessions: number;
  distance_km: number;
  minutes: number;
}

function fmtWeek(iso: string) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

export default function VolumeChart({
  weeks,
  metric,
}: {
  weeks: Week[];
  metric: "distance_km" | "minutes";
}) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={weeks} margin={{ top: 8, right: 4, bottom: 0, left: -22 }} barCategoryGap="22%">
        <CartesianGrid stroke="var(--line)" vertical={false} />
        <XAxis
          dataKey="week_start"
          tickFormatter={fmtWeek}
          tick={{ fontSize: 11, fill: "var(--ink-3)", fontFamily: "IBM Plex Mono" }}
          tickLine={false}
          axisLine={{ stroke: "var(--line)" }}
          minTickGap={30}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--ink-3)", fontFamily: "IBM Plex Mono" }}
          tickLine={false}
          axisLine={false}
          width={44}
          allowDecimals={false}
        />
        <Tooltip
          cursor={{ fill: "var(--surface-2)", opacity: 0.6 }}
          labelFormatter={(iso) => `Semana del ${fmtWeek(String(iso))}`}
          formatter={(value, _name, item) => {
            const week = item?.payload as Week | undefined;
            const label = metric === "distance_km" ? "km" : "min";
            const extra = week ? ` · ${week.sessions} sesiones` : "";
            return [`${value} ${label}${extra}`, ""];
          }}
          contentStyle={{
            borderRadius: 10,
            border: "1px solid var(--line)",
            fontFamily: "Barlow",
            fontSize: 13,
          }}
        />
        <Bar dataKey={metric} fill={BRAND} radius={[4, 4, 0, 0]} maxBarSize={26} />
      </BarChart>
    </ResponsiveContainer>
  );
}
