"use client";

import { useState } from "react";
import { Phone, FileDown } from "lucide-react";
import type { SelectionResult } from "@/schemas/result";
import { fetchQuestionnaireDocx, fetchEmptyQuestionnaireDocx, triggerDownload } from "@/lib/api";

interface EngineerCTAProps {
  result: SelectionResult | null;
}

export function EngineerCTA({ result }: EngineerCTAProps) {
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleDownloadDocx = async () => {
    setDownloadError(null);
    try {
      const blob = result
        ? await fetchQuestionnaireDocx(result, {})
        : await fetchEmptyQuestionnaireDocx();
      triggerDownload(blob, "Опросный_лист_КНС.docx");
    } catch (e) {
      setDownloadError(
        e instanceof Error
          ? `Не удалось скачать опросный лист: ${e.message}`
          : "Не удалось скачать опросный лист. Попробуйте позже или позвоните 8 (800) 222-44-57.",
      );
    }
  };

  return (
    <section id="engineer" className="kns-contact">
      <div className="kns-shell">
        <h2>Передать данные инженеру</h2>
        <p>Скачайте опросный лист или позвоните, чтобы обсудить параметры объекта.</p>
        <div className="kns-hero-actions">
          <a href="tel:+78002224457"><Phone size={17} aria-hidden="true" /> 8 (800) 222-44-57</a>
          <button type="button" onClick={handleDownloadDocx}>
            <FileDown size={17} aria-hidden="true" /> Скачать опросный лист
          </button>
        </div>
        {downloadError && <p role="alert" className="kns-error">{downloadError}</p>}
      </div>
    </section>
  );
}
