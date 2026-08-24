import { useNavigate } from "react-router-dom";

import MonthGrid from "../components/MonthGrid";

/** Home: the calendar. Tap any day to see its meals, activity and log. */
export default function CalendarPage() {
  const navigate = useNavigate();
  return (
    <div className="stack">
      <div className="card">
        <MonthGrid onSelectDay={(iso) => navigate(`/dia/${iso}`)} />
      </div>
      <p className="hint muted" style={{ textAlign: "center", margin: 0 }}>
        Toca cualquier día para ver sus comidas y actividad, o para registrar lo que hiciste.
      </p>
    </div>
  );
}
