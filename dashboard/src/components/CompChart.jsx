import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { colorFor } from "../propertyColors";
import { formatRent, formatSqft } from "../utils";

function StarShape(props) {
  const { cx, cy, fill } = props;
  if (cx == null || cy == null) return null;
  const spikes = 5;
  const outer = 9;
  const inner = 4;
  let rot = (Math.PI / 2) * 3;
  const step = Math.PI / spikes;
  let path = "";
  for (let i = 0; i < spikes; i += 1) {
    path += `${i === 0 ? "M" : "L"} ${cx + Math.cos(rot) * outer} ${cy + Math.sin(rot) * outer} `;
    rot += step;
    path += `L ${cx + Math.cos(rot) * inner} ${cy + Math.sin(rot) * inner} `;
    rot += step;
  }
  path += "Z";
  return <path d={path} fill={fill} stroke="#0f172a" strokeWidth={1} />;
}

function CircleShape(props) {
  const { cx, cy, fill } = props;
  if (cx == null || cy == null) return null;
  return (
    <circle cx={cx} cy={cy} r={5} fill={fill} stroke="#ffffff" strokeWidth={1} />
  );
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-semibold" style={{ color: colorFor(d.property) }}>
        {d.property}
      </div>
      <div>Unit: {d.unit_number || "—"}</div>
      <div>Floorplan: {d.floorplan || "—"}</div>
      <div>Sq Ft: {formatSqft(d.sqft)}</div>
      <div>Rent: {formatRent(d.rent)}</div>
      <div>Available: {d.available_date || "—"}</div>
      <div className="mt-1 max-w-[240px] whitespace-normal text-slate-600">
        Concession: {d.specials || "—"}
      </div>
    </div>
  );
}

export default function CompChart({ title, series }) {
  const hasData = series.some((s) => s.data.length > 0);

  return (
    <section className="mb-10">
      <h2 className="mb-4 text-lg font-semibold text-navy">{title}</h2>
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        {!hasData ? (
          <div className="py-16 text-center text-sm text-slate-500">
            Not enough data to render the chart.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart margin={{ top: 20, right: 24, bottom: 40, left: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                type="number"
                dataKey="sqft"
                name="Square Feet"
                domain={["dataMin - 50", "dataMax + 50"]}
                tickFormatter={(v) => formatSqft(v)}
                label={{
                  value: "Square Feet",
                  position: "insideBottom",
                  offset: -20,
                  fill: "#0f172a",
                }}
              />
              <YAxis
                type="number"
                dataKey="rent"
                name="Rent"
                domain={["dataMin - 100", "dataMax + 100"]}
                tickFormatter={(v) => `$${Math.round(v).toLocaleString()}`}
                label={{
                  value: "Rental Rates",
                  angle: -90,
                  position: "insideLeft",
                  offset: 0,
                  fill: "#0f172a",
                }}
              />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={<ChartTooltip />}
              />
              <Legend
                verticalAlign="bottom"
                wrapperStyle={{ paddingTop: 16 }}
              />
              {series.map((s) => (
                <Scatter
                  key={s.name}
                  name={s.name}
                  data={s.data}
                  fill={s.color}
                  shape={s.isSubject ? <StarShape /> : <CircleShape />}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
