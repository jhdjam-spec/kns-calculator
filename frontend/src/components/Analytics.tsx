"use client";

import Script from "next/script";

/**
 * Аналитика: Yandex Metrika + Google Analytics 4.
 *
 * Загружается через next/script с strategy="afterInteractive" — не блокирует
 * LCP/FCP, грузится после first paint. Идле-загрузка.
 *
 * Цели/события (трекаются автоматически + custom через window.ym/window.gtag):
 *  - docx_download: клик на скачивание опросного листа DOCX
 *  - pdf_download: клик на скачивание PDF спецификации
 *  - donate_click: переход на YooMoney Fundraise
 *  - calculator_submit: расчёт через калькулятор
 *  - phone_click: tap по tel:
 *  - email_click: tap по mailto:
 *
 * Чтобы активировать — задайте:
 *   NEXT_PUBLIC_YM_ID=12345678
 *   NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX
 *
 * Без env-переменных скрипты НЕ загружаются — не нагружают сайт впустую.
 */
export function Analytics() {
  const YM_ID = process.env.NEXT_PUBLIC_YM_ID;
  const YM_ID_ONLINE = process.env.NEXT_PUBLIC_YM_ID_ONLINE;
  const GA_ID = process.env.NEXT_PUBLIC_GA_ID;

  if (!YM_ID && !GA_ID) return null;

  return (
    <>
      {/* Yandex Metrika — domain-aware: на podborkns.ru используется YM_ID,
          на podborkns.online — YM_ID_ONLINE (если задан). Сейчас .online 301-редиректит
          на .ru, посетитель попадает на основной счётчик. Если когда-то перейдём
          в mirror-mode — каждый домен получит свой счётчик автоматически. */}
      {YM_ID && (
        <>
          <Script
            id="yandex-metrika"
            strategy="lazyOnload"
            dangerouslySetInnerHTML={{
              __html: `
(function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
m[i].l=1*new Date();
for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
(window, document,'script','https://mc.yandex.ru/metrika/tag.js?id=${YM_ID}','ym');
var __ym_id = ${YM_ID};
${YM_ID_ONLINE ? `try {
  if (location.hostname && location.hostname.indexOf('podborkns.online') !== -1) {
    __ym_id = ${YM_ID_ONLINE};
  }
} catch(_) {}` : ""}
ym(__ym_id, 'init', {
  ssr: true,
  webvisor: true,
  clickmap: true,
  ecommerce: 'dataLayer',
  referrer: document.referrer,
  url: location.href,
  accurateTrackBounce: true,
  trackLinks: true
});
              `,
            }}
          />
          <noscript>
            <div>
              <img
                src={`https://mc.yandex.ru/watch/${YM_ID}`}
                style={{ position: "absolute", left: "-9999px" }}
                alt=""
              />
            </div>
          </noscript>
        </>
      )}

      {/* Google Analytics 4 */}
      {GA_ID && (
        <>
          <Script
            src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
            strategy="afterInteractive"
          />
          <Script
            id="ga4-init"
            strategy="afterInteractive"
            dangerouslySetInnerHTML={{
              __html: `
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '${GA_ID}', { anonymize_ip: true });
              `,
            }}
          />
        </>
      )}

      {/* Global click-tracker для автоматического трекинга целей */}
      <Script
        id="auto-track-goals"
        strategy="lazyOnload"
        dangerouslySetInnerHTML={{
          __html: `
(function() {
  function getYmId() {
    ${YM_ID_ONLINE ? `try {
      if (location.hostname && location.hostname.indexOf('podborkns.online') !== -1) return ${YM_ID_ONLINE};
    } catch(_) {}` : ""}
    return ${YM_ID || "null"};
  }
  function track(goal, params) {
    var id = getYmId();
    if (typeof window.ym === 'function' && id) {
      window.ym(id, 'reachGoal', goal, params || {});
    }
    if (typeof window.gtag === 'function') {
      window.gtag('event', goal, params || {});
    }
  }
  document.addEventListener('click', function(e) {
    var t = e.target.closest('a, button');
    if (!t) return;
    var href = (t.getAttribute('href') || '').toLowerCase();
    var label = (t.textContent || '').toLowerCase().trim().slice(0, 50);
    if (href.startsWith('tel:')) return track('phone_click', { number: href.replace('tel:','') });
    if (href.startsWith('mailto:')) return track('email_click', { addr: href.replace('mailto:','') });
    if (href.includes('yoomoney.ru/fundraise')) return track('donate_click');
    if (href.endsWith('.docx') || label.includes('опросный лист') || label.includes('docx')) return track('docx_download');
    if (href.endsWith('.pdf') || label.includes('скачать pdf')) return track('pdf_download');
    if (label.includes('подобрать насос') || label.includes('рассчитать')) return track('calculator_submit');
  }, { passive: true });
})();
          `,
        }}
      />
    </>
  );
}
