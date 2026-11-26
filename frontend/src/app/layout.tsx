import type { Metadata, Viewport } from "next";
import { Providers } from "./providers";
import { inter, jetbrainsMono } from "./fonts";
import { BetaBanner } from "@/components/BetaBanner";
import { EncyclopediaDrawer } from "@/components/teach/EncyclopediaDrawer";
import { Analytics } from "@/components/Analytics";
import "./globals.css";

// Production URL: https://podborkns.ru (с 2026-05-16).
// Старый: https://kns-calculator-frontend.website.yandexcloud.net
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://podborkns.ru";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Серво-Юг — подбор насоса для КНС, ЛОС и СПД · калькулятор",
  description:
    "Подбор насосного оборудования для канализационных, ливневых, пожарных и водоподающих станций. От ТЗ до спецификации с гидравликой за минуту. Серво-Юг — производитель оборудования с 2009 года.",
  authors: [{ name: "Морозов Константин · Layout Stars Studio", url: "https://inservo.ru" }],
  creator: "Layout Stars Studio by inservo.ru",
  publisher: "Серво-Юг",
  alternates: {
    canonical: "/",
  },
  icons: {
    icon: "/icon.png",
    apple: "/apple-touch-icon.png",
  },
  openGraph: {
    title: "Серво-Юг — подбор насоса для КНС, ЛОС и СПД",
    description:
      "Чисто, надёжно, надолго. Подбор насосного оборудования с гидравликой за минуту. Серво-Юг — производство с 2009 года.",
    type: "website",
    locale: "ru_RU",
    siteName: "Серво-Юг",
    url: SITE_URL,
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 1200,
        alt: "Серво-Юг — качественная автономная канализация. Чисто, надёжно, надолго",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Серво-Юг — подбор насоса для КНС, ЛОС и СПД",
    description:
      "Чисто, надёжно, надолго. Подбор насосного оборудования с гидравликой за минуту.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

/**
 * Inline-скрипт устанавливает .dark/.light на <html> до первого рендера,
 * чтобы избежать FOUC при переключении темы. Читает localStorage.theme:
 *   "dark"  → принудительно тёмная
 *   "light" → принудительно светлая
 *   "auto"/отсутствует → ничего не ставим, темой управляет CSS prefers-color-scheme.
 */
const themeInitScript = `(function(){try{var t=localStorage.getItem('theme');var r=document.documentElement;if(t==='dark'){r.classList.add('dark');}else if(t==='light'){r.classList.add('light');}}catch(e){}})();`;

/**
 * Структурированные данные о сайте и услугах компании.
 */
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}#organization`,
      name: "Серво-Юг",
      alternateName: ["Layout Stars Studio"],
      url: SITE_URL,
      logo: `${SITE_URL}/icon.png`,
      foundingDate: "2009",
      slogan: "Чисто, надёжно, надолго",
      description:
        "Производитель насосного оборудования и КНС/ЛОС/СПД-станций с 2009 года. Поставка по югу России: Краснодарский край, Адыгея, Ростов, Крым, Ставрополь.",
      address: [
        {
          "@type": "PostalAddress",
          addressCountry: "RU",
          addressRegion: "Краснодарский край",
          addressLocality: "Сочи",
        },
        {
          "@type": "PostalAddress",
          addressCountry: "RU",
          addressRegion: "Республика Адыгея",
          addressLocality: "аул Хатукай",
          description: "Производственная площадка",
        },
      ],
      contactPoint: [
        {
          "@type": "ContactPoint",
          telephone: "+7-800-222-44-57",
          contactType: "sales",
          availableLanguage: ["ru"],
          areaServed: "RU",
        },
        {
          "@type": "ContactPoint",
          telephone: "+7-988-237-32-87",
          contactType: "customer support",
          availableLanguage: ["ru"],
          contactOption: "TollFree",
        },
      ],
      email: "zakaz@inservo.ru",
      sameAs: [
        "https://inservo.ru",
        "https://emkosti.pro",
        "https://servotank.ru",
      ],
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}#website`,
      url: SITE_URL,
      name: "Серво-Юг · Калькулятор подбора КНС/ЛОС/СПД",
      publisher: { "@id": `${SITE_URL}#organization` },
      inLanguage: "ru-RU",
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${SITE_URL}#calculator`,
      name: "Калькулятор подбора КНС / ЛОС / СПД",
      description:
        "Бесплатный онлайн-калькулятор подбора насосного оборудования для канализационных насосных станций, локальных очистных сооружений и станций повышения давления. Расчёт по СП 32.13330, 494 моделей насосов в базе.",
      applicationCategory: "EngineeringApplication",
      operatingSystem: "Web",
      url: SITE_URL,
      inLanguage: "ru-RU",
      offers: { "@type": "Offer", price: "0", priceCurrency: "RUB" },
      publisher: { "@id": `${SITE_URL}#organization` },
      featureList: [
        "Подбор насоса по Q-H",
        "Гидравлический расчёт по СП 32.13330",
        "Расчёт ливневой канализации",
        "Прочностной расчёт корпуса КНС",
        "Подбор резервуаров ПЭ/стеклопластик",
        "Энциклопедия инженера ВК",
        "Импорт ТЗ из DOCX",
        "Спецификация в PDF/DOCX",
      ],
      browserRequirements: "Современный браузер с включённым JavaScript",
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        {
          "@type": "ListItem",
          position: 1,
          name: "Главная",
          item: SITE_URL,
        },
      ],
    },
    // Service-схемы для AI-поисковиков (повышают видимость в локальных запросах
    // «купить КНС Краснодар», «производитель ЛОС юг России»).
    {
      "@type": "Service",
      "@id": `${SITE_URL}#service-kns`,
      name: "Производство и поставка КНС (канализационных насосных станций)",
      serviceType: "Sewage Pump Station Manufacturing",
      provider: { "@id": `${SITE_URL}#organization` },
      areaServed: [
        { "@type": "AdministrativeArea", name: "Краснодарский край" },
        { "@type": "AdministrativeArea", name: "Республика Адыгея" },
        { "@type": "AdministrativeArea", name: "Ростовская область" },
        { "@type": "AdministrativeArea", name: "Республика Крым" },
        { "@type": "AdministrativeArea", name: "Ставропольский край" },
      ],
      description:
        "Изготовление КНС из ПЭ и стеклопластика D800-D3000 мм для бытовой, ливневой, промышленной канализации. Шеф-монтаж и пусконаладка. Проектирование по СП 32.13330.",
      offers: { "@type": "AggregateOffer", priceCurrency: "RUB", lowPrice: "70000" },
    },
    {
      "@type": "Service",
      "@id": `${SITE_URL}#service-los`,
      name: "Локальные очистные сооружения (ЛОС)",
      serviceType: "Wastewater Treatment Plant Manufacturing",
      provider: { "@id": `${SITE_URL}#organization` },
      areaServed: { "@type": "Country", name: "Россия" },
      description:
        "Производство ЛОС для жилых, гостиничных и промышленных объектов. Биологическая очистка, нитрификация, баланс БПК/ХПК. Расчёт по Henze IWA 2008 и СП 32.13330.",
    },
    {
      "@type": "Service",
      "@id": `${SITE_URL}#service-spd`,
      name: "Станции повышения давления (СПД)",
      serviceType: "Pressure Boosting Station",
      provider: { "@id": `${SITE_URL}#organization` },
      areaServed: { "@type": "Country", name: "Россия" },
      description:
        "СПД для холодного и горячего водоснабжения по СП 30.13330. Подбор по расходу 5-1000 м³/ч, напор до 80 м.",
    },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="ru"
      className={`${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Yandex Webmaster — добавьте сюда meta-tag после регистрации:
            <meta name="yandex-verification" content="..." />
            Google Search Console:
            <meta name="google-site-verification" content="..." /> */}
        <meta name="yandex-verification" content="c8ba367f2221e7b4" />
        <meta name="google-site-verification" content="RSl9S9_fWbgOMAouCp-YJi7moYVTvuWmHYJJh7I-oaw" />

        {/* Resource hints для backend API — снижает latency первого запроса */}
        <link rel="preconnect" href="https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net" />
        <link rel="dns-prefetch" href="https://d5dnu7r53036cq815mes.ccx97b51.apigw.yandexcloud.net" />

        {/* Preconnect для YooMoney iframe (Fundraise widget на /#donate) */}
        <link rel="preconnect" href="https://yoomoney.ru" />

        {/* Webmaster для других поисковиков */}
        <meta name="msvalidate.01" content="PENDING_BING_VERIFICATION" />
        <meta name="mailru-verification" content="PENDING_MAILRU_VERIFICATION" />

        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body>
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:bg-brand-500 focus:text-white focus:px-4 focus:py-2 focus:rounded"
        >
          К содержимому
        </a>
        {/* BetaBanner убран из top — оправдывался до того как пользователь
            увидел продукт (убийца доверия по copy-аудиту). Дисклеймер
            теперь живёт в SiteFooter + /legal. */}
        <Providers>
          {children}
          <EncyclopediaDrawer />
        </Providers>
        <Analytics />
      </body>
    </html>
  );
}
