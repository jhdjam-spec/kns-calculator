import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Семантические цвета сегментов
        budget: "#16a34a",  // green-600
        mid: "#ca8a04",     // yellow-600
        premium: "#2563eb", // blue-600
      },
    },
  },
  plugins: [],
};

export default config;
