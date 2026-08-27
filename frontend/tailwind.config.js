/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Sora", "ui-sans-serif", "system-ui"],
        body: ["Inter", "ui-sans-serif", "system-ui"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular"],
      },
      colors: {
        ink: "#0F172A",
        paper: "#F7F8FA",
        ledger: "#E4E7EC",
        brand: {
          50: "#ECFDF7",
          100: "#D1FAE9",
          400: "#2DD4BF",
          500: "#0F9488",
          600: "#0F766E",
          700: "#0B5C56",
          900: "#093F3B",
        },
        caution: {
          100: "#FEF3C7",
          500: "#D97706",
          600: "#B45309",
        },
        critical: {
          100: "#FEE2E2",
          500: "#DC2626",
          600: "#B91C1C",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 12px rgba(15, 23, 42, 0.04)",
      },
    },
  },
  plugins: [],
};
