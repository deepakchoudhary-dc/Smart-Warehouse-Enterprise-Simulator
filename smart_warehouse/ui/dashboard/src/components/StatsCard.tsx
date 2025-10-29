type StatsCardProps = {
  title: string;
  value: number;
  suffix?: string;
  format?: "integer" | "decimal";
};

function renderValue(value: number, format: StatsCardProps["format"]): string {
  if (Number.isNaN(value) || !Number.isFinite(value)) {
    return "–";
  }
  if (format === "decimal") {
    return value.toFixed(1);
  }
  return Math.round(value).toString();
}

export function StatsCard({ title, value, suffix, format = "integer" }: StatsCardProps) {
  const display = renderValue(value, format);
  return (
    <article className="stats-card">
      <h3>{title}</h3>
      <p>
        {display}
        {suffix ? <span className="stats-card-suffix">{suffix}</span> : null}
      </p>
    </article>
  );
}
