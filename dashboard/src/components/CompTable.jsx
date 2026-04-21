import { colorFor } from "../propertyColors";
import { formatPsf, formatRent, formatSqft, truncate } from "../utils";

const COLUMNS = [
  "Property Name",
  "Unit",
  "Date Available",
  "Concession",
  "Floorplan",
  "Sq Ft",
  "Asking Rate",
  "PSF",
];

export default function CompTable({ rows }) {
  if (rows.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="max-h-[560px] overflow-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-navy text-white">
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c}
                  className="px-3 py-2 text-left font-semibold whitespace-nowrap"
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const isSubject = row.is_subject;
              const base = isSubject
                ? "bg-[#eff6ff] font-medium"
                : idx % 2 === 0
                  ? "bg-white"
                  : "bg-slate-50";
              const concession = row.specials || "—";
              return (
                <tr
                  key={`${row.property}-${row.unit_number ?? idx}-${row.floorplan ?? ""}-${idx}`}
                  className={`${base} border-t border-slate-200`}
                >
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block h-3 w-3 rounded-full ring-1 ring-black/10"
                        style={{ background: colorFor(row.property) }}
                        aria-hidden
                      />
                      <span
                        className={isSubject ? "font-semibold text-subject" : ""}
                      >
                        {row.property}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2">{row.unit_number || "—"}</td>
                  <td className="px-3 py-2">{row.available_date || "—"}</td>
                  <td
                    className="max-w-[220px] px-3 py-2 text-slate-700"
                    title={row.specials || undefined}
                  >
                    {row.specials ? truncate(concession, 40) : "—"}
                  </td>
                  <td className="px-3 py-2">{row.floorplan || "—"}</td>
                  <td className="px-3 py-2">{formatSqft(row.sqft)}</td>
                  <td className="px-3 py-2">{formatRent(row.rent)}</td>
                  <td className="px-3 py-2">{formatPsf(row.rent, row.sqft)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
