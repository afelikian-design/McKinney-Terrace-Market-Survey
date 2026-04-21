import { useEffect } from "react";

export default function Toast({ toast, onDismiss }) {
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(onDismiss, 6000);
    return () => clearTimeout(t);
  }, [toast, onDismiss]);

  if (!toast) return null;

  const base =
    "toast fixed top-6 right-6 z-50 max-w-sm rounded-lg px-4 py-3 shadow-lg text-sm font-medium";
  const tone =
    toast.type === "success"
      ? "bg-emerald-600 text-white"
      : "bg-red-600 text-white";

  return (
    <div role="status" className={`${base} ${tone}`}>
      {toast.message}
    </div>
  );
}
