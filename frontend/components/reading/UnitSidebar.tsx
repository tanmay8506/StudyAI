"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useFocusMode } from "./FocusModeProvider";
import { TierBadge } from "../overview/TierBadge"; // Reusing the compact badge logic if needed
import { useIsMobile } from "@/lib/hooks/useMediaQuery";

/**
 * UnitSidebar — The 220px topic navigation strip.
 * 
 * Implements the Focus Mode collapsed state (20px wide) displaying only
 * the vertical stack of priority dots, which expands on hover.
 */

export interface TopicData {
  id: string;
  name: string;
  studyTime: string;
  priority: "high" | "medium" | "low" | "none";
  isActive?: boolean;
}

interface UnitSidebarProps {
  paperName: string;
  tier: 1 | 2 | 3 | 4;
  topics: TopicData[];
  onTopicSelect?: (id: string) => void;
}

export function UnitSidebar({ paperName, tier, topics, onTopicSelect }: UnitSidebarProps) {
  const { isFocusMode } = useFocusMode();
  const [isHovered, setIsHovered] = useState(false);
  const isMobile = useIsMobile();

  // If in focus mode, and not hovering over the 20px strip, we are collapsed.
  const isCollapsed = isFocusMode && !isHovered;

  const getDotColor = (priority: string) => {
    switch (priority) {
      case "high": return "bg-red";
      case "medium": return "bg-accent";
      case "low": return "bg-text-tertiary";
      default: return "bg-border-subtle";
    }
  };

  return (
    <motion.div
      // On mobile: fixed bottom sheet. On desktop: side panel.
      animate={
        isMobile 
          ? { height: isCollapsed ? 60 : 320, width: "100%" }
          : { width: isCollapsed ? 20 : 220, height: "100vh" }
      }
      transition={{ type: "spring", stiffness: 200, damping: 25 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`bg-bg-raised border-border-subtle overflow-y-auto overflow-x-hidden flex-shrink-0 z-40 scrollbar-none ${
        isMobile ? "fixed bottom-0 left-0 right-0 border-t rounded-t-xl" : "h-screen border-r relative"
      }`}
    >
      {/* SIDEBAR HEADER */}
      <motion.div 
        animate={{ opacity: isCollapsed ? 0 : 1 }}
        transition={{ duration: 0.2 }}
        className="p-[20px_16px_16px] border-b border-border-subtle flex flex-col gap-2 whitespace-nowrap"
      >
        <div className="font-sans text-[10px] uppercase text-text-tertiary tracking-widest">
          StudyAI
        </div>
        <div className="font-serif text-[15px] text-text-primary truncate">
          {paperName}
        </div>
        {/* Render a simple compact tier badge for the sidebar */}
        <div className="font-mono text-[10px] text-text-tertiary uppercase mt-1">
          Tier {tier} Paper
        </div>
      </motion.div>

      {/* TOPIC NAVIGATION */}
      <motion.div 
        animate={{ opacity: isCollapsed ? 0 : 1 }}
        transition={{ duration: 0.2 }}
        className="p-4 font-sans text-[10px] uppercase text-text-tertiary tracking-widest whitespace-nowrap"
      >
        Unit Topics
      </motion.div>

      <div className="flex flex-col relative w-full">
        {topics.map((topic, i) => (
          <div
            key={topic.id}
            onClick={() => onTopicSelect?.(topic.id)}
            className="relative cursor-pointer group"
          >
            {/* Active Border */}
            {topic.isActive && !isCollapsed && (
              <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-accent" />
            )}

            <motion.div
              // Background changes on active or hover
              className={`flex items-center p-[7px_16px] transition-colors duration-150 ${
                topic.isActive && !isCollapsed
                  ? "bg-accent-dim" 
                  : "group-hover:bg-bg-card"
              }`}
              // When collapsed, we center the dot in the 20px strip (padding left approx 7px)
              animate={
                isMobile
                  ? { paddingLeft: 16, paddingRight: 16 }
                  : { paddingLeft: isCollapsed ? 7 : 16, paddingRight: isCollapsed ? 7 : 16 }
              }
              transition={{ type: "spring", stiffness: 200, damping: 25 }}
            >
              {/* Priority Dot */}
              <motion.div
                className={`rounded-full flex-shrink-0 ${getDotColor(topic.priority)}`}
                // Base size is 6px, expands to 8px on hover
                initial={{ width: 6, height: 6 }}
                whileHover={{ width: 8, height: 8 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
              />

              {/* Text Content - Fades out when collapsed */}
              <motion.div
                animate={{ opacity: isCollapsed ? 0 : 1 }}
                className="flex flex-row flex-1 items-center justify-between ml-3 overflow-hidden whitespace-nowrap gap-2"
              >
                <span className={`font-sans text-[12px] truncate ${
                  topic.isActive ? "text-accent font-bold" : "text-text-secondary"
                }`}>
                  {topic.name}
                </span>
                <span className="font-mono text-[10px] text-text-tertiary flex-shrink-0">
                  {topic.studyTime}
                </span>
              </motion.div>
            </motion.div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
