import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Plus } from "lucide-react";
import { useBudget } from "../hooks/useBudget";
import { periodLabel } from "../utils/format";

export function PeriodSwitcher() {
  const { budget, budgets, selectBudget, isViewingCurrentMonth } = useBudget();
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  if (!budget) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-sm font-medium text-ink hover:bg-slate-50 rounded-lg px-2 py-1 transition-colors"
      >
        {periodLabel(budget.period)}
        {!isViewingCurrentMonth && <span className="text-[10px] text-slate-400 font-normal">(past)</span>}
        <ChevronDown size={14} className="text-slate-400" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 mt-1 w-56 bg-white border border-ledger rounded-xl shadow-lg z-50 py-1 max-h-72 overflow-y-auto">
            {budgets.map((b) => (
              <button
                key={b.id}
                onClick={() => {
                  selectBudget(b.id);
                  setOpen(false);
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-50 transition-colors ${
                  b.id === budget.id ? "font-medium text-brand-700 bg-brand-50" : "text-ink"
                }`}
              >
                {periodLabel(b.period)}
              </button>
            ))}
            <div className="border-t border-ledger mt-1 pt-1">
              <button
                onClick={() => {
                  setOpen(false);
                  navigate("/budget-setup?new=1");
                }}
                className="w-full text-left px-3 py-2 text-sm text-brand-600 font-medium hover:bg-slate-50 flex items-center gap-1.5"
              >
                <Plus size={14} /> New month
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
