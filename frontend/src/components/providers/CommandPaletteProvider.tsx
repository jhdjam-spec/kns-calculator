"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import dynamic from "next/dynamic";

// Lazy-load CommandPalette — он тащит cmdk (~30KB). Не нужно загружать
// при первом рендере главной, только когда пользователь нажмёт Cmd+K
// или клик по кнопке «Поиск».
const CommandPalette = dynamic(
  () => import("@/components/CommandPalette").then((m) => m.CommandPalette),
  { ssr: false },
);

interface Ctx {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
}

const CommandPaletteContext = createContext<Ctx | null>(null);

export function CommandPaletteProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  // Mount lazy-loaded компонент только после первого взаимодействия —
  // экономит initial bundle ~30 KB до того момента, как реально нужен.
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (open && !mounted) setMounted(true);
  }, [open, mounted]);

  // Глобальный Cmd+K shortcut слушаем здесь (не в палитре),
  // чтобы не грузить cmdk до первого нажатия.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (!mounted) setMounted(true);
        setOpen((p) => !p);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mounted]);

  return (
    <CommandPaletteContext.Provider
      value={{
        open,
        setOpen: (v: boolean) => {
          if (v && !mounted) setMounted(true);
          setOpen(v);
        },
        toggle: () => {
          if (!mounted) setMounted(true);
          setOpen((p) => !p);
        },
      }}
    >
      {children}
      {mounted && <CommandPalette open={open} onOpenChange={setOpen} />}
    </CommandPaletteContext.Provider>
  );
}

export function useCommandPalette() {
  const ctx = useContext(CommandPaletteContext);
  if (!ctx) {
    throw new Error("useCommandPalette must be used within CommandPaletteProvider");
  }
  return ctx;
}
