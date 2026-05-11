"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { ModeProvider } from "@/components/providers/ModeProvider";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 60_000, retry: 1 },
          mutations: { retry: 1 },
        },
      })
  );

  return (
    <QueryClientProvider client={client}>
      <ModeProvider>{children}</ModeProvider>
    </QueryClientProvider>
  );
}
