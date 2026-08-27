import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useBudget } from "../hooks/useBudget";
import * as api from "../services/api";
import type { BudgetSummary, Forecast, SpendingTrendPoint, TravelAnalytics } from "../types";
import { Card, CardHeader, Money, ProgressBar, Badge, Button, Spinner, EmptyState } from "../components/ui";
import { formatShortDate, statusColor } from "../utils/format";

export default function Analytics() {
  const { budget, needsSetup } = useBudget();
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [travel, setTravel] = useState<TravelAnalytics | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [trends, setTrends] = useState<SpendingTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!budget) return;
    setLoading(true);
    Promise.all([
      api.getSummary(budget.id),
      api.getTravelAnalytics(budget.id),
      api.getForecast(budget.id),
      api.getTrends(budget.id),
    ])
      .then(([s, t, f, tr]) => {
        setSummary(s);
        setTravel(t);
        setForecast(f);
        setTrends(tr);
      })
      .finally(() => setLoading(false));
  }, [budget]);

  if (needsSetup || !budget) {
    return (
      <EmptyState
        title="No budget yet"
        description="Set up a budget to see analytics."
        action={
          <Link to="/budget-setup">
            <Button>Set up budget</Button>
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display font-bold text-2xl text-ink">Analytics</h1>
        <p className="text-sm text-slate-500 mt-1">Deep dive into your spending patterns and projections.</p>
      </div>

      {/* Category analytics table */}
      <Card className="p-0 overflow-hidden">
        <div className="p-5 pb-0">
          <CardHeader title="Category analytics" subtitle="Daily average, projection and surplus/deficit per category" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-400 border-y border-ledger">
                <th className="px-5 py-2 font-medium">Category</th>
                <th className="px-3 py-2 font-medium text-right">Allocation</th>
                <th className="px-3 py-2 font-medium text-right">Spent</th>
                <th className="px-3 py-2 font-medium text-right">% Used</th>
                <th className="px-3 py-2 font-medium text-right">Daily avg</th>
                <th className="px-3 py-2 font-medium text-right">Projected</th>
                <th className="px-5 py-2 font-medium text-right">Surplus/Deficit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ledger">
              {summary.categories.map((c) => (
                <tr key={c.category_id}>
                  <td className="px-5 py-2.5 font-medium text-ink">{c.name}</td>
                  <td className="px-3 py-2.5 text-right num">{symbol}{c.allocation.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-2.5 text-right num">{symbol}{c.spent.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-2.5 text-right">
                    <Badge tone={statusColor(c.percent_used) === "critical" ? "critical" : statusColor(c.percent_used) === "caution" ? "caution" : "healthy"}>
                      {c.percent_used}%
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5 text-right num">{symbol}{c.daily_average.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-2.5 text-right num">{symbol}{c.projected_spending.toLocaleString("en-IN")}</td>
                  <td className={`px-5 py-2.5 text-right num font-medium ${c.projected_surplus_deficit < 0 ? "text-critical-600" : "text-brand-700"}`}>
                    {c.projected_surplus_deficit >= 0 ? "+" : ""}
                    {symbol}{c.projected_surplus_deficit.toLocaleString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Daily spending chart */}
      <Card>
        <CardHeader title="Daily spending" subtitle="Amount spent per day this period" />
        {trends.length === 0 ? (
          <p className="text-sm text-slate-400 py-10 text-center">No expenses recorded yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={trends.map((t) => ({ ...t, label: formatShortDate(t.date) }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E4E7EC" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11 }} width={40} />
              <Tooltip formatter={(v: number) => `${symbol}${v.toLocaleString("en-IN")}`} />
              <Bar dataKey="amount" fill="#0F9488" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* Travel budget */}
      {travel && (
        <Card>
          <CardHeader title="Travel budget" subtitle="Fixed vs variable travel spending" />
          <div className="grid sm:grid-cols-2 gap-4 mb-4">
            <Stat label="Travel budget" value={travel.travel_budget} symbol={symbol} />
            <Stat label="Travel spent" value={travel.travel_spent} symbol={symbol} />
            <Stat label="Fixed travel expenses" value={travel.fixed_travel_expenses} symbol={symbol} />
            <Stat label="Variable travel remaining" value={travel.variable_travel_remaining} symbol={symbol} />
          </div>
          <div className="hairline pb-3 mb-3">
            <p className="text-sm text-slate-600">
              Recommended variable travel spending: <Money value={travel.recommended_daily_spending} symbol={symbol} size="sm" />/day
            </p>
          </div>
          {travel.estimated_daily_travel !== null && (
            <div className="text-sm text-slate-600 space-y-1">
              <p>
                At your estimated <Money value={travel.estimated_daily_travel} symbol={symbol} size="sm" />/day, expected cost for
                remaining days is <Money value={travel.expected_cost_remaining_days || 0} symbol={symbol} size="sm" />.
              </p>
              <p>
                Budget sufficiency:{" "}
                <Badge tone={travel.budget_sufficient ? "healthy" : "critical"}>
                  {travel.budget_sufficient ? "Sufficient" : "Insufficient"}
                </Badge>
              </p>
              {travel.expected_exhaustion_date && (
                <p>Expected exhaustion date: <span className="num">{travel.expected_exhaustion_date}</span></p>
              )}
              {travel.required_daily_reduction != null && travel.required_daily_reduction > 0 && (
                <p className="text-caution-600">
                  Reduce daily travel spending by <Money value={travel.required_daily_reduction} symbol={symbol} size="sm" />/day to stay within budget.
                </p>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Forecast */}
      {forecast && (
        <Card>
          <CardHeader title="Forecast" subtitle={`Method: ${forecast.method.replace(/_/g, " ")}`} />
          <p className="text-sm text-slate-600 mb-4">{forecast.explanation}</p>
          <div className="grid sm:grid-cols-2 gap-4 mb-4">
            <Stat label="Projected monthly spending" value={forecast.projected_monthly_spending} symbol={symbol} />
            <Stat
              label="Projected surplus/deficit"
              value={forecast.projected_surplus_deficit}
              symbol={symbol}
              tone={forecast.projected_surplus_deficit < 0 ? "critical" : "healthy"}
            />
          </div>
          {forecast.expected_exhaustion_date && (
            <p className="text-sm text-caution-600 mb-3">
              At this rate, your budget may be exhausted around <span className="num">{forecast.expected_exhaustion_date}</span>.
            </p>
          )}
          <div className="space-y-2">
            {forecast.category_forecasts.map((cf) => (
              <div key={cf.category_id} className="hairline py-2 flex items-center justify-between text-sm">
                <span className="font-medium text-ink">{cf.name}</span>
                <span className="text-slate-500">
                  Projected <span className="num">{symbol}{cf.projected_spending.toLocaleString("en-IN")}</span> of{" "}
                  <span className="num">{symbol}{cf.allocation.toLocaleString("en-IN")}</span>
                </span>
                <span className={`num font-medium ${cf.projected_surplus_deficit < 0 ? "text-critical-600" : "text-brand-700"}`}>
                  {cf.projected_surplus_deficit >= 0 ? "+" : ""}
                  {symbol}{cf.projected_surplus_deficit.toLocaleString("en-IN")}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value, symbol, tone = "default" }: { label: string; value: number; symbol: string; tone?: "default" | "healthy" | "critical" }) {
  const cls = tone === "critical" ? "text-critical-600" : tone === "healthy" ? "text-brand-700" : "text-ink";
  return (
    <div>
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <Money value={value} symbol={symbol} size="lg" className={cls} />
    </div>
  );
}
