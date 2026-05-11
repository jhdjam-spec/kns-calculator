"use client";

/** Декоративный SVG Q-H график для hero. Не настоящие данные — показывает форму
 * характеристики центробежного насоса. Принимает Q (нормированный 0..1) для
 * позиционирования рабочей точки.
 *
 * Theme-aware: использует currentColor для сетки/осей/подписей через text-классы
 * Tailwind (light: ink-700/600, dark: white-translucent). Кривые имеют отдельные
 * <linearGradient> для light (brand teal) и dark (accent brass) режимов через
 * dark:hidden / hidden dark:block.
 */
export function QHCurve({ qNormalized = 0.4 }: { qNormalized?: number }) {
  const W = 480;
  const H = 360;
  const padX = 60;
  const padY = 50;

  // Кривая Q-H: H = H0 - k*Q^2 (parabola, типичная для центробежного)
  const points: string[] = [];
  for (let i = 0; i <= 50; i++) {
    const t = i / 50;
    const x = padX + t * (W - 2 * padX);
    const y = padY + (0.15 + 0.7 * t * t) * (H - 2 * padY);
    points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  const pumpCurve = points.join(" ");

  // Системная кривая (что нужно проекту): pieced как линейная нарастающая
  const sysPoints: string[] = [];
  for (let i = 0; i <= 50; i++) {
    const t = i / 50;
    const x = padX + t * (W - 2 * padX);
    const y = padY + (0.85 - 0.55 * t) * (H - 2 * padY);
    sysPoints.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  const sysCurve = sysPoints.join(" ");

  // Точка пересечения (приблизительно)
  const intersectX = padX + qNormalized * (W - 2 * padX);
  const tIntersect = qNormalized;
  const intersectY = padY + (0.15 + 0.7 * tIntersect * tIntersect) * (H - 2 * padY);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full h-full text-ink-700 dark:text-white"
      role="img"
      aria-label="Характеристика насоса Q-H"
    >
      <defs>
        {/* Dark mode: brass-gold pump curve gradient */}
        <linearGradient id="qhFadeDark" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgb(212 178 107)" stopOpacity="0" />
          <stop offset="20%" stopColor="rgb(212 178 107)" stopOpacity="1" />
          <stop offset="100%" stopColor="rgb(212 178 107)" stopOpacity="1" />
        </linearGradient>
        {/* Light mode: deep teal pump curve gradient */}
        <linearGradient id="qhFadeLight" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="rgb(24 69 85)" stopOpacity="0" />
          <stop offset="20%" stopColor="rgb(24 69 85)" stopOpacity="1" />
          <stop offset="100%" stopColor="rgb(24 69 85)" stopOpacity="1" />
        </linearGradient>
      </defs>

      {/* Сетка — используем currentColor с низкой opacity */}
      {Array.from({ length: 8 }).map((_, i) => {
        const x = padX + (i * (W - 2 * padX)) / 7;
        return (
          <line
            key={`vx-${i}`}
            x1={x}
            y1={padY}
            x2={x}
            y2={H - padY}
            stroke="currentColor"
            strokeOpacity="0.08"
            strokeWidth="1"
          />
        );
      })}
      {Array.from({ length: 6 }).map((_, i) => {
        const y = padY + (i * (H - 2 * padY)) / 5;
        return (
          <line
            key={`hy-${i}`}
            x1={padX}
            y1={y}
            x2={W - padX}
            y2={y}
            stroke="currentColor"
            strokeOpacity="0.08"
            strokeWidth="1"
          />
        );
      })}

      {/* Оси */}
      <line
        x1={padX}
        y1={H - padY}
        x2={W - padX}
        y2={H - padY}
        stroke="currentColor"
        strokeOpacity="0.35"
        strokeWidth="1"
      />
      <line
        x1={padX}
        y1={padY}
        x2={padX}
        y2={H - padY}
        stroke="currentColor"
        strokeOpacity="0.35"
        strokeWidth="1"
      />

      {/* Засечки осей */}
      {Array.from({ length: 8 }).map((_, i) => {
        const x = padX + (i * (W - 2 * padX)) / 7;
        return (
          <line
            key={`tickx-${i}`}
            x1={x}
            y1={H - padY}
            x2={x}
            y2={H - padY + 4}
            stroke="currentColor"
            strokeOpacity="0.5"
            strokeWidth="1"
          />
        );
      })}

      {/* Подписи осей */}
      <text
        x={W - padX}
        y={H - padY + 24}
        textAnchor="end"
        fill="currentColor"
        fillOpacity="0.6"
        fontSize="11"
        fontFamily="var(--font-mono)"
      >
        Q, м³/ч
      </text>
      <text
        x={padX - 12}
        y={padY - 12}
        textAnchor="end"
        fill="currentColor"
        fillOpacity="0.6"
        fontSize="11"
        fontFamily="var(--font-mono)"
      >
        H, м
      </text>

      {/* Системная кривая (пунктир) — brand teal в обеих темах, но opacity варьируется */}
      <polyline
        points={sysCurve}
        fill="none"
        stroke="rgba(122,178,191,0.7)"
        strokeWidth="1.25"
        strokeDasharray="4 4"
        className="dark:opacity-100 opacity-90"
      />

      {/* Кривая насоса — light variant (deep teal brand-700) */}
      <polyline
        points={pumpCurve}
        fill="none"
        stroke="url(#qhFadeLight)"
        strokeWidth="1.75"
        strokeLinecap="round"
        className="dark:hidden"
      />
      {/* Кривая насоса — dark variant (brass accent) */}
      <polyline
        points={pumpCurve}
        fill="none"
        stroke="url(#qhFadeDark)"
        strokeWidth="1.75"
        strokeLinecap="round"
        className="hidden dark:block"
      />

      {/* Рабочая точка — light (deep teal) */}
      <g className="dark:hidden">
        <circle cx={intersectX} cy={intersectY} r="6" fill="rgb(24 69 85)" opacity="0.4">
          <animate attributeName="r" values="6;9;6" dur="1.6s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.4;0.1;0.4" dur="1.6s" repeatCount="indefinite" />
        </circle>
        <circle cx={intersectX} cy={intersectY} r="3" fill="rgb(24 69 85)" />
        <text
          x={intersectX + 12}
          y={intersectY - 6}
          fill="rgb(24 69 85)"
          fontSize="11"
          fontFamily="var(--font-mono)"
          fontWeight="500"
        >
          рабочая точка
        </text>
      </g>

      {/* Рабочая точка — dark (brass) */}
      <g className="hidden dark:block">
        <circle cx={intersectX} cy={intersectY} r="6" fill="rgb(212 178 107)" opacity="0.4">
          <animate attributeName="r" values="6;9;6" dur="1.6s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.4;0.1;0.4" dur="1.6s" repeatCount="indefinite" />
        </circle>
        <circle cx={intersectX} cy={intersectY} r="3" fill="rgb(212 178 107)" />
        <text
          x={intersectX + 12}
          y={intersectY - 6}
          fill="rgb(212 178 107)"
          fontSize="11"
          fontFamily="var(--font-mono)"
          fontWeight="500"
        >
          рабочая точка
        </text>
      </g>

      {/* Легенда */}
      <g transform={`translate(${padX}, ${H - 18})`}>
        {/* Light: brand teal */}
        <line
          x1="0"
          y1="0"
          x2="20"
          y2="0"
          stroke="rgb(24 69 85)"
          strokeWidth="1.75"
          className="dark:hidden"
        />
        {/* Dark: brass */}
        <line
          x1="0"
          y1="0"
          x2="20"
          y2="0"
          stroke="rgb(212 178 107)"
          strokeWidth="1.75"
          className="hidden dark:block"
        />
        <text
          x="26"
          y="3"
          fill="currentColor"
          fillOpacity="0.6"
          fontSize="10"
          fontFamily="var(--font-mono)"
        >
          насос
        </text>
        <line
          x1="100"
          y1="0"
          x2="120"
          y2="0"
          stroke="rgba(122,178,191,0.7)"
          strokeWidth="1.25"
          strokeDasharray="3 3"
        />
        <text
          x="126"
          y="3"
          fill="currentColor"
          fillOpacity="0.6"
          fontSize="10"
          fontFamily="var(--font-mono)"
        >
          ваша система
        </text>
      </g>
    </svg>
  );
}
