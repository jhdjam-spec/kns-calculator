import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // Brand: deep teal-blue — гидравлика, не банковский индиго
        brand: {
          50: "#EEF6F7",
          100: "#D5E8EC",
          200: "#ADD1D9",
          300: "#7AB2BF",
          400: "#4A8E9F",
          500: "#2C6F82",
          600: "#1F576B",
          700: "#184555",
          800: "#133846",
          900: "#0E2A35",
          950: "#081A22",
        },
        // Accent: industrial brass — KPI и активные состояния
        accent: {
          400: "#D4B26B",
          500: "#C9A24A",
          600: "#A8842F",
        },
        // Ink: тёплый графит вместо холодного slate
        ink: {
          50: "#FAFAF9",
          100: "#F4F4F2",
          200: "#E8E8E5",
          300: "#D1D1CC",
          400: "#A6A6A0",
          500: "#757571",
          600: "#54544F",
          700: "#383834",
          800: "#1F1F1C",
          900: "#121210",
          950: "#0B0D0E",
        },
        // Семантика сегментов: новые тона
        budget: "#54544F", // ink-600 (графит)
        mid: "#184555", // brand-700 (рекомендуемый)
        premium: "#0E2A35", // brand-900 (премиум)
        success: "#2D8C5F",
        warning: "#D4892A",
        error: "#C7423B",
      },
      borderRadius: {
        card: "14px",
        block: "20px",
        hero: "28px",
      },
      boxShadow: {
        "premium-sm": "0 1px 2px rgba(11,13,14,0.04), 0 1px 3px rgba(11,13,14,0.06)",
        "premium-md": "0 2px 4px rgba(11,13,14,0.04), 0 4px 12px rgba(11,13,14,0.08)",
        "premium-lg": "0 4px 8px rgba(11,13,14,0.04), 0 12px 32px rgba(11,13,14,0.10)",
        "premium-xl": "0 8px 16px rgba(11,13,14,0.05), 0 24px 56px rgba(11,13,14,0.12)",
        brand: "0 8px 24px rgba(24,69,85,0.18)",
      },
      transitionTimingFunction: {
        "out-quart": "cubic-bezier(0.25, 1, 0.5, 1)",
        "out-expo": "cubic-bezier(0.16, 1, 0.3, 1)",
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      transitionDuration: {
        fast: "120ms",
        base: "200ms",
        slow: "320ms",
        slower: "500ms",
      },
      letterSpacing: {
        tightest: "-0.025em",
        tighter: "-0.02em",
        tight: "-0.015em",
        wide: "0.08em",
        wider: "0.12em",
        widest: "0.16em",
      },
    },
  },
  plugins: [],
};

export default config;
