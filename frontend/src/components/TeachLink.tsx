"use client";

import { useRouter } from "next/navigation";
import { useCallback, type AnchorHTMLAttributes, type ReactNode } from "react";

interface Props extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  href: string;
  children: ReactNode;
}

/**
 * Ссылка с поддержкой View Transitions API (Chrome 111+, Safari 18+, FF 130+).
 * Для браузеров без поддержки — обычный router.push без эффекта.
 * Уважает prefers-reduced-motion: в этом режиме переход без анимации.
 *
 * Используется внутри /teach/* — гладкий cross-fade между разделами
 * справочника, ощущение «бумажной книги», а не SPA-jank.
 */
export function TeachLink({ href, children, onClick, ...rest }: Props) {
  const router = useRouter();

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>) => {
      onClick?.(e);
      if (e.defaultPrevented) return;
      // Не перехватываем ctrl/cmd-click и middle-click (новая вкладка)
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
      e.preventDefault();

      // 1) Сразу запускаем навигацию — Next App Router начнёт prefetch+commit,
      //    URL обновится. Это гарантирует переход даже если View Transitions
      //    fail/blocked/не успели.
      router.push(href);

      // 2) Параллельно (best-effort) запускаем View Transition для cross-fade
      //    эффекта. Это работает только если браузер поддерживает API и юзер
      //    не выставил prefers-reduced-motion. Промахивается тихо.
      try {
        const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const viewTransition = (document as Document & {
          startViewTransition?: (cb: () => void | Promise<void>) => { finished: Promise<void> };
        }).startViewTransition;
        if (typeof viewTransition === "function" && !reduceMotion) {
          viewTransition(() => {});
        }
      } catch {
        // View Transitions API не критичен — игнорируем
      }
    },
    [router, href, onClick],
  );

  return (
    <a href={href} onClick={handleClick} {...rest}>
      {children}
    </a>
  );
}
