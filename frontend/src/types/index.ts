export type PaymentMethod = "Cash" | "UPI" | "Debit Card" | "Credit Card" | "Bank Transfer" | "Other";
export type RecurrenceFrequency = "Daily" | "Weekly" | "Monthly";
export type Severity = "INFO" | "WARNING" | "CRITICAL";

export interface Category {
  id: string;
  budget_id: string;
  name: string;
  allocation: number;
  spending_limit: number | null;
  color: string;
  icon: string;
  is_travel: boolean;
  fixed_amount: number;
  estimated_daily_amount: number | null;
  spent: number;
  remaining: number;
  percent_used: number;
  daily_allowance: number;
}

export interface Budget {
  id: string;
  period: string;
  total_amount: number;
  allow_over_allocation: boolean;
  currency_symbol: string;
  categories: Category[];
}

export interface Expense {
  id: string;
  budget_id: string;
  category_id: string;
  category_name: string;
  amount: number;
  description: string;
  date: string;
  payment_method: PaymentMethod;
  notes: string;
  is_ai_entered: boolean;
  created_at: string;
}

export interface CategoryAnalytics {
  category_id: string;
  name: string;
  allocation: number;
  spent: number;
  remaining: number;
  percent_used: number;
  daily_average: number;
  projected_spending: number;
  projected_surplus_deficit: number;
  color: string;
  icon: string;
}

export interface BudgetSummary {
  period: string;
  total_budget: number;
  total_spent: number;
  total_remaining: number;
  percent_used: number;
  days_elapsed: number;
  days_remaining: number;
  total_days: number;
  daily_average_spending: number;
  recommended_safe_daily_spending: number;
  projected_monthly_spending: number;
  projected_surplus_deficit: number;
  categories: CategoryAnalytics[];
  currency_symbol: string;
}

export interface TravelAnalytics {
  travel_budget: number;
  travel_spent: number;
  travel_remaining: number;
  fixed_travel_expenses: number;
  variable_travel_budget: number;
  variable_travel_remaining: number;
  recommended_daily_spending: number;
  estimated_daily_travel: number | null;
  expected_cost_remaining_days: number | null;
  budget_sufficient: boolean | null;
  expected_exhaustion_date: string | null;
  required_daily_reduction: number | null;
}

export interface SpendingTrendPoint {
  date: string;
  amount: number;
  cumulative: number;
}

export interface CategoryForecast {
  category_id: string;
  name: string;
  allocation: number;
  projected_spending: number;
  projected_surplus_deficit: number;
  expected_exhaustion_date: string | null;
}

export interface Forecast {
  method: string;
  explanation: string;
  projected_monthly_spending: number;
  projected_surplus_deficit: number;
  category_forecasts: CategoryForecast[];
  expected_exhaustion_date: string | null;
}

export interface Alert {
  severity: Severity;
  category: string;
  message: string;
  metric?: Record<string, number> | null;
}

export interface AffordabilityResult {
  verdict: "Yes" | "No" | "Caution";
  amount: number;
  remaining_total_after: number;
  category_name: string | null;
  category_remaining_before: number | null;
  category_remaining_after: number | null;
  recommended_spending_limit: number;
  explanation: string;
}

export interface ParsedExpense {
  amount: number;
  category: string;
  description: string;
  date: string;
  payment_method: PaymentMethod | null;
  confidence: number;
  source: "ai" | "fallback";
}

export interface AssistantMessage {
  role: "user" | "assistant";
  text: string;
  source?: "ai" | "fallback";
}

export interface RecurringExpense {
  id: string;
  budget_id: string;
  category_id: string;
  category_name: string;
  name: string;
  amount: number;
  frequency: RecurrenceFrequency;
  next_due_date: string;
  active: boolean;
}

export interface User {
  id: string;
  name: string;
  email: string;
  currency: string;
  currency_symbol: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface FinancialGoal {
  id: string;
  name: string;
  target_amount: number;
  current_amount: number;
  deadline: string;
  remaining_amount: number;
  days_left: number;
  required_daily_saving: number;
  required_weekly_saving: number;
}
