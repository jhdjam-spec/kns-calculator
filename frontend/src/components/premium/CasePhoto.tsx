// ╭───────────────────────────────────────────────────────────────────────╮
// │ Гибрид: stock-фото на фоне + SVG-wireframe overlay + clover-gradient. │
// │ Фото — локально в /public/cases/<kind>.webp (~25-50 KB каждое).        │
// │ Лицензия: Unsplash License (free for commercial use, no attribution).  │
// ╰───────────────────────────────────────────────────────────────────────╯
import { memo } from "react";
import { CaseIllustration, type CaseKind } from "./CaseIllustration";

interface Props {
  kind: CaseKind;
  alt: string;
}

/** Маппинг типа объекта → файл фото в /public/cases/. */
const PHOTO_PATH: Record<CaseKind, string> = {
  hotel: "/cases/hotel.webp",
  residential: "/cases/residential.webp",
  mall: "/cases/mall.webp",
  roof_drain: "/cases/roof_drain.webp",
};

export const CasePhoto = memo(function CasePhoto({ kind, alt }: Props) {
  const photoSrc = PHOTO_PATH[kind];

  return (
    <>
      {/* Фото-фон: lazy, sync decode для plain <img> в static export */}
      <img
        src={photoSrc}
        alt={alt}
        loading="lazy"
        decoding="async"
        className="absolute inset-0 w-full h-full object-cover"
        // Если файла нет — graceful degradation: SVG-wireframe виден поверх пустого фона
        onError={(e) => {
          e.currentTarget.style.display = "none";
        }}
      />

      {/* Clover-gradient overlay для бренд-единства и контраста с текстом-меткой */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(135deg, rgba(31,122,77,0.55) 0%, rgba(10,15,13,0.35) 60%, rgba(10,15,13,0.7) 100%)",
        }}
        aria-hidden="true"
      />

      {/* SVG-wireframe сверху, opacity 0.35 — служит «технической схемой» поверх фото */}
      <div className="absolute inset-0 opacity-35 mix-blend-screen pointer-events-none">
        <CaseIllustration kind={kind} />
      </div>
    </>
  );
});
