import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useBudget } from "../hooks/useBudget";
import * as api from "../services/api";
import type { RecurringExpense, RecurrenceFrequency } from "../types";
import { Card, CardHeader, Button, Input, Select, Modal, Field, Badge, ProgressBar, EmptyState, Spinner } from "../components/ui";
import { CategoryIcon } from "../components/CategoryIcon";
import { formatDate, formatMoney } from "../utils/format";

const ICONS = ["utensils", "bus", "book", "bag", "film", "receipt", "heart", "dots", "wallet", "education"];
const COLORS = ["#0F766E", "#2563EB", "#7C3AED", "#DB2777", "#EA580C", "#0891B2", "#DC2626", "#64748B", "#CA8A04", "#059669"];
const FREQUENCIES: RecurrenceFrequency[] = ["Daily", "Weekly", "Monthly"];

export default function Categories() {
  const { budget, refresh, needsSetup } = useBudget();
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [recurring, setRecurring] = useState<RecurringExpense[]>([]);
  const [showRecurringForm, setShowRecurringForm] = useState(false);

  useEffect(() => {
    if (!budget) return;
    api.listRecurring(budget.id).then(setRecurring);
  }, [budget]);

  async function reloadRecurring() {
    if (!budget) return;
    setRecurring(await api.listRecurring(budget.id));
  }

  if (needsSetup || !budget) {
    return (
      <EmptyState
        title="No budget yet"
        description="Set up a budget first to manage categories."
        action={
          <Link to="/budget-setup">
            <Button>Set up budget</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl text-ink">Categories</h1>
          <p className="text-sm text-slate-500 mt-1">Manage budget categories and recurring expenses.</p>
        </div>
        <Button onClick={() => setCreating(true)}>+ Add category</Button>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {budget.categories.map((c) => (
          <Card key={c.id} className="relative">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0" style={{ backgroundColor: c.color }}>
                <CategoryIcon icon={c.icon} size={16} />
              </span>
              <span className="font-medium text-ink flex-1">{c.name}</span>
              {c.is_travel && <Badge tone="brand">Travel</Badge>}
            </div>
            <ProgressBar percent={c.percent_used} size="sm" />
            <div className="flex justify-between text-xs num text-slate-500 mt-1.5 mb-3">
              <span>{formatMoney(c.spent, budget.currency_symbol)} spent</span>
              <span>{formatMoney(c.allocation, budget.currency_symbol)} budget</span>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setEditingId(c.id)} className="text-xs text-slate-500 hover:text-brand-600">
                Edit
              </button>
              <button onClick={() => setDeletingId(c.id)} className="text-xs text-slate-500 hover:text-critical-600">
                Delete
              </button>
            </div>
          </Card>
        ))}
      </div>

      {/* Recurring expenses */}
      <Card>
        <CardHeader
          title="Recurring expenses"
          subtitle="Bus passes, subscriptions, fees — included in forecasts and affordability checks"
          action={
            <Button variant="secondary" onClick={() => setShowRecurringForm(true)}>
              + Add recurring
            </Button>
          }
        />
        {recurring.length === 0 ? (
          <p className="text-sm text-slate-400 py-4">No recurring expenses yet.</p>
        ) : (
          <div className="divide-y divide-ledger">
            {recurring.map((r) => (
              <div key={r.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium text-sm text-ink">{r.name}</p>
                  <p className="text-xs text-slate-500">
                    {r.category_name} &middot; {r.frequency} &middot; next due {formatDate(r.next_due_date)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="num font-medium text-ink">{formatMoney(r.amount, budget.currency_symbol)}</span>
                  <button
                    onClick={async () => {
                      await api.deleteRecurring(budget.id, r.id);
                      reloadRecurring();
                    }}
                    className="text-xs text-slate-500 hover:text-critical-600"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {creating && (
        <CategoryFormModal
          budgetId={budget.id}
          onClose={() => setCreating(false)}
          onSaved={async () => {
            setCreating(false);
            await refresh();
          }}
        />
      )}

      {editingId && (
        <CategoryFormModal
          budgetId={budget.id}
          category={budget.categories.find((c) => c.id === editingId)!}
          onClose={() => setEditingId(null)}
          onSaved={async () => {
            setEditingId(null);
            await refresh();
          }}
        />
      )}

      <Modal open={!!deletingId} onClose={() => setDeletingId(null)} title="Delete category?">
        <p className="text-sm text-slate-600 mb-4">
          This will permanently delete this category and all of its expenses.
        </p>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={() => setDeletingId(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={async () => {
              if (deletingId) await api.deleteCategory(budget.id, deletingId);
              setDeletingId(null);
              await refresh();
            }}
          >
            Delete
          </Button>
        </div>
      </Modal>

      {showRecurringForm && (
        <RecurringFormModal
          budgetId={budget.id}
          categories={budget.categories}
          onClose={() => setShowRecurringForm(false)}
          onSaved={async () => {
            setShowRecurringForm(false);
            await reloadRecurring();
          }}
        />
      )}
    </div>
  );
}

function CategoryFormModal({
  budgetId,
  category,
  onClose,
  onSaved,
}: {
  budgetId: string;
  category?: any;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(category?.name || "");
  const [allocation, setAllocation] = useState(String(category?.allocation ?? "0"));
  const [color, setColor] = useState(category?.color || COLORS[0]);
  const [icon, setIcon] = useState(category?.icon || ICONS[0]);
  const [isTravel, setIsTravel] = useState(category?.is_travel || false);
  const [fixedAmount, setFixedAmount] = useState(String(category?.fixed_amount ?? "0"));
  const [spendingLimit, setSpendingLimit] = useState(category?.spending_limit != null ? String(category.spending_limit) : "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name,
        allocation: parseFloat(allocation) || 0,
        color,
        icon,
        is_travel: isTravel,
        fixed_amount: parseFloat(fixedAmount) || 0,
        spending_limit: spendingLimit ? parseFloat(spendingLimit) : null,
      };
      if (category) {
        await api.updateCategory(budgetId, category.id, payload as any);
      } else {
        await api.createCategory(budgetId, payload as any);
      }
      onSaved();
    } catch (err: any) {
      setError(err.message || "Failed to save category");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={category ? "Edit category" : "New category"}>
      <Field label="Name">
        <Input value={name} onChange={(e) => setName(e.target.value)} required />
      </Field>
      <Field label="Monthly allocation (₹)">
        <Input type="number" min={0} step="0.01" value={allocation} onChange={(e) => setAllocation(e.target.value)} />
      </Field>
      <Field label="Optional spending limit per day (₹)">
        <Input type="number" min={0} step="0.01" value={spendingLimit} onChange={(e) => setSpendingLimit(e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Color">
          <div className="flex flex-wrap gap-2">
            {COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className={`w-6 h-6 rounded-full ${color === c ? "ring-2 ring-offset-1 ring-ink" : ""}`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </Field>
        <Field label="Icon">
          <div className="flex flex-wrap gap-2">
            {ICONS.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => setIcon(i)}
                className={`w-7 h-7 rounded-lg flex items-center justify-center border ${
                  icon === i ? "border-brand-600 bg-brand-50" : "border-ledger"
                }`}
              >
                <CategoryIcon icon={i} size={14} />
              </button>
            ))}
          </div>
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-600 my-3">
        <input type="checkbox" checked={isTravel} onChange={(e) => setIsTravel(e.target.checked)} className="rounded" />
        This is the travel category (enables fixed vs variable travel budget tracking)
      </label>
      {isTravel && (
        <Field label="Fixed travel cost (e.g. bus pass) per month (₹)">
          <Input type="number" min={0} step="0.01" value={fixedAmount} onChange={(e) => setFixedAmount(e.target.value)} />
        </Field>
      )}
      {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
      <div className="flex gap-2 justify-end">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving || !name}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>
    </Modal>
  );
}

function RecurringFormModal({
  budgetId,
  categories,
  onClose,
  onSaved,
}: {
  budgetId: string;
  categories: { id: string; name: string }[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState("");
  const [categoryId, setCategoryId] = useState(categories[0]?.id || "");
  const [amount, setAmount] = useState("");
  const [frequency, setFrequency] = useState<RecurrenceFrequency>("Monthly");
  const [nextDueDate, setNextDueDate] = useState(new Date().toISOString().slice(0, 10));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await api.createRecurring(budgetId, {
        name,
        category_id: categoryId,
        amount: parseFloat(amount),
        frequency,
        next_due_date: nextDueDate,
      });
      onSaved();
    } catch (err: any) {
      setError(err.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="New recurring expense">
      <Field label="Name">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Hostel fee" />
      </Field>
      <Field label="Category">
        <Select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Amount (₹)">
        <Input type="number" min={0} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
      </Field>
      <Field label="Frequency">
        <Select value={frequency} onChange={(e) => setFrequency(e.target.value as RecurrenceFrequency)}>
          {FREQUENCIES.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Next due date">
        <Input type="date" value={nextDueDate} onChange={(e) => setNextDueDate(e.target.value)} />
      </Field>
      {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
      <div className="flex gap-2 justify-end">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving || !name || !amount}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>
    </Modal>
  );
}
