"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Layers, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { springNavEntrance } from "@/lib/animations";
import { ThemeToggle } from "@/components/ThemeToggle";

const navItems = [
  { name: "Home",      path: "/",          icon: Home     },
  { name: "Pipeline",  path: "/pipeline",  icon: Layers   },
  { name: "Workspace", path: "/paper/demo",icon: BookOpen },
];

export function BottomNav() {
  const pathname = usePathname();
  if (!pathname) return null;

  return (
    <motion.div
      initial={{ y: 50, opacity: 0, x: "-50%" }}
      animate={{ y: 0,  opacity: 1, x: "-50%" }}
      transition={springNavEntrance}
      className="fixed bottom-[24px] left-1/2 z-[100] flex items-center"
    >
      <div
        className="flex items-center gap-1 shadow-[0_8px_32px_rgba(0,0,0,0.2)] backdrop-blur-md"
        style={{
          backgroundColor: "var(--bg-raised)",
          border:          "1px solid var(--border-subtle)",
          borderRadius:    "var(--r-full)",
          padding:         "6px 8px",
          transition:      "background-color 0.35s ease, border-color 0.35s ease",
        }}
      >
        {navItems.map((item) => {
          const isActive =
            item.path === "/"
              ? pathname === "/"
              : pathname.startsWith(item.path) ||
                (item.name === "Workspace" && pathname.startsWith("/reading"));

          return (
            <Link
              key={item.path}
              href={item.path}
              className={cn(
                "relative flex items-center gap-2 px-4 py-1.5 rounded-full transition-colors duration-150",
                isActive
                  ? "text-accent"
                  : "text-text-tertiary hover:text-text-primary"
              )}
              style={{ color: isActive ? "var(--accent)" : undefined }}
            >
              {isActive && (
                <motion.div
                  layoutId="bottom-nav-indicator"
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: "var(--accent)" }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                />
              )}
              <item.icon className="w-3.5 h-3.5" />
              <span className="font-sans text-[11px] font-bold uppercase tracking-widest leading-none">
                {item.name}
              </span>
            </Link>
          );
        })}

        {/* Divider */}
        <div
          style={{
            width:           1,
            height:          20,
            backgroundColor: "var(--border-default)",
            marginLeft:      4,
            marginRight:     4,
            flexShrink:      0,
          }}
        />

        {/* Theme Toggle */}
        <ThemeToggle />
      </div>
    </motion.div>
  );
}
