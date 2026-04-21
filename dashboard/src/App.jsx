import { useEffect, useMemo, useState } from "react";
import CompChart from "./components/CompChart.jsx";
import CompTable from "./components/CompTable.jsx";
import Toast from "./components/Toast.jsx";
import { colorFor } from "./propertyColors";
import { formatTimestamp } from "./utils";

const TABS = [
  { id: "studios", label: "Studios", beds: 0, chartTitle: "Studio — Market Survey Comparison" },
  { id: "one", label: "1-Bedrooms", beds: 1, chartTitle: "1-Bedroom — Market Survey Comparison" },
  { id: "two", label: "2-Bedrooms", beds: 2, chartTitle: "2-Bedroom — Market Survey Comparison" },
  { id: "three", label: "3-Bedrooms", beds: 3, chartTitle: "3-Bedroom — Market Survey Comparison" },
];

function flattenUnits(properties) {
  const rows = [];
  for (const prop of properties || []) {
    for (const unit of prop.units || []) {
      rows.push({
        property: prop.name,
        is_subject: prop.is_subject === true,
        specials: prop.specials || null,
        unit_number: unit.unit_number,
        floorplan: unit.floorplan,
        beds: unit.beds,
        baths: unit.baths,
        sqft: unit.sqft,
        rent: unit.rent,
        available_date: unit.available_date,
      });
    }
  }
  return rows;
}

function filterByBeds(rows, beds) {
  return rows.filter((r) => r.beds === beds && r.rent && r.sqft);
}

function sortRows(rows) {
  return [...rows].sort((a, b) => {
    if (a.is_subject && !b.is_subject) return -1;
    if (!a.is_subject && b.is_subject) return 1;
    const byName = (a.property || "").localeCompare(b.property || "");
    if (byName !== 0) return byName;
    return (a.sqft || 0) - (b.sqft || 0);
  });
}

function buildSeries(rows) {
  const map = new Map();
  for (const r of rows) {
    if (!map.has(r.property)) {
      map.set(r.property, {
        name: r.property,
        color: colorFor(r.property),
        isSubject: r.is_subject,
        data: [],
      });
    }
    map.get(r.property).data.push(r);
  }
  return Array.from(map.values()).sort((a, b) => {
    if (a.isSubject && !b.isSubject) return -1;
    if (!a.isSubject && b.isSubject) return 1;
    return a.name.localeCompare(b.name);
  });
}

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("one");
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch("/data.json", { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          setData({ last_updated: null, properties: [] });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const allRows = useMemo(() => flattenUnits(data?.properties), [data]);
  const activeTabMeta = TABS.find((t) => t.id === activeTab);
  const filteredRows = useMemo(
    () => filterByBeds(allRows, activeTabMeta.beds),
    [allRows, activeTabMeta.beds],
  );
  const sortedRows = useMemo(() => sortRows(filteredRows), [filteredRows]);
  const series = useMemo(() => buildSeries(filteredRows), [filteredRows]);

  async function handleRefresh() {
    const token = import.meta.env.VITE_GITHUB_TOKEN;
    const repo = import.meta.env.VITE_GITHUB_REPO;
    if (!token || !repo) {
      setToast({
        type: "error",
        message: "❌ Missing VITE_GITHUB_TOKEN or VITE_GITHUB_REPO env var.",
      });
      return;
    }
    setRefreshing(true);
    try {
      const res = await fetch(
        `https://api.github.com/repos/${repo}/actions/workflows/scrape.yml/dispatches`,
        {
          method: "POST",
          headers: {
            Accept: "application/vnd.github+json",
            Authorization: `Bearer ${token}`,
            "X-GitHub-Api-Version": "2022-11-28",
          },
          body: JSON.stringify({ ref: "main" }),
        },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setToast({
        type: "success",
        message:
          "✅ Scrape started! Data will refresh in ~3 minutes. Reload the page after.",
      });
    } catch (err) {
      console.error(err);
      setToast({
        type: "error",
        message: "❌ Failed to trigger scrape. Check your GitHub token.",
      });
    } finally {
      setRefreshing(false);
    }
  }

  const hasData =
    !!data && data.last_updated && (data.properties || []).length > 0;

  return (
    <div className="min-h-screen bg-white text-navy">
      <Toast toast={toast} onDismiss={() => setToast(null)} />

      <header className="bg-navy text-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold">
              McKinney Terrace — Comp Tracker
            </h1>
            <p className="text-sm text-slate-300">
              McKinney / Allen Submarket · DFW
            </p>
            <p className="mt-2 text-xs text-slate-400">
              Last updated: {formatTimestamp(data?.last_updated)}
            </p>
          </div>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-white px-4 py-2 text-sm font-semibold text-navy shadow transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {refreshing ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-navy border-t-transparent" />
                Triggering…
              </>
            ) : (
              <>🔄 Refresh Data</>
            )}
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {loading ? (
          <div className="flex min-h-[40vh] items-center justify-center">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-subject" />
          </div>
        ) : !hasData ? (
          <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-10 text-center text-slate-600">
            No data yet — click 🔄 Refresh Data to run your first scrape.
          </div>
        ) : (
          <>
            <nav className="mb-6 flex flex-wrap gap-1 border-b border-slate-200">
              {TABS.map((tab) => {
                const isActive = tab.id === activeTab;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-3 text-sm font-medium transition ${
                      isActive
                        ? "border-b-2 border-navy text-navy"
                        : "border-b-2 border-transparent text-slate-500 hover:text-navy"
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </nav>

            {filteredRows.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-10 text-center text-slate-600">
                No available {activeTabMeta.label.toLowerCase()} units found in
                current data.
              </div>
            ) : (
              <>
                <CompChart title={activeTabMeta.chartTitle} series={series} />
                <CompTable rows={sortedRows} />
              </>
            )}
          </>
        )}
      </main>

      <footer className="border-t border-slate-200 bg-slate-50 py-4 text-center text-xs text-slate-500">
        McKinney Terrace Comp Tracker · Data sourced from Apartments.com &
        RentCafe.
      </footer>
    </div>
  );
}
