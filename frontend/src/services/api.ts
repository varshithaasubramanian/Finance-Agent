import axios, { AxiosError } from "axios";
import type {
  AffordabilityResult,
  Alert,
  AssistantMessage,
  AuthResponse,
  Budget,
  BudgetSummary,
  Category,
  Expense,
  FinancialGoal,
  Forecast,
  ParsedExpense,
  RecurringExpense,
  SpendingTrendPoint,
  TravelAnalytics,
} from "../types";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "finch_token";

export const http = axios.create({ baseURL, headers: { "Content-Type": "application/json" } });

// Attach the stored JWT (if any) to every outgoing request.
http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Let the app react globally to an expired/invalid session (401) by
// clearing the stored token; useAuth listens for this event.
http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event("finch:unauthorized"));
    }
    return Promise.reject(err);
  }
);

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

function unwrap<T>(promise: Promise<{ data: T }>): Promise<T> {
  return promise
    .then((res) => res.data)
    .catch((err: AxiosError<any>) => {
      const detail = err.response?.data?.detail || err.message || "Something went wrong";
      throw new ApiError(detail, err.response?.status);
    });
}

// --------------------------------------------------------------------- auth
export const signup = (name: string, email: string, password: string) =>
  unwrap<AuthResponse>(http.post("/api/auth/signup", { name, email, password }));
export const login = (email: string, password: string) =>
  unwrap<AuthResponse>(http.post("/api/auth/login", { email, password }));
export const getMe = () => unwrap<AuthResponse["user"]>(http.get("/api/auth/me"));

// ------------------------------------------------------------------ budgets
export const getCurrentBudget = () => unwrap<Budget>(http.get("/api/budgets/current"));
export const listBudgets = () => unwrap<Budget[]>(http.get("/api/budgets"));
export const createBudget = (payload: {
  period: string;
  total_amount: number;
  allow_over_allocation?: boolean;
  categories?: Partial<Category>[];
}) => unwrap<Budget>(http.post("/api/budgets", payload));
export const updateBudget = (budgetId: string, payload: { total_amount?: number; allow_over_allocation?: boolean }) =>
  unwrap<Budget>(http.patch(`/api/budgets/${budgetId}`, payload));

// --------------------------------------------------------------- categories
export const listCategories = (budgetId: string) => unwrap<Category[]>(http.get(`/api/budgets/${budgetId}/categories`));
export const createCategory = (budgetId: string, payload: Partial<Category> & { name: string; allocation: number }) =>
  unwrap<Category>(http.post(`/api/budgets/${budgetId}/categories`, payload));
export const updateCategory = (budgetId: string, categoryId: string, payload: Partial<Category>) =>
  unwrap<Category>(http.patch(`/api/budgets/${budgetId}/categories/${categoryId}`, payload));
export const deleteCategory = (budgetId: string, categoryId: string) =>
  unwrap<void>(http.delete(`/api/budgets/${budgetId}/categories/${categoryId}`));

// ----------------------------------------------------------------- expenses
export interface ExpenseFilters {
  category_id?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  payment_method?: string;
  sort_by?: "date" | "amount" | "category";
  sort_dir?: "asc" | "desc";
}
export const listExpenses = (budgetId: string, filters: ExpenseFilters = {}) =>
  unwrap<Expense[]>(http.get(`/api/budgets/${budgetId}/expenses`, { params: filters }));
export const createExpense = (
  budgetId: string,
  payload: {
    amount: number;
    category_id: string;
    description?: string;
    date: string;
    payment_method?: string;
    notes?: string;
    is_ai_entered?: boolean;
  }
) => unwrap<Expense>(http.post(`/api/budgets/${budgetId}/expenses`, payload));
export const updateExpense = (budgetId: string, expenseId: string, payload: Partial<Expense>) =>
  unwrap<Expense>(http.patch(`/api/budgets/${budgetId}/expenses/${expenseId}`, payload));
export const deleteExpense = (budgetId: string, expenseId: string) =>
  unwrap<void>(http.delete(`/api/budgets/${budgetId}/expenses/${expenseId}`));

// --------------------------------------------------------------- analytics
export const getSummary = (budgetId: string) => unwrap<BudgetSummary>(http.get(`/api/budgets/${budgetId}/summary`));
export const getTravelAnalytics = (budgetId: string) =>
  unwrap<TravelAnalytics | null>(http.get(`/api/budgets/${budgetId}/travel`));
export const getTrends = (budgetId: string) => unwrap<SpendingTrendPoint[]>(http.get(`/api/budgets/${budgetId}/trends`));
export const getForecast = (budgetId: string) => unwrap<Forecast>(http.get(`/api/budgets/${budgetId}/forecast`));
export const getAlerts = (budgetId: string) => unwrap<Alert[]>(http.get(`/api/budgets/${budgetId}/alerts`));
export const checkAffordability = (budgetId: string, amount: number, category_id?: string, description?: string) =>
  unwrap<AffordabilityResult>(http.post(`/api/budgets/${budgetId}/affordability`, { amount, category_id, description }));
export const parseExpenseText = (budgetId: string, text: string) =>
  unwrap<ParsedExpense>(http.post(`/api/budgets/${budgetId}/parse-expense`, { text }));

// ----------------------------------------------------------------- assistant
export const askAssistant = (budgetId: string, message: string) =>
  unwrap<{ reply: string; source: "ai" | "fallback" }>(http.post(`/api/budgets/${budgetId}/assistant/ask`, { message }));
export const getAssistantStatus = (budgetId: string) =>
  unwrap<{ ai_enabled: boolean; model: string | null }>(http.get(`/api/budgets/${budgetId}/assistant/status`));

// -------------------------------------------------------------- recurring
export const listRecurring = (budgetId: string) =>
  unwrap<RecurringExpense[]>(http.get(`/api/budgets/${budgetId}/recurring`));
export const createRecurring = (
  budgetId: string,
  payload: { category_id: string; name: string; amount: number; frequency: string; next_due_date: string }
) => unwrap<RecurringExpense>(http.post(`/api/budgets/${budgetId}/recurring`, payload));
export const deleteRecurring = (budgetId: string, recurringId: string) =>
  unwrap<void>(http.delete(`/api/budgets/${budgetId}/recurring/${recurringId}`));

// ------------------------------------------------------------------- goals
export const listGoals = () => unwrap<FinancialGoal[]>(http.get("/api/goals"));
export const createGoal = (payload: { name: string; target_amount: number; current_amount?: number; deadline: string }) =>
  unwrap<FinancialGoal>(http.post("/api/goals", payload));
export const updateGoal = (goalId: string, payload: Partial<FinancialGoal>) =>
  unwrap<FinancialGoal>(http.patch(`/api/goals/${goalId}`, payload));
export const deleteGoal = (goalId: string) => unwrap<void>(http.delete(`/api/goals/${goalId}`));

export type { AssistantMessage };
