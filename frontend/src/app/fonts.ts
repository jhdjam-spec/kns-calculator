import { Manrope, Inter, JetBrains_Mono } from "next/font/google";

export const manrope = Manrope({
  subsets: ["latin", "cyrillic"],
  variable: "--font-display",
  weight: ["600", "700", "800"],
  display: "swap",
});

export const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
  display: "swap",
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap",
});
