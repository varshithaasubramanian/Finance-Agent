import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as api from "../services/api";
import type { Budget } from "../types";

interface BudgetContextValue {
  budget: Budget | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  needsSetup: boolean;
}

const BudgetContext = createContext<BudgetContextValue | undefined>(undefined);

export function BudgetProvider({ children }: { children: React.ReactNode }) {
  const [budget, setBudget] = useState<Budget | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const b = await api.getCurrentBudget();
      setBudget(b);
      setNeedsSetup(false);
    } catch (err: any) {
      if (err?.status === 404) {
        setNeedsSetup(true);
        setBudget(null);
      } else {
        setError(err?.message || "Failed to load budget");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <BudgetContext.Provider value={{ budget, loading, error, refresh, needsSetup }}>
      {children}
    </BudgetContext.Provider>
  );
}

export function useBudget(): BudgetContextValue {
  const ctx = useContext(BudgetContext);
  if (!ctx) throw new Error("useBudget must be used within a BudgetProvider");
  return ctx;
}
