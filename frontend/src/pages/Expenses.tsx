import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useBudget } from "../hooks/useBudget";
import * as api from "../services/api";
import type { Expense, PaymentMethod } from "../types";
import { Card, Button, Input, Select, Modal, Field, Spinner, EmptyState, Badge } from "../components/ui";
import { formatDate, formatMoney } from "../utils/format";

const PAYMENT_METHODS: PaymentMethod[] = ["Cash", "UPI", "Debit Card", "Credit Card", "Bank Transfer", "Other"];

export default function Expenses() {
  const { budget, needsSetup } = useBudget();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [sortBy, setSortBy] = useState<"date" | "amount" | "category">("date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [editing, setEditing] = useState<Expense | null>(null);
  const [deleting, setDeleting] = useState<Expense | null>(null);

  async function load() {
    if (!budget) return;
    setLoading(true);
    try {
      const data = await api.listExpenses(budget.id, {
        search: search || undefined,
        category_id: categoryId || undefined,
        payment_method: paymentMethod || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      });
      setExpenses(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [budget, search, categoryId, paymentMethod, sortBy, sortDir]);

  const total = useMemo(() => expenses.reduce((sum, e) => sum + e.amount, 0), [expenses]);

  async function handleDelete() {
    if (!budget || !deleting) return;
    await api.deleteExpense(budget.id, deleting.id);
    setDeleting(null);
    load();
  }

  if (needsSetup || !budget) {
    return (
      <EmptyState
        title="No budget yet"
        description="Set up a budget first to start tracking expenses."
        action={
          <Link to="/budget-setup">
            <Button>Set up budget</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="font-display font-bold text-2xl text-ink">Expenses</h1>
          <p className="text-sm text-slate-500 mt-1">
            {expenses.length} expense(s) &middot; total <span className="num">{formatMoney(total, budget.currency_symbol)}</span>
          </p>
        </div>
        <Link to="/add-expense">
          <Button>+ Add expense</Button>
        </Link>
      </div>

      <Card>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <Input placeholder="Search description..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <Select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">All categories</option>
            {budget.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
            <option value="">All payment methods</option>
            {PAYMENT_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>
          <Select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
            <option value="date">Sort by date</option>
            <option value="amount">Sort by amount</option>
            <option value="category">Sort by category</option>
          </Select>
          <Select value={sortDir} onChange={(e) => setSortDir(e.target.value as any)}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </Select>
        </div>
      </Card>

      <Card className="p-0 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : expenses.length === 0 ? (
          <EmptyState title="No expenses found" description="Try adjusting your filters, or add a new expense." />
        ) : (
          <div className="divide-y divide-ledger">
            {expenses.map((e) => (
              <div key={e.id} className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50/60 transition-colors">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-sm text-ink truncate">{e.description || "Expense"}</p>
                    {e.is_ai_entered && <Badge tone="brand">AI</Badge>}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {e.category_name} &middot; {formatDate(e.date)} &middot; {e.payment_method}
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="num font-semibold text-ink">{formatMoney(e.amount, budget.currency_symbol)}</span>
                  <button onClick={() => setEditing(e)} className="text-xs text-slate-500 hover:text-brand-600 px-1.5">
                    Edit
                  </button>
                  <button onClick={() => setDeleting(e)} className="text-xs text-slate-500 hover:text-critical-600 px-1.5">
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {editing && (
        <EditExpenseModal
          expense={editing}
          budgetId={budget.id}
          categories={budget.categories}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
        />
      )}

      <Modal open={!!deleting} onClose={() => setDeleting(null)} title="Delete expense?">
        <p className="text-sm text-slate-600 mb-4">
          This will permanently remove "{deleting?.description || "this expense"}" ({formatMoney(deleting?.amount || 0, budget.currency_symbol)}).
        </p>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" onClick={() => setDeleting(null)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete}>
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}

function EditExpenseModal({
  expense,
  budgetId,
  categories,
  onClose,
  onSaved,
}: {
  expense: Expense;
  budgetId: string;
  categories: { id: string; name: string }[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [amount, setAmount] = useState(String(expense.amount));
  const [categoryId, setCategoryId] = useState(expense.category_id);
  const [description, setDescription] = useState(expense.description);
  const [date, setDate] = useState(expense.date);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>(expense.payment_method);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await api.updateExpense(budgetId, expense.id, {
        amount: parseFloat(amount),
        category_id: categoryId,
        description,
        date,
        payment_method: paymentMethod,
      } as any);
      onSaved();
    } catch (err: any) {
      setError(err.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Edit expense">
      <Field label="Amount (₹)">
        <Input type="number" step="0.01" min={0} value={amount} onChange={(e) => setAmount(e.target.value)} />
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
      <Field label="Description">
        <Input value={description} onChange={(e) => setDescription(e.target.value)} />
      </Field>
      <Field label="Date">
        <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </Field>
      <Field label="Payment method">
        <Select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}>
          {PAYMENT_METHODS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </Select>
      </Field>
      {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
      <div className="flex gap-2 justify-end">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save changes"}
        </Button>
      </div>
    </Modal>
  );
}
