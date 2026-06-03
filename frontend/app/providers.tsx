"use client";

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { ReactLenis, useLenis } from 'lenis/react';
import { useAnimationFrame } from 'framer-motion';
import { ThemeProvider } from 'next-themes';

function LenisSync() {
  const lenis = useLenis();
  useAnimationFrame((time) => {
    lenis?.raf(time);
  });
  return null;
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
      },
    },
  }));

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      disableTransitionOnChange={false}
    >
      <ReactLenis root autoRaf={false} options={{ lerp: 0.08, duration: 1.5, smoothWheel: true }}>
        <LenisSync />
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </ReactLenis>
    </ThemeProvider>
  );
}
