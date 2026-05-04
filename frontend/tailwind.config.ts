import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Цвета сегментов: чем дороже — тем "увесистее" визуально.
        // Не используем "светофор" (зелёный/жёлтый/красный) — это семантика
        // оптимума/предупреждения/опасности, а не цены. Бюджет — нейтральный
        // серый, премиум — насыщенный индиго.
        budget: "#64748b",   // slate-500 — нейтральный серый
        mid: "#0891b2",      // cyan-600 — деловой бирюзовый
        premium: "#4f46e5",  // indigo-600 — премиум
      },
    },
  },
  plugins: [],
};

export default config;
