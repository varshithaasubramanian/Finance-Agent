import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useBudget, currentPeriod } from "../hooks/useBudget";
import * as api from "../services/api";
import { Card, CardHeader, Button, Field, Input, Spinner } from "../components/ui";
import { formatMoney, periodLabel } from "../utils/format";

interface DraftCategory {
  name: string;
  allocation: string;
}

const DEFAULT_DRAFT: DraftCategory[] = [
  { name: "Food", allocation: "1000" },
  { name: "Travel", allocation: "800" },
  { name: "Others", allocation: "200" },
];

export default function BudgetSetup() {
  const { budget, budgets, refresh, selectBudget, needsSetup, loading } = useBudget();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const forceNew = searchParams.get("new") === "1";

  // Editing the currently-selected budget's totals, vs. creating a brand new month
  const isCreating = needsSetup || forceNew || !budget;

  const [period, setPeriod] = useState(currentPeriod());
  const [totalAmount, setTotalAmount] = useState("2000");
  const [allowOver, setAllowOver] = useState(false);
  const [categories, setCategories] = useState<DraftCategory[]>(DEFAULT_DRAFT);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isCreating && budget) {
      setTotalAmount(String(budget.total_amount));
      setAllowOver(budget.allow_over_allocation);
    }
    if (isCreating) {
      // Default the new-month picker to one past the most recent existing budget, else this month
      if (budgets.length > 0) {
        const [y, m] = budgets[0].period.split("-").map(Number);
        const next = new Date(y, m - 1 + 1, 1); // first of the month after the newest budget
        const today = new Date();
        const candidate = next > today ? next : today;
        setPeriod(`${candidate.getFullYear()}-${String(candidate.getMonth() + 1).padStart(2, "0")}`);
      } else {
        setPeriod(currentPeriod());
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCreating, budget]);

  const allocatedTotal = categories.reduce((sum, c) => sum + (parseFloat(c.allocation) || 0), 0);
  const total = parseFloat(totalAmount) || 0;
  const overAllocated = !allowOver && allocatedTotal > total;
  const periodAlreadyExists = budgets.some((b) => b.period === period);

  function updateCategory(idx: number, field: keyof DraftCategory, value: string) {
    setCategories((prev) => prev.map((c, i) => (i === idx ? { ...c, [field]: value } : c)));
  }

  function addCategoryRow() {
    setCategories((prev) => [...prev, { name: "", allocation: "0" }]);
  }

  function removeCategoryRow(idx: number) {
    setCategories((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.createBudget({
        period,
        total_amount: total,
        allow_over_allocation: allowOver,
        categories: categories
          .filter((c) => c.name.trim())
          .map((c) => ({ name: c.name.trim(), allocation: parseFloat(c.allocation) || 0 })),
      });
      await refresh();
      selectBudget(created.id);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Failed to create budget");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!budget) return;
    setError(null);
    setSubmitting(true);
    try {
      await api.updateBudget(budget.id, { total_amount: total, allow_over_allocation: allowOver });
      await refresh();
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Failed to update budget");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner />
      </div>
    );
  }

  if (!isCreating && budget) {
    return (
      <div className="max-w-xl space-y-6">
        <div>
          <h1 className="font-display font-bold text-2xl text-ink">Budget setup</h1>
          <p className="text-sm text-slate-500 mt-1">Editing your {periodLabel(budget.period)} budget.</p>
        </div>
        <Card>
          <form onSubmit={handleUpdate}>
            <Field label="Total monthly budget (₹)">
              <Input type="number" min={0} step="0.01" value={totalAmount} onChange={(e) => setTotalAmount(e.target.value)} required />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-600 mb-4">
              <input type="checkbox" checked={allowOver} onChange={(e) => setAllowOver(e.target.checked)} className="rounded" />
              Allow category allocations to exceed the total budget
            </label>
            {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : "Save changes"}
            </Button>
          </form>
        </Card>
        <p className="text-sm text-slate-500">
          To manage categories (add, edit allocations, delete), head to the{" "}
          <a href="/categories" className="text-brand-600 font-medium hover:underline">
            Categories
          </a>{" "}
          page. To set up a different month,{" "}
          <a href="/budget-setup?new=1" className="text-brand-600 font-medium hover:underline">
            create a new month's budget
          </a>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="font-display font-bold text-2xl text-ink">
          {budgets.length === 0 ? "Set up your budget" : "Set up a new month"}
        </h1>
        <p className="text-sm text-slate-500 mt-1">Choose a month, define a total, and split it into categories.</p>
      </div>

      <Card>
        <form onSubmit={handleCreate}>
          <Field label="Month">
            <Input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} required />
          </Field>
          {periodAlreadyExists && (
            <p className="text-sm text-critical-600 mb-4">
              You already have a budget for {periodLabel(period)}. Pick a different month, or go edit that one from
              the month switcher instead.
            </p>
          )}

          <Field label="Total monthly budget (₹)">
            <Input type="number" min={0} step="0.01" value={totalAmount} onChange={(e) => setTotalAmount(e.target.value)} required />
          </Field>

          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">Categories</span>
            <button type="button" onClick={addCategoryRow} className="text-sm text-brand-600 font-medium hover:underline">
              + Add category
            </button>
          </div>
          <div className="space-y-2 mb-2">
            {categories.map((c, idx) => (
              <div key={idx} className="flex gap-2 items-center">
                <Input
                  placeholder="Category name"
                  value={c.name}
                  onChange={(e) => updateCategory(idx, "name", e.target.value)}
                  className="flex-1"
                />
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  placeholder="Amount"
                  value={c.allocation}
                  onChange={(e) => updateCategory(idx, "allocation", e.target.value)}
                  className="w-32"
                />
                <button
                  type="button"
                  onClick={() => removeCategoryRow(idx)}
                  className="text-slate-400 hover:text-critical-500 px-1"
                  aria-label="Remove category"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          <p className="text-xs text-slate-500 mb-4">
            Allocated: <span className="num">{formatMoney(allocatedTotal)}</span> of{" "}
            <span className="num">{formatMoney(total)}</span>
            {overAllocated && <span className="text-critical-600 font-medium"> — exceeds total budget</span>}
          </p>

          <label className="flex items-center gap-2 text-sm text-slate-600 mb-4">
            <input type="checkbox" checked={allowOver} onChange={(e) => setAllowOver(e.target.checked)} className="rounded" />
            Allow category allocations to exceed the total budget
          </label>

          {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}

          <Button type="submit" disabled={submitting || overAllocated || periodAlreadyExists} className="w-full sm:w-auto">
            {submitting ? "Creating..." : "Create budget"}
          </Button>
          <p className="text-xs text-slate-400 mt-3">
            Leave categories empty to start with the default set (Food, Travel, Education, Shopping, Entertainment,
            Bills, Health, Others) with zero allocation.
          </p>
        </form>
      </Card>
    </div>
  );
}
