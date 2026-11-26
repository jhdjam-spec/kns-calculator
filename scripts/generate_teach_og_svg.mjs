#!/usr/bin/env node
// Генерирует OG-image для каждой темы /teach/* как SVG 1200×630.
// SVG чтобы:
//   1) не плодить PNG (легко править/локализовать)
//   2) индексируется в OG-картинках Telegram/VK/WhatsApp (поддерживают SVG)
//   3) лёгкий вес — каждая ~5 KB вместо 1.3 MB PNG
//
// Запуск: `node scripts/generate_teach_og_svg.mjs` (prebuild hook).

import { writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const repoRoot = resolve(dirname(__filename), "..");

const outDir = resolve(repoRoot, "frontend", "public", "og", "teach");
mkdirSync(outDir, { recursive: true });

// Brand: clover-зелёный + ink-950 (тёмный фон). Тематические иконки SVG-paths.
const BRAND = "#1F7A4D";
const BRAND_LIGHT = "#5CB389";
const DARK = "#0A0F0D";

const TOPICS = [
  {
    key: "hydraulics",
    title: "Гидравлика насосов",
    subtitle: "Q-H · NPSH · AOR/POR",
    norm: "ISO 9906 · СП 32",
    // Q-H curve
    icon: `<path d="M0,140 Q160,130 240,80 T480,20" stroke="#5CB389" stroke-width="6" fill="none" stroke-linecap="round"/>
           <circle cx="240" cy="80" r="10" fill="#5CB389"/>
           <text x="260" y="75" font-family="Inter,sans-serif" font-size="22" fill="#5CB389">BEP</text>`,
  },
  {
    key: "fire",
    title: "Пожарная защита",
    subtitle: "Резерв 1+1 · СП 10",
    norm: "СП 10.13130 · СП 8",
    icon: `<path d="M240,200 Q180,140 240,80 Q300,140 240,200 Z" fill="#5CB389"/>
           <path d="M240,150 Q210,120 240,90 Q270,120 240,150 Z" fill="#FFB400"/>`,
  },
  {
    key: "water",
    title: "Водоснабжение",
    subtitle: "СП 30 · СП 31",
    norm: "Хозбыт · Пожарный · Технический",
    icon: `<path d="M240,40 Q160,150 160,200 Q160,260 240,260 Q320,260 320,200 Q320,150 240,40 Z" fill="#5CB389" opacity="0.9"/>
           <path d="M240,60 Q180,150 180,200 Q180,240 240,240 Q300,240 300,200 Q300,150 240,60 Z" fill="#1F7A4D"/>`,
  },
  {
    key: "electrical",
    title: "Электрика КНС",
    subtitle: "ПУЭ · IP65 · VFD",
    norm: "I/II категория · Селективность",
    icon: `<path d="M260,40 L160,160 L240,160 L220,260 L320,140 L240,140 Z" fill="#5CB389" stroke="#FFB400" stroke-width="3"/>`,
  },
  {
    key: "structural",
    title: "Корпуса КНС",
    subtitle: "Полиэтилен · Стеклопластик",
    norm: "СП 22 · Всплытие · УГВ",
    icon: `<rect x="170" y="80" width="140" height="180" rx="14" fill="#1F7A4D" stroke="#5CB389" stroke-width="4"/>
           <path d="M170,160 L310,160" stroke="#5CB389" stroke-width="3" stroke-dasharray="6 4"/>
           <text x="180" y="175" font-family="Inter,sans-serif" font-size="14" fill="#5CB389">УГВ</text>`,
  },
  {
    key: "los",
    title: "ЛОС / биология",
    subtitle: "Нитрификация · ХПК · БПК",
    norm: "СП 32 §6 · Henze IWA",
    icon: `<circle cx="240" cy="150" r="60" fill="#1F7A4D" stroke="#5CB389" stroke-width="3"/>
           <circle cx="210" cy="135" r="8" fill="#5CB389"/>
           <circle cx="260" cy="160" r="6" fill="#5CB389"/>
           <circle cx="235" cy="180" r="10" fill="#5CB389"/>
           <circle cx="265" cy="125" r="5" fill="#5CB389"/>`,
  },
  {
    key: "documentation",
    title: "Документация КНС",
    subtitle: "КМД · КМ · Опросник",
    norm: "Спецификация · ТЗ · РД",
    icon: `<rect x="180" y="60" width="120" height="160" rx="6" fill="#0A0F0D" stroke="#5CB389" stroke-width="3"/>
           <path d="M195,90 L285,90 M195,110 L285,110 M195,130 L265,130 M195,150 L285,150 M195,170 L260,170" stroke="#5CB389" stroke-width="2"/>`,
  },
];

function buildSvg({ title, subtitle, norm, icon }) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${DARK}"/>
      <stop offset="100%" stop-color="#11201A"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>

  <!-- Clover marker -->
  <g transform="translate(80,80)">
    <circle cx="20" cy="20" r="22" fill="${BRAND}"/>
    <text x="20" y="27" text-anchor="middle" font-family="Inter,sans-serif" font-size="20" font-weight="700" fill="white">88</text>
  </g>
  <text x="140" y="100" font-family="Inter,sans-serif" font-size="22" font-weight="600" fill="${BRAND_LIGHT}">Серво-Юг · Подбор насоса для КНС</text>
  <text x="140" y="126" font-family="Inter,sans-serif" font-size="16" fill="#7A8B83">podborkns.ru — справочник по СП и ГОСТ</text>

  <!-- Title -->
  <text x="80" y="320" font-family="Inter,sans-serif" font-size="72" font-weight="700" fill="white" letter-spacing="-2">${title}</text>
  <text x="80" y="380" font-family="Inter,sans-serif" font-size="32" fill="${BRAND_LIGHT}">${subtitle}</text>

  <!-- Norm tag -->
  <rect x="80" y="430" width="${30 + norm.length * 11}" height="48" rx="24" fill="${BRAND}" opacity="0.18"/>
  <text x="100" y="461" font-family="Inter,sans-serif" font-size="20" font-weight="500" fill="${BRAND_LIGHT}">${norm}</text>

  <!-- Thematic icon (320×280, top-right) -->
  <g transform="translate(720,140) scale(1.0)">
    ${icon}
  </g>

  <!-- Footer -->
  <text x="80" y="580" font-family="Inter,sans-serif" font-size="18" fill="#5A6B63">17 лет · 1400+ объектов · Чисто, надёжно, надолго</text>
</svg>`;
}

for (const topic of TOPICS) {
  const svg = buildSvg(topic);
  const file = resolve(outDir, `${topic.key}.svg`);
  writeFileSync(file, svg, "utf-8");
}

console.log(`OK: ${TOPICS.length} OG-SVG → ${outDir}`);
