import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { BudgetProvider } from "./hooks/useBudget";
import { Spinner } from "./components/ui";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import BudgetSetup from "./pages/BudgetSetup";
import Expenses from "./pages/Expenses";
import AddExpense from "./pages/AddExpense";
import Analytics from "./pages/Analytics";
import AIAssistant from "./pages/AIAssistant";
import Categories from "./pages/Categories";
import Settings from "./pages/Settings";

function AuthenticatedApp() {
  return (
    <BudgetProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/budget-setup" element={<BudgetSetup />} />
          <Route path="/expenses" element={<Expenses />} />
          <Route path="/add-expense" element={<AddExpense />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/assistant" element={<AIAssistant />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BudgetProvider>
  );
}

function Gate() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return user ? <AuthenticatedApp /> : <Login />;
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  );
}
