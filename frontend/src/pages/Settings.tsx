import { useEffect, useState } from "react";
import { useBudget } from "../hooks/useBudget";
import * as api from "../services/api";
import type { FinancialGoal } from "../types";
import { Card, CardHeader, Button, Input, Field, Modal, ProgressBar, Badge, EmptyState } from "../components/ui";
import { formatDate, formatMoney, clampPercent } from "../utils/format";

export default function Settings() {
  const { budget } = useBudget();
  const [aiEnabled, setAiEnabled] = useState<boolean | null>(null);
  const [aiModel, setAiModel] = useState<string | null>(null);
  const [goals, setGoals] = useState<FinancialGoal[]>([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (budget) {
      api.getAssistantStatus(budget.id).then((s) => {
        setAiEnabled(s.ai_enabled);
        setAiModel(s.model);
      });
    }
    reloadGoals();
  }, [budget]);

  async function reloadGoals() {
    setGoals(await api.listGoals());
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="font-display font-bold text-2xl text-ink">Settings</h1>
        <p className="text-sm text-slate-500 mt-1">App configuration and financial goals.</p>
      </div>

      <Card>
        <CardHeader title="AI configuration" />
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-slate-600">AI assistant status</span>
          <Badge tone={aiEnabled ? "brand" : "neutral"}>{aiEnabled === null ? "Checking..." : aiEnabled ? "Enabled" : "Disabled (fallback active)"}</Badge>
        </div>
        {aiEnabled && aiModel && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-600">Model</span>
            <span className="num text-ink">{aiModel}</span>
          </div>
        )}
        {!aiEnabled && (
          <p className="text-xs text-slate-500 mt-2">
            Add an <code className="num bg-slate-100 px-1 py-0.5 rounded">AI_API_KEY</code> to your backend's{" "}
            <code className="num bg-slate-100 px-1 py-0.5 rounded">.env</code> file to enable natural-language chat
            and smarter expense parsing. All core features (budgeting, expense tracking, analytics, alerts,
            forecasting, affordability checks) work fully without it.
          </p>
        )}
      </Card>

      <Card>
        <CardHeader title="Currency" />
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-600">Current currency</span>
          <span className="num text-ink">INR ({budget?.currency_symbol || "\u20b9"})</span>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          The currency system is extensible server-side; additional currencies can be added by updating the user's
          currency/currency_symbol fields.
        </p>
      </Card>

      <Card>
        <CardHeader title="Financial goals" subtitle="Track savings targets, separate from budgeting" action={<Button variant="secondary" onClick={() => setCreating(true)}>+ New goal</Button>} />
        {goals.length === 0 ? (
          <EmptyState title="No goals yet" description="Create a savings goal like 'Buy headphones' to track progress." />
        ) : (
          <div className="space-y-4">
            {goals.map((g) => {
              const percent = clampPercent((g.current_amount / g.target_amount) * 100);
              return (
                <div key={g.id} className="hairline pb-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm text-ink">{g.name}</span>
                    <span className="text-xs text-slate-500">Deadline {formatDate(g.deadline)}</span>
                  </div>
                  <ProgressBar percent={percent} size="sm" />
                  <div className="flex justify-between text-xs num text-slate-500 mt-1.5">
                    <span>
                      {formatMoney(g.current_amount, budget?.currency_symbol)} / {formatMoney(g.target_amount, budget?.currency_symbol)}
                    </span>
                    <span>{g.days_left} day(s) left</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Save {formatMoney(g.required_daily_saving, budget?.currency_symbol)}/day or{" "}
                    {formatMoney(g.required_weekly_saving, budget?.currency_symbol)}/week to reach this goal.
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Card className="bg-slate-50 border-dashed">
        <p className="text-xs text-slate-500">
          Your account is private — only you can see your budgets, expenses, and goals. Data is stored server-side
          and persists across sessions and devices as long as you log in with the same account.
        </p>
      </Card>

      {creating && (
        <GoalFormModal
          onClose={() => setCreating(false)}
          onSaved={async () => {
            setCreating(false);
            await reloadGoals();
          }}
        />
      )}
    </div>
  );
}

function GoalFormModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [current, setCurrent] = useState("0");
  const [deadline, setDeadline] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await api.createGoal({
        name,
        target_amount: parseFloat(target),
        current_amount: parseFloat(current) || 0,
        deadline,
      });
      onSaved();
    } catch (err: any) {
      setError(err.message || "Failed to save goal");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New financial goal">
      <Field label="Goal name">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Buy headphones" />
      </Field>
      <Field label="Target amount (₹)">
        <Input type="number" min={0} step="0.01" value={target} onChange={(e) => setTarget(e.target.value)} />
      </Field>
      <Field label="Already saved (₹)">
        <Input type="number" min={0} step="0.01" value={current} onChange={(e) => setCurrent(e.target.value)} />
      </Field>
      <Field label="Deadline">
        <Input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
      </Field>
      {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
      <div className="flex gap-2 justify-end">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving || !name || !target || !deadline}>
          {saving ? "Saving..." : "Create goal"}
        </Button>
      </div>
    </Modal>
  );
}
