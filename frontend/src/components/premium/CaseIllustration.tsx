// ╭───────────────────────────────────────────────────────────────────────╮
// │ Тематические SVG-иллюстрации к карточкам кейсов на главной.            │
// │ Свой векторный арт (zero-licensing). Стиль — wireframe с brand-glow,   │
// │ единый с QHCurve и SVG-фоном hero.                                     │
// ╰───────────────────────────────────────────────────────────────────────╯
import { memo } from "react";

export type CaseKind = "hotel" | "residential" | "mall" | "roof_drain";

interface Props {
  kind: CaseKind;
}

const GLOW = "drop-shadow(0 0 12px rgba(61,157,98,0.18))";

/**
 * 4 уникальные сцены под 4 кейса. Каждая — wireframe + ключевой технический
 * элемент (трубы, КНС, поплавки), чтобы читать тип объекта за секунду.
 */
export const CaseIllustration = memo(function CaseIllustration({ kind }: Props) {
  return (
    <svg
      viewBox="0 0 200 150"
      className="absolute inset-0 w-full h-full"
      style={{ filter: GLOW }}
      role="img"
      aria-hidden="true"
    >
      <g
        stroke="rgba(255,255,255,0.5)"
        strokeWidth="0.75"
        fill="none"
        strokeLinejoin="round"
        strokeLinecap="round"
      >
        {kind === "hotel" && <HotelScene />}
        {kind === "residential" && <ResidentialScene />}
        {kind === "mall" && <MallScene />}
        {kind === "roof_drain" && <RoofDrainScene />}
      </g>
    </svg>
  );
});

/** Гостиница 4★: 8-этажная башня с балконами + бассейн + пальмы (Анапа) */
function HotelScene() {
  return (
    <>
      {/* Море-горизонт */}
      <line x1="0" y1="115" x2="200" y2="115" strokeDasharray="1 2" opacity="0.3" />
      {/* Земля */}
      <line x1="0" y1="135" x2="200" y2="135" />
      {/* Здание-башня */}
      <rect x="80" y="35" width="50" height="100" />
      {/* Этажи */}
      {Array.from({ length: 7 }).map((_, i) => (
        <line key={i} x1="80" y1={47 + i * 12} x2="130" y2={47 + i * 12} opacity="0.55" />
      ))}
      {/* Окна (тёмный → светлые подсветы) */}
      {Array.from({ length: 7 }).flatMap((_, row) =>
        [85, 95, 105, 115].map((x) => (
          <rect
            key={`${row}-${x}`}
            x={x}
            y={37 + row * 12}
            width="6"
            height="8"
            fill="rgba(61,157,98,0.25)"
            stroke="none"
          />
        ))
      )}
      {/* 4 звезды на фронтоне */}
      <g fill="rgba(212,178,107,0.8)" stroke="none">
        {[90, 100, 110, 120].map((x) => (
          <polygon
            key={x}
            points={`${x},27 ${x + 1.2},30 ${x + 4},30 ${x + 1.8},32 ${x + 2.5},35 ${x},33 ${x - 2.5},35 ${x - 1.8},32 ${x - 4},30 ${x - 1.2},30`}
          />
        ))}
      </g>
      {/* Бассейн справа */}
      <rect x="145" y="120" width="40" height="12" rx="2" />
      <line x1="148" y1="124" x2="183" y2="124" strokeDasharray="1.5 2" opacity="0.5" />
      <line x1="148" y1="128" x2="183" y2="128" strokeDasharray="1.5 2" opacity="0.5" />
      {/* Пальмы */}
      <g>
        <line x1="20" y1="135" x2="20" y2="105" strokeWidth="1.25" />
        <path d="M 20 105 q -8 -4 -14 -2 M 20 105 q 8 -4 14 -2 M 20 105 q -4 -8 -2 -14 M 20 105 q 4 -8 2 -14" />
        <line x1="42" y1="135" x2="42" y2="112" strokeWidth="1" />
        <path d="M 42 112 q -6 -3 -10 -1 M 42 112 q 6 -3 10 -1 M 42 112 q -3 -6 -1 -10" />
      </g>
      {/* Подземная КНС с насосом — техническая суть */}
      <ellipse cx="155" cy="142" rx="14" ry="3" opacity="0.3" />
      <path d="M 141 142 L 141 148 M 169 142 L 169 148" strokeDasharray="1 1.5" opacity="0.5" />
    </>
  );
}

/** ЖК: 3 башни разной высоты + людские силуэты внизу (Краснодар, 320 квартир) */
function ResidentialScene() {
  return (
    <>
      {/* Земля */}
      <line x1="0" y1="135" x2="200" y2="135" />
      {/* Башня 1 — низкая */}
      <rect x="30" y="55" width="36" height="80" />
      {Array.from({ length: 8 }).flatMap((_, row) =>
        [35, 45, 55].map((x) => (
          <rect
            key={`t1-${row}-${x}`}
            x={x}
            y={60 + row * 9}
            width="6"
            height="5"
            fill="rgba(61,157,98,0.22)"
            stroke="none"
          />
        ))
      )}
      {/* Башня 2 — высокая */}
      <rect x="78" y="25" width="42" height="110" />
      {Array.from({ length: 11 }).flatMap((_, row) =>
        [83, 94, 105, 113].map((x) => (
          <rect
            key={`t2-${row}-${x}`}
            x={x}
            y={30 + row * 9}
            width="6"
            height="5"
            fill="rgba(61,157,98,0.28)"
            stroke="none"
          />
        ))
      )}
      {/* Башня 3 — средняя */}
      <rect x="132" y="42" width="40" height="93" />
      {Array.from({ length: 9 }).flatMap((_, row) =>
        [136, 146, 156, 165].map((x) => (
          <rect
            key={`t3-${row}-${x}`}
            x={x}
            y={47 + row * 9}
            width="6"
            height="5"
            fill="rgba(61,157,98,0.20)"
            stroke="none"
          />
        ))
      )}
      {/* Антенны на крышах */}
      <line x1="50" y1="55" x2="50" y2="48" strokeWidth="0.5" />
      <line x1="99" y1="25" x2="99" y2="15" strokeWidth="0.5" />
      <line x1="152" y1="42" x2="152" y2="35" strokeWidth="0.5" />
      {/* Деревья перед двором */}
      <g>
        {[12, 75, 125, 188].map((x, i) => (
          <g key={i}>
            <line x1={x} y1="135" x2={x} y2="128" strokeWidth="0.5" />
            <circle cx={x} cy="125" r="4" fill="rgba(61,157,98,0.2)" stroke="rgba(255,255,255,0.4)" strokeWidth="0.5" />
          </g>
        ))}
      </g>
      {/* Линия подземного коллектора → точка КНС */}
      <line x1="0" y1="145" x2="200" y2="145" strokeDasharray="2 2" opacity="0.4" />
      <circle cx="100" cy="145" r="2" fill="rgba(212,178,107,0.7)" stroke="none" />
    </>
  );
}

/** ТРЦ: широкое плоское здание + парковка + 3 насоса (Ростов, 30 000 м²) */
function MallScene() {
  return (
    <>
      {/* Земля */}
      <line x1="0" y1="135" x2="200" y2="135" />
      {/* Парковка слева — линии разметки */}
      <g opacity="0.4">
        {[10, 20, 30, 40, 50].map((x) => (
          <line key={x} x1={x} y1="120" x2={x} y2="135" strokeDasharray="1 1" />
        ))}
        <line x1="5" y1="120" x2="55" y2="120" />
      </g>
      {/* Машины-боксы */}
      <rect x="11" y="125" width="8" height="6" fill="rgba(61,157,98,0.2)" stroke="none" />
      <rect x="21" y="125" width="8" height="6" fill="rgba(61,157,98,0.2)" stroke="none" />
      <rect x="41" y="125" width="8" height="6" fill="rgba(61,157,98,0.2)" stroke="none" />
      {/* Плоский ТРЦ-комплекс */}
      <path d="M 65 135 L 65 75 L 80 65 L 145 65 L 160 75 L 160 135 Z" />
      {/* Стеклянный фасад */}
      <g opacity="0.55">
        {[70, 85, 100, 115, 130, 145].map((x) => (
          <line key={x} x1={x} y1="80" x2={x} y2="135" />
        ))}
        <line x1="65" y1="100" x2="160" y2="100" strokeDasharray="2 1" />
        <line x1="65" y1="118" x2="160" y2="118" strokeDasharray="2 1" />
      </g>
      {/* Витрины-подсветы */}
      <rect x="68" y="120" width="22" height="13" fill="rgba(61,157,98,0.3)" stroke="none" />
      <rect x="92" y="120" width="22" height="13" fill="rgba(212,178,107,0.18)" stroke="none" />
      <rect x="116" y="120" width="22" height="13" fill="rgba(61,157,98,0.3)" stroke="none" />
      {/* Логотип-вывеска */}
      <rect x="105" y="70" width="20" height="6" fill="rgba(212,178,107,0.5)" stroke="none" />
      {/* КНС-площадка справа: 3 насоса × ×3 modules */}
      <g transform="translate(170,120)">
        <rect width="22" height="15" fill="rgba(255,255,255,0.04)" />
        <line x1="0" y1="0" x2="22" y2="0" />
        <line x1="0" y1="15" x2="22" y2="15" />
        <line x1="0" y1="0" x2="0" y2="15" />
        <line x1="22" y1="0" x2="22" y2="15" />
        <circle cx="4" cy="7" r="2" />
        <circle cx="11" cy="7" r="2" />
        <circle cx="18" cy="7" r="2" />
      </g>
    </>
  );
}

/** Дренаж кровли: плоское здание + дождь + воронки (Сочи, 5 га, 974 м³/ч) */
function RoofDrainScene() {
  return (
    <>
      {/* Облако */}
      <g opacity="0.4">
        <ellipse cx="60" cy="22" rx="16" ry="6" />
        <ellipse cx="80" cy="20" rx="14" ry="5" />
        <ellipse cx="115" cy="24" rx="18" ry="7" />
        <ellipse cx="145" cy="22" rx="14" ry="5" />
      </g>
      {/* Дождь — диагональные штрихи */}
      <g stroke="rgba(122,178,191,0.55)" strokeWidth="0.5">
        {Array.from({ length: 28 }).map((_, i) => {
          const x = 35 + (i % 14) * 10 + (i > 13 ? 5 : 0);
          const y = 35 + Math.floor(i / 14) * 12;
          return <line key={i} x1={x} y1={y} x2={x - 3} y2={y + 8} />;
        })}
      </g>
      {/* Земля */}
      <line x1="0" y1="135" x2="200" y2="135" />
      {/* Плоская кровля промышленного объекта */}
      <path d="M 10 135 L 10 95 L 190 95 L 190 135 Z" />
      {/* Парапет */}
      <line x1="10" y1="93" x2="190" y2="93" strokeWidth="1.25" />
      {/* Воронки на кровле (3 шт) */}
      <g>
        {[50, 100, 150].map((x) => (
          <g key={x}>
            <ellipse cx={x} cy="97" rx="6" ry="2" fill="rgba(212,178,107,0.5)" stroke="rgba(255,255,255,0.7)" strokeWidth="0.75" />
            {/* Стоковая труба вниз */}
            <line x1={x} y1="99" x2={x} y2="120" strokeDasharray="1 1" opacity="0.6" />
          </g>
        ))}
      </g>
      {/* Фасад — окна на промздании */}
      <g opacity="0.5">
        {[20, 35, 50, 65, 80, 95, 110, 125, 140, 155, 170].map((x) => (
          <rect key={x} x={x} y="105" width="8" height="6" fill="rgba(61,157,98,0.18)" stroke="none" />
        ))}
        {[20, 35, 50, 65, 80, 95, 110, 125, 140, 155, 170].map((x) => (
          <rect key={`r2-${x}`} x={x} y="118" width="8" height="6" fill="rgba(61,157,98,0.18)" stroke="none" />
        ))}
      </g>
      {/* КНС-приямок: показывает, куда вода уходит */}
      <ellipse cx="100" cy="143" rx="18" ry="3" />
      <line x1="82" y1="143" x2="82" y2="150" strokeDasharray="1 1" opacity="0.4" />
      <line x1="118" y1="143" x2="118" y2="150" strokeDasharray="1 1" opacity="0.4" />
      <circle cx="92" cy="146" r="1.5" fill="rgba(212,178,107,0.6)" stroke="none" />
      <circle cx="108" cy="146" r="1.5" fill="rgba(212,178,107,0.6)" stroke="none" />
    </>
  );
}
