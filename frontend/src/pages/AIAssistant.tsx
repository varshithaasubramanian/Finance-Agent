import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useBudget } from "../hooks/useBudget";
import * as api from "../services/api";
import type { AffordabilityResult, AssistantMessage } from "../types";
import { Card, CardHeader, Button, Input, Select, Badge, Spinner, EmptyState } from "../components/ui";
import { formatMoney } from "../utils/format";

const SUGGESTIONS = [
  "How much money do I have left?",
  "How much can I spend today?",
  "Am I overspending on food?",
  "Which category am I spending the most on?",
  "Will I exceed my budget?",
  "Give me a summary of this month.",
];

export default function AIAssistant() {
  const { budget, needsSetup } = useBudget();
  const [aiEnabled, setAiEnabled] = useState<boolean | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!budget) return;
    api.getAssistantStatus(budget.id).then((s) => setAiEnabled(s.ai_enabled));
    setMessages([
      {
        role: "assistant",
        text: "Hi! I'm your financial assistant. Ask me about your budget, spending, or whether you can afford something.",
      },
    ]);
  }, [budget]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!budget || !text.trim()) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    setSending(true);
    try {
      const res = await api.askAssistant(budget.id, text);
      setMessages((prev) => [...prev, { role: "assistant", text: res.reply, source: res.source }]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Sorry, something went wrong: ${err.message || "unknown error"}` },
      ]);
    } finally {
      setSending(false);
    }
  }

  if (needsSetup || !budget) {
    return (
      <EmptyState
        title="No budget yet"
        description="Set up a budget so the assistant has data to work with."
        action={
          <Link to="/budget-setup">
            <Button>Set up budget</Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display font-bold text-2xl text-ink">AI Assistant</h1>
            <p className="text-sm text-slate-500 mt-1">Numbers always come from your real budget data — never guessed.</p>
          </div>
          {aiEnabled !== null && (
            <Badge tone={aiEnabled ? "brand" : "neutral"}>{aiEnabled ? "AI mode" : "Rule-based mode"}</Badge>
          )}
        </div>

        <Card className="flex flex-col h-[65vh]">
          <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin">
            {messages.map((m, i) => (
              <ChatBubble key={i} message={m} />
            ))}
            {sending && (
              <div className="flex items-center gap-2 text-slate-400 text-sm px-1">
                <Spinner className="!w-4 !h-4" />
                Thinking...
              </div>
            )}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage(input);
            }}
            className="flex gap-2 mt-4 pt-4 border-t border-ledger"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your budget..."
              className="flex-1"
            />
            <Button type="submit" disabled={sending || !input.trim()}>
              Send
            </Button>
          </form>
        </Card>

        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => sendMessage(s)}
              className="text-xs px-3 py-1.5 rounded-full border border-ledger text-slate-600 hover:bg-slate-50 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div>
        <AffordabilityCard budgetId={budget.id} categories={budget.categories} currencySymbol={budget.currency_symbol} />
      </div>
    </div>
  );
}

function ChatBubble({ message }: { message: AssistantMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
          isUser ? "bg-brand-600 text-white rounded-br-sm" : "bg-slate-100 text-ink rounded-bl-sm"
        }`}
      >
        {message.text}
        {!isUser && message.source && (
          <div className="mt-1">
            <span className={`text-[10px] ${isUser ? "text-white/70" : "text-slate-400"}`}>
              {message.source === "ai" ? "AI-narrated" : "Rule-based"}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function AffordabilityCard({
  budgetId,
  categories,
  currencySymbol,
}: {
  budgetId: string;
  categories: { id: string; name: string }[];
  currencySymbol: string;
}) {
  const [amount, setAmount] = useState("300");
  const [categoryId, setCategoryId] = useState("");
  const [description, setDescription] = useState("");
  const [result, setResult] = useState<AffordabilityResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleCheck() {
    setLoading(true);
    try {
      const res = await api.checkAffordability(budgetId, parseFloat(amount), categoryId || undefined, description);
      setResult(res);
    } finally {
      setLoading(false);
    }
  }

  const verdictTone = result?.verdict === "Yes" ? "healthy" : result?.verdict === "No" ? "critical" : "caution";

  return (
    <Card>
      <CardHeader title="Can I afford this?" subtitle="Deterministic check against your real budget" />
      <div className="space-y-3">
        <Input type="number" min={0} step="0.01" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <Select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">No specific category</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Input placeholder="What is it for? (optional)" value={description} onChange={(e) => setDescription(e.target.value)} />
        <Button onClick={handleCheck} disabled={loading || !amount} className="w-full">
          {loading ? "Checking..." : "Check affordability"}
        </Button>
      </div>

      {result && (
        <div className="mt-5 pt-4 border-t border-ledger">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-600">Verdict</span>
            <Badge tone={verdictTone}>{result.verdict}</Badge>
          </div>
          <p className="text-sm text-slate-600 mb-3">{result.explanation}</p>
          <dl className="text-xs text-slate-500 space-y-1">
            <div className="flex justify-between">
              <dt>Remaining total after</dt>
              <dd className="num">{formatMoney(result.remaining_total_after, currencySymbol)}</dd>
            </div>
            {result.category_name && (
              <div className="flex justify-between">
                <dt>{result.category_name} remaining after</dt>
                <dd className="num">{formatMoney(result.category_remaining_after || 0, currencySymbol)}</dd>
              </div>
            )}
            <div className="flex justify-between">
              <dt>Recommended spending limit</dt>
              <dd className="num">{formatMoney(result.recommended_spending_limit, currencySymbol)}</dd>
            </div>
          </dl>
        </div>
      )}
    </Card>
  );
}
