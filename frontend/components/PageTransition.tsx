"use client";

import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { pageFade, pageManifestoToHome } from "@/lib/animations";

export function PageTransition({ children, className }: { children: React.ReactNode, className?: string }) {
  const pathname = usePathname();
  const prevPathRef = useRef<string | null>(null);

  useEffect(() => {
    prevPathRef.current = pathname;
  }, [pathname]);

  const isManifestoToHome = prevPathRef.current === "/manifesto" && pathname === "/";
  const variants = isManifestoToHome ? pageManifestoToHome : pageFade;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        variants={variants}
        initial="initial"
        animate="animate"
        exit="exit"
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
