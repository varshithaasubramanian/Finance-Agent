import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useBudget } from "../hooks/useBudget";
import * as api from "../services/api";
import type { ParsedExpense, PaymentMethod } from "../types";
import { Card, Button, Input, Select, TextArea, Field, EmptyState, Badge } from "../components/ui";
import { formatMoney } from "../utils/format";

const PAYMENT_METHODS: PaymentMethod[] = ["Cash", "UPI", "Debit Card", "Credit Card", "Bank Transfer", "Other"];

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function AddExpense() {
  const { budget, needsSetup } = useBudget();
  const [mode, setMode] = useState<"form" | "ai">("ai");

  if (needsSetup || !budget) {
    return (
      <EmptyState
        title="No budget yet"
        description="Set up a budget first before adding expenses."
        action={
          <Link to="/budget-setup">
            <Button>Set up budget</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="max-w-xl space-y-5">
      <div>
        <h1 className="font-display font-bold text-2xl text-ink">Add expense</h1>
        <p className="text-sm text-slate-500 mt-1">Log it by hand, or just describe it in plain English.</p>
      </div>

      <div className="inline-flex bg-slate-100 rounded-xl p-1">
        <button
          onClick={() => setMode("ai")}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            mode === "ai" ? "bg-white shadow-sm text-ink" : "text-slate-500"
          }`}
        >
          ✨ AI quick entry
        </button>
        <button
          onClick={() => setMode("form")}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            mode === "form" ? "bg-white shadow-sm text-ink" : "text-slate-500"
          }`}
        >
          Traditional form
        </button>
      </div>

      {mode === "ai" ? <AIQuickEntry budgetId={budget.id} categories={budget.categories} /> : <TraditionalForm budgetId={budget.id} categories={budget.categories} />}
    </div>
  );
}

function TraditionalForm({ budgetId, categories }: { budgetId: string; categories: { id: string; name: string }[] }) {
  const navigate = useNavigate();
  const [amount, setAmount] = useState("");
  const [categoryId, setCategoryId] = useState(categories[0]?.id || "");
  const [description, setDescription] = useState("");
  const [date, setDate] = useState(today());
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("UPI");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.createExpense(budgetId, {
        amount: parseFloat(amount),
        category_id: categoryId,
        description,
        date,
        payment_method: paymentMethod,
        notes,
      });
      setSuccess(true);
      setAmount("");
      setDescription("");
      setNotes("");
      setTimeout(() => navigate("/expenses"), 700);
    } catch (err: any) {
      setError(err.message || "Failed to save expense");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <form onSubmit={handleSubmit}>
        <Field label="Amount (₹)">
          <Input type="number" min={0.01} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required autoFocus />
        </Field>
        <Field label="Category">
          <Select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} required>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Description">
          <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Lunch at canteen" />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Date">
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
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
        </div>
        <Field label="Notes (optional)">
          <TextArea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>

        {error && <p className="text-sm text-critical-600 mb-3">{error}</p>}
        {success && <p className="text-sm text-brand-600 mb-3">Expense added!</p>}

        <Button type="submit" disabled={saving} className="w-full">
          {saving ? "Saving..." : "Add expense"}
        </Button>
      </form>
    </Card>
  );
}

function AIQuickEntry({ budgetId, categories }: { budgetId: string; categories: { id: string; name: string }[] }) {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<ParsedExpense | null>(null);
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Editable fields shown before confirming
  const [editAmount, setEditAmount] = useState("");
  const [editCategoryId, setEditCategoryId] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDate, setEditDate] = useState("");
  const [editPaymentMethod, setEditPaymentMethod] = useState<PaymentMethod>("Other");

  async function handleParse() {
    if (!text.trim()) return;
    setParsing(true);
    setError(null);
    setParsed(null);
    try {
      const result = await api.parseExpenseText(budgetId, text);
      setParsed(result);
      setEditAmount(String(result.amount));
      const matched = categories.find((c) => c.name.toLowerCase() === result.category.toLowerCase());
      setEditCategoryId(matched?.id || categories[0]?.id || "");
      setEditDescription(result.description);
      setEditDate(result.date);
      setEditPaymentMethod((result.payment_method as PaymentMethod) || "Other");
    } catch (err: any) {
      setError(err.message || "Could not parse that. Try including an amount, e.g. 'spent 120 on lunch'.");
    } finally {
      setParsing(false);
    }
  }

  async function handleConfirm() {
    setSaving(true);
    setError(null);
    try {
      await api.createExpense(budgetId, {
        amount: parseFloat(editAmount),
        category_id: editCategoryId,
        description: editDescription,
        date: editDate,
        payment_method: editPaymentMethod,
        is_ai_entered: true,
      });
      navigate("/expenses");
    } catch (err: any) {
      setError(err.message || "Failed to save expense");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <Field label="Describe your expense">
          <TextArea
            rows={2}
            placeholder="e.g. Spent 60 on auto to college"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </Field>
        <Button onClick={handleParse} disabled={parsing || !text.trim()}>
          {parsing ? "Interpreting..." : "Interpret with AI"}
        </Button>
        {error && <p className="text-sm text-critical-600 mt-3">{error}</p>}
        <p className="text-xs text-slate-400 mt-3">
          Try: "I spent ₹120 on lunch", "Spent 60 on auto to college", "Yesterday I paid 250 for dinner"
        </p>
      </Card>

      {parsed && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display font-semibold text-ink">Review before saving</h3>
            <Badge tone={parsed.source === "ai" ? "brand" : "neutral"}>
              {parsed.source === "ai" ? "AI interpreted" : "Rule-based fallback"}
            </Badge>
          </div>

          <Field label="Amount (₹)">
            <Input type="number" step="0.01" min={0} value={editAmount} onChange={(e) => setEditAmount(e.target.value)} />
          </Field>
          <Field label="Category">
            <Select value={editCategoryId} onChange={(e) => setEditCategoryId(e.target.value)}>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Description">
            <Input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Date">
              <Input type="date" value={editDate} onChange={(e) => setEditDate(e.target.value)} />
            </Field>
            <Field label="Payment method">
              <Select value={editPaymentMethod} onChange={(e) => setEditPaymentMethod(e.target.value as PaymentMethod)}>
                {PAYMENT_METHODS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <p className="text-xs text-slate-400 mb-4">
            Confirming will log{" "}
            <span className="num font-medium text-ink">{formatMoney(parseFloat(editAmount) || 0)}</span> under{" "}
            {categories.find((c) => c.id === editCategoryId)?.name}.
          </p>

          <div className="flex gap-2">
            <Button onClick={handleConfirm} disabled={saving}>
              {saving ? "Saving..." : "Confirm & add"}
            </Button>
            <Button variant="secondary" onClick={() => setParsed(null)}>
              Discard
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
