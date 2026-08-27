import React from "react";
import { NavLink } from "react-router-dom";
import clsx from "clsx";
import {
  LayoutDashboard,
  Wallet,
  ListPlus,
  Receipt,
  BarChart3,
  Sparkles,
  Tags,
  Settings as SettingsIcon,
  LogOut,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/budget-setup", label: "Budget Setup", icon: Wallet },
  { to: "/expenses", label: "Expenses", icon: Receipt },
  { to: "/add-expense", label: "Add Expense", icon: ListPlus },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/assistant", label: "AI Assistant", icon: Sparkles },
  { to: "/categories", label: "Categories", icon: Tags },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

// Primary items shown in the mobile bottom bar (limited to 5 for space)
const MOBILE_ITEMS = [
  { to: "/", label: "Home", icon: LayoutDashboard, end: true },
  { to: "/expenses", label: "Expenses", icon: Receipt },
  { to: "/add-expense", label: "Add", icon: ListPlus },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/assistant", label: "Assistant", icon: Sparkles },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:w-60 md:flex-col border-r border-ledger bg-white sticky top-0 h-screen px-4 py-6">
        <Brand />
        <nav className="mt-8 flex-1 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavItem key={item.to} {...item} />
          ))}
        </nav>
        <UserFooter />
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <header className="md:hidden sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-ledger px-4 py-3 flex items-center justify-between">
          <Brand compact />
          <MobileLogout />
        </header>

        <main className="flex-1 px-4 py-6 md:px-8 md:py-8 pb-24 md:pb-8 max-w-6xl w-full mx-auto">{children}</main>

        {/* Mobile bottom nav */}
        <nav className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-white border-t border-ledger flex justify-around py-2 px-1">
          {MOBILE_ITEMS.map((item) => (
            <MobileNavItem key={item.to} {...item} />
          ))}
        </nav>
      </div>
    </div>
  );
}

function MobileLogout() {
  const { logout } = useAuth();
  return (
    <button onClick={logout} className="text-slate-400 hover:text-critical-600 p-1.5" aria-label="Log out">
      <LogOut size={18} />
    </button>
  );
}

function UserFooter() {
  const { user, logout } = useAuth();
  return (
    <div className="pt-4 border-t border-ledger px-3">
      <p className="text-sm font-medium text-ink truncate">{user?.name}</p>
      <p className="text-xs text-slate-400 truncate mb-2">{user?.email}</p>
      <button
        onClick={logout}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-critical-600 transition-colors"
      >
        <LogOut size={13} /> Log out
      </button>
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2 px-2">
      <div className="w-8 h-8 rounded-lg bg-brand-600 text-white flex items-center justify-center font-display font-bold text-sm shrink-0">
        ₹
      </div>
      <div>
        <div className="font-display font-bold text-ink leading-none">Finch</div>
        {!compact && <div className="text-[11px] text-slate-400 mt-0.5">Budget Agent</div>}
      </div>
    </div>
  );
}

function NavItem({ to, label, icon: Icon, end }: { to: string; label: string; icon: any; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        clsx(
          "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors",
          isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50 hover:text-ink"
        )
      }
    >
      <Icon size={18} strokeWidth={2} />
      {label}
    </NavLink>
  );
}

function MobileNavItem({ to, label, icon: Icon, end }: { to: string; label: string; icon: any; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        clsx(
          "flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg text-[10px] font-medium transition-colors min-w-[56px]",
          isActive ? "text-brand-700" : "text-slate-400"
        )
      }
    >
      <Icon size={20} strokeWidth={2} />
      {label}
    </NavLink>
  );
}
