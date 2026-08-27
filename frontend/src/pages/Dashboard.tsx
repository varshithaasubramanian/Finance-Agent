import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { useBudget } from "../hooks/useBudget";
import * as api from "../services/api";
import type { Alert, BudgetSummary, Forecast, SpendingTrendPoint } from "../types";
import { Card, CardHeader, Money, ProgressBar, RingGauge, Badge, AlertBanner, Button, Spinner, EmptyState } from "../components/ui";
import { CategoryIcon } from "../components/CategoryIcon";
import { formatShortDate, periodLabel, statusColor } from "../utils/format";

export default function Dashboard() {
  const { budget, loading: budgetLoading, needsSetup } = useBudget();
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [trends, setTrends] = useState<SpendingTrendPoint[]>([]);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!budget) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      api.getSummary(budget.id),
      api.getAlerts(budget.id),
      api.getTrends(budget.id),
      api.getForecast(budget.id),
    ])
      .then(([s, a, t, f]) => {
        if (cancelled) return;
        setSummary(s);
        setAlerts(a);
        setTrends(t);
        setForecast(f);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [budget]);

  if (budgetLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner />
      </div>
    );
  }

  if (needsSetup || !budget) {
    return (
      <EmptyState
        title="No budget set up for this month yet"
        description="Create a monthly budget and split it into categories to start tracking your spending."
        action={
          <Link to="/budget-setup">
            <Button>Set up your budget</Button>
          </Link>
        }
      />
    );
  }

  if (loading || !summary) {
    return (
      <div className="flex justify-center py-24">
        <Spinner />
      </div>
    );
  }

  const symbol = summary.currency_symbol;
  const pieData = summary.categories
    .filter((c) => c.spent > 0)
    .map((c) => ({ name: c.name, value: c.spent, color: c.color }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">{periodLabel(summary.period)}</p>
          <h1 className="font-display font-bold text-2xl text-ink">Dashboard</h1>
        </div>
        <Link to="/add-expense">
          <Button>+ Add expense</Button>
        </Link>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard label="Total budget" value={summary.total_budget} symbol={symbol} />
        <SummaryCard label="Spent" value={summary.total_spent} symbol={symbol} tone="spent" />
        <SummaryCard
          label="Remaining"
          value={summary.total_remaining}
          symbol={symbol}
          tone={summary.total_remaining < 0 ? "critical" : "healthy"}
        />
        <SummaryCard label="Safe daily spend" value={summary.recommended_safe_daily_spending} symbol={symbol} tone="brand" />
      </div>

      {/* Overall progress */}
      <Card>
        <div className="flex items-center gap-6">
          <RingGauge percent={summary.percent_used} size={72} strokeWidth={7} />
          <div className="flex-1">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-slate-500">
                {summary.days_elapsed} of {summary.total_days} days elapsed &middot; {summary.days_remaining} day(s) left
              </span>
              <span className="text-sm num text-slate-500">{summary.percent_used}% used</span>
            </div>
            <ProgressBar percent={summary.percent_used} />
            <div className="flex justify-between text-xs text-slate-400 mt-1.5">
              <span>
                Avg <Money value={summary.daily_average_spending} symbol={symbol} size="sm" />/day
              </span>
              <span>
                Projected <Money value={summary.projected_monthly_spending} symbol={symbol} size="sm" />
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Category breakdown */}
      <Card>
        <CardHeader title="Categories" subtitle="Spend vs allocation this period" />
        <div className="grid sm:grid-cols-2 gap-4">
          {summary.categories.map((c) => (
            <div key={c.category_id} className="hairline pb-3 last:border-0">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-white shrink-0"
                    style={{ backgroundColor: c.color }}
                  >
                    <CategoryIcon icon={c.icon} size={14} />
                  </span>
                  <span className="font-medium text-sm text-ink">{c.name}</span>
                </div>
                <Badge tone={statusColor(c.percent_used) === "critical" ? "critical" : statusColor(c.percent_used) === "caution" ? "caution" : "healthy"}>
                  {c.percent_used}%
                </Badge>
              </div>
              <ProgressBar percent={c.percent_used} size="sm" />
              <div className="flex justify-between text-xs num text-slate-500 mt-1">
                <span>
                  {symbol}
                  {c.spent.toLocaleString("en-IN")} / {symbol}
                  {c.allocation.toLocaleString("en-IN")}
                </span>
                <span>{symbol}{c.remaining.toLocaleString("en-IN")} left</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Spending by category" />
          {pieData.length === 0 ? (
            <p className="text-sm text-slate-400 py-10 text-center">No expenses recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => `${symbol}${v.toLocaleString("en-IN")}`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <CardHeader title="Spending over time" subtitle="Cumulative spend this period" />
          {trends.length === 0 ? (
            <p className="text-sm text-slate-400 py-10 text-center">No expenses recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trends.map((t) => ({ ...t, label: formatShortDate(t.date) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 11 }} width={40} />
                <Tooltip formatter={(v: number) => `${symbol}${v.toLocaleString("en-IN")}`} />
                <Line type="monotone" dataKey="cumulative" stroke="#0F766E" strokeWidth={2} dot={false} name="Cumulative" />
                <Line type="monotone" dataKey="amount" stroke="#94A3B8" strokeWidth={1.5} dot={false} name="Daily" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <CardHeader title="Budget vs actual" subtitle="By category" />
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={summary.categories}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} width={40} />
              <Tooltip formatter={(v: number) => `${symbol}${v.toLocaleString("en-IN")}`} />
              <Legend />
              <Bar dataKey="allocation" fill="#CBD5E1" name="Budget" radius={[4, 4, 0, 0]} />
              <Bar dataKey="spent" fill="#0F766E" name="Spent" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <CardHeader title="Projected vs budget" subtitle={forecast ? `Method: ${forecast.method.replace(/_/g, " ")}` : undefined} />
          {forecast && (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={[
                    { name: "Total", Budget: summary.total_budget, Projected: forecast.projected_monthly_spending },
                  ]}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={50} />
                  <Tooltip formatter={(v: number) => `${symbol}${v.toLocaleString("en-IN")}`} />
                  <Legend />
                  <Bar dataKey="Budget" fill="#CBD5E1" radius={[0, 4, 4, 0]} />
                  <Bar
                    dataKey="Projected"
                    fill={forecast.projected_surplus_deficit < 0 ? "#DC2626" : "#0F766E"}
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
              <p className="text-xs text-slate-500 mt-2">{forecast.explanation}</p>
            </>
          )}
        </Card>
      </div>

      {/* AI Insights */}
      <Card>
        <CardHeader
          title="Insights & alerts"
          subtitle="Generated from your live budget data"
          action={
            <Link to="/assistant" className="text-sm text-brand-600 font-medium hover:underline">
              Ask the assistant →
            </Link>
          }
        />
        {alerts.length === 0 ? (
          <p className="text-sm text-slate-500">
            No alerts right now — your spending is tracking comfortably within budget. 🎉
          </p>
        ) : (
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <AlertBanner key={i} severity={a.severity}>
                {a.message}
              </AlertBanner>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  symbol,
  tone = "default",
}: {
  label: string;
  value: number;
  symbol: string;
  tone?: "default" | "spent" | "healthy" | "critical" | "brand";
}) {
  const toneClass =
    tone === "critical" ? "text-critical-600" : tone === "healthy" ? "text-brand-700" : tone === "brand" ? "text-brand-600" : "text-ink";
  return (
    <Card className="p-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <Money value={value} symbol={symbol} size="lg" className={toneClass} />
    </Card>
  );
}
