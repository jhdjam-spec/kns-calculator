// Server-side generateStaticParams + JSON-LD Article schema для каждой темы.
// 7 тем энциклопедии — список фиксирован, синхронизирован с backend
// pump_calculator/encyclopedia/registry.py.
//
// JSON-LD Article повышает цитируемость в AI-поисковиках и Google rich-results.

const TOPIC_KEYS = [
  "fire",
  "water",
  "electrical",
  "hydraulics",
  "structural",
  "los",
  "documentation",
] as const;

type TopicKey = (typeof TOPIC_KEYS)[number];

const TOPIC_META: Record<TopicKey, { title: string; description: string }> = {
  fire: {
    title: "Пожарный водопровод и СП 10.13130 — энциклопедия инженера",
    description:
      "Внутренний пожарный водопровод, СП 10.13130, расчёт расхода и напора для пожарных насосов. Резервирование 1+1 (один рабочий + один резервный).",
  },
  water: {
    title: "Водоснабжение и водоотведение — нормы СП 30 / СП 31",
    description:
      "Хозяйственно-питьевое и противопожарное водоснабжение, нормы потребления СП 30.13330, расходы по СП 31.13330.",
  },
  electrical: {
    title: "Электрика КНС: ПУЭ, ВРУ, IP65, частотное регулирование",
    description:
      "Электроснабжение канализационных насосных станций: I/II категория по ПУЭ, селективность защит, частотные преобразователи, кабели в раструбах.",
  },
  hydraulics: {
    title: "Гидравлика насосов: Q-H характеристика, NPSH, AOR/POR",
    description:
      "Подбор центробежных насосов по характеристике Q-H, кавитационный запас NPSHa/NPSHr, рабочая зона AOR (ANSI/HI) и POR.",
  },
  structural: {
    title: "Корпуса КНС: полиэтилен, стеклопластик, бетонные кольца",
    description:
      "Материалы корпусов КНС, расчёт прочности при УГВ (уровень грунтовых вод), противоразмывные рёбра, толщина стенки по СП 22.",
  },
  los: {
    title: "ЛОС — локальные очистные сооружения, биологическая очистка",
    description:
      "Локальные очистные сооружения, нитрификация/денитрификация, аэробные/анаэробные процессы, СП 32 §6, нормативы сброса.",
  },
  documentation: {
    title: "Документация КНС: КМД, КМ, опросный лист, спецификация",
    description:
      "Состав рабочей документации: КМД (конструкции металлические деталировочные), КМ (конструкции металлические), спецификация оборудования, опросный лист.",
  },
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://podborkns.ru";

export function generateStaticParams() {
  return TOPIC_KEYS.map((topic) => ({ topic }));
}

export function generateMetadata({ params }: { params: { topic: string } }) {
  const meta = TOPIC_META[params.topic as TopicKey];
  if (!meta) return {};
  const ogImage = `${SITE_URL}/og/teach/${params.topic}.svg`;
  return {
    title: meta.title,
    description: meta.description,
    alternates: { canonical: `/teach/${params.topic}` },
    openGraph: {
      title: meta.title,
      description: meta.description,
      type: "article",
      url: `${SITE_URL}/teach/${params.topic}`,
      locale: "ru_RU",
      images: [
        {
          url: ogImage,
          width: 1200,
          height: 630,
          alt: meta.title,
          type: "image/svg+xml",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: meta.title,
      description: meta.description,
      images: [ogImage],
    },
  };
}

export default function TeachTopicLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { topic: string };
}) {
  const meta = TOPIC_META[params.topic as TopicKey];

  // BreadcrumbList — для AI-поисковиков (Yandex Yazeka, Google AI Overviews)
  // и для Rich Snippets в SERP. 3 уровня: Главная → Энциклопедия → Топик.
  const breadcrumb = meta
    ? {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Главная",
            item: SITE_URL,
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Энциклопедия",
            item: `${SITE_URL}/teach`,
          },
          {
            "@type": "ListItem",
            position: 3,
            name: meta.title.split(" — ")[0],
            item: `${SITE_URL}/teach/${params.topic}`,
          },
        ],
      }
    : null;

  const jsonLd = meta
    ? {
        "@context": "https://schema.org",
        "@type": "Article",
        headline: meta.title,
        description: meta.description,
        url: `${SITE_URL}/teach/${params.topic}`,
        inLanguage: "ru-RU",
        author: {
          "@type": "Organization",
          name: "Серво-Юг",
          url: SITE_URL,
        },
        publisher: {
          "@type": "Organization",
          name: "Серво-Юг",
          url: SITE_URL,
        },
        mainEntityOfPage: `${SITE_URL}/teach/${params.topic}`,
      }
    : null;

  // Server-side <h1> для SEO/AI-поисковиков: на /teach/[topic] он обязателен,
  // так как сама page.tsx — "use client" и заголовок в исходном HTML отсутствует.
  // h1 берём из meta.title (без "— энциклопедия инженера" хвоста — короче и читаемее).
  const h1Text = meta ? meta.title.split(" — ")[0] : "";

  return (
    <>
      {breadcrumb && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumb) }}
        />
      )}
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
      {h1Text && (
        <h1 className="sr-only" itemProp="headline">
          {h1Text}
        </h1>
      )}
      {children}
    </>
  );
}
