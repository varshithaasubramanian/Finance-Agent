import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as api from "../services/api";
import type { Budget } from "../types";

function currentPeriod(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

interface BudgetContextValue {
  budget: Budget | null;
  budgets: Budget[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  selectBudget: (budgetId: string) => void;
  needsSetup: boolean;
  isViewingCurrentMonth: boolean;
}

const BudgetContext = createContext<BudgetContextValue | undefined>(undefined);

export function BudgetProvider({ children }: { children: React.ReactNode }) {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.listBudgets();
      // Newest period first
      const sorted = [...list].sort((a, b) => (a.period < b.period ? 1 : -1));
      setBudgets(sorted);

      setSelectedId((prevSelected) => {
        if (prevSelected && sorted.some((b) => b.id === prevSelected)) {
          return prevSelected; // keep whatever the user was looking at
        }
        const thisMonth = sorted.find((b) => b.period === currentPeriod());
        return thisMonth ? thisMonth.id : sorted[0]?.id ?? null;
      });
    } catch (err: any) {
      setError(err?.message || "Failed to load budgets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const budget = useMemo(() => budgets.find((b) => b.id === selectedId) ?? null, [budgets, selectedId]);
  const needsSetup = !loading && budgets.length === 0;
  const isViewingCurrentMonth = budget?.period === currentPeriod();

  function selectBudget(budgetId: string) {
    setSelectedId(budgetId);
  }

  return (
    <BudgetContext.Provider
      value={{ budget, budgets, loading, error, refresh, selectBudget, needsSetup, isViewingCurrentMonth }}
    >
      {children}
    </BudgetContext.Provider>
  );
}

export function useBudget(): BudgetContextValue {
  const ctx = useContext(BudgetContext);
  if (!ctx) throw new Error("useBudget must be used within a BudgetProvider");
  return ctx;
}

export { currentPeriod };
