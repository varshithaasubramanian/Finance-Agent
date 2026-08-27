import React from "react";
import clsx from "clsx";
import { formatMoney, clampPercent, statusColor } from "../utils/format";

// -------------------------------------------------------------------- Card
export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx("card p-5", className)}>{children}</div>;
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h3 className="font-display font-semibold text-ink text-base">{title}</h3>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// ---------------------------------------------------------------- Money
export function Money({
  value,
  symbol = "\u20b9",
  className = "",
  size = "base",
}: {
  value: number;
  symbol?: string;
  className?: string;
  size?: "sm" | "base" | "lg" | "xl";
}) {
  const sizes = { sm: "text-sm", base: "text-base", lg: "text-2xl", xl: "text-4xl" };
  return <span className={clsx("num font-semibold", sizes[size], className)}>{formatMoney(value, symbol)}</span>;
}

// ----------------------------------------------------------- ProgressBar
export function ProgressBar({ percent, size = "md" }: { percent: number; size?: "sm" | "md" }) {
  const clamped = clampPercent(percent);
  const status = statusColor(percent);
  const barColor = status === "critical" ? "bg-critical-500" : status === "caution" ? "bg-caution-500" : "bg-brand-600";
  const height = size === "sm" ? "h-1.5" : "h-2.5";
  return (
    <div className={clsx("w-full bg-ledger rounded-full overflow-hidden", height)}>
      <div
        className={clsx("h-full rounded-full transition-all duration-500", barColor)}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

// ------------------------------------------------------------- RingGauge
export function RingGauge({ percent, size = 56, strokeWidth = 6 }: { percent: number; size?: number; strokeWidth?: number }) {
  const clamped = clampPercent(percent);
  const status = statusColor(percent);
  const color = status === "critical" ? "#DC2626" : status === "caution" ? "#D97706" : "#0F766E";
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={radius} stroke="#E4E7EC" strokeWidth={strokeWidth} fill="none" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        stroke={color}
        strokeWidth={strokeWidth}
        fill="none"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        style={{ transition: "stroke-dashoffset 0.6s ease" }}
      />
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="central"
        transform={`rotate(90 ${size / 2} ${size / 2})`}
        className="num"
        fontSize={size * 0.24}
        fontWeight={700}
        fill="#0F172A"
      >
        {Math.round(clamped)}%
      </text>
    </svg>
  );
}

// --------------------------------------------------------------- Badge
export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "healthy" | "caution" | "critical" | "brand";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-slate-100 text-slate-600",
    healthy: "bg-brand-100 text-brand-700",
    caution: "bg-caution-100 text-caution-600",
    critical: "bg-critical-100 text-critical-600",
    brand: "bg-brand-600 text-white",
  };
  return (
    <span className={clsx("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", tones[tone])}>
      {children}
    </span>
  );
}

// ----------------------------------------------------------------- Alert
export function AlertBanner({ severity, children }: { severity: "INFO" | "WARNING" | "CRITICAL"; children: React.ReactNode }) {
  const styles: Record<string, string> = {
    INFO: "bg-slate-50 border-slate-200 text-slate-700",
    WARNING: "bg-caution-100/60 border-caution-500/30 text-caution-600",
    CRITICAL: "bg-critical-100/60 border-critical-500/30 text-critical-600",
  };
  return (
    <div className={clsx("border rounded-xl px-4 py-3 text-sm flex items-start gap-2", styles[severity])}>
      <span className="font-semibold shrink-0">
        {severity === "CRITICAL" ? "⚠" : severity === "WARNING" ? "!" : "i"}
      </span>
      <span>{children}</span>
    </div>
  );
}

// ----------------------------------------------------------------- Modal
export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-t-2xl sm:rounded-2xl w-full sm:max-w-lg max-h-[90vh] overflow-y-auto p-6 shadow-xl animate-in">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-semibold text-lg text-ink">{title}</h3>
          <button
            onClick={onClose}
            aria-label="Close"
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-500"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Button
export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger" }) {
  const variants: Record<string, string> = {
    primary: "bg-brand-600 hover:bg-brand-700 text-white shadow-sm",
    secondary: "bg-white hover:bg-slate-50 text-ink border border-ledger",
    ghost: "bg-transparent hover:bg-slate-100 text-ink",
    danger: "bg-critical-500 hover:bg-critical-600 text-white",
  };
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

// ------------------------------------------------------------------ Input
export function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block mb-4">
      <span className="block text-sm font-medium text-slate-700 mb-1.5">{label}</span>
      {children}
      {hint && <span className="block text-xs text-slate-400 mt-1">{hint}</span>}
    </label>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        "w-full rounded-xl border border-ledger px-3.5 py-2.5 text-sm text-ink placeholder:text-slate-400 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none transition-colors",
        props.className
      )}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={clsx(
        "w-full rounded-xl border border-ledger px-3.5 py-2.5 text-sm text-ink bg-white focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none transition-colors",
        props.className
      )}
    />
  );
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={clsx(
        "w-full rounded-xl border border-ledger px-3.5 py-2.5 text-sm text-ink placeholder:text-slate-400 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none transition-colors resize-none",
        props.className
      )}
    />
  );
}

// -------------------------------------------------------------- EmptyState
export function EmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return (
    <div className="text-center py-12 px-4">
      <p className="font-display font-semibold text-ink mb-1">{title}</p>
      <p className="text-sm text-slate-500 mb-4 max-w-sm mx-auto">{description}</p>
      {action}
    </div>
  );
}

// ----------------------------------------------------------------- Spinner
export function Spinner({ className = "" }: { className?: string }) {
  return (
    <div className={clsx("animate-spin rounded-full border-2 border-slate-200 border-t-brand-600", className)} style={{ width: 20, height: 20 }} />
  );
}
