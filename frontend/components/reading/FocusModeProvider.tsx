"use client";

import React, { createContext, useContext, useState } from "react";

/**
 * FocusModeContext — Manages the global state for the immersive reading experience.
 * 
 * When activated, the sidebar collapses, the topbar shrinks and fades, and the 
 * reading column expands to maximize content visibility.
 */

interface FocusModeContextType {
  isFocusMode: boolean;
  toggleFocusMode: () => void;
  setFocusMode: (value: boolean) => void;
}

const FocusModeContext = createContext<FocusModeContextType | undefined>(undefined);

export function useFocusMode() {
  const context = useContext(FocusModeContext);
  if (!context) {
    throw new Error("useFocusMode must be used within a FocusModeProvider");
  }
  return context;
}

export function FocusModeProvider({ children }: { children: React.ReactNode }) {
  const [isFocusMode, setIsFocusMode] = useState(false);

  const toggleFocusMode = () => setIsFocusMode((prev) => !prev);

  return (
    <FocusModeContext.Provider value={{ isFocusMode, toggleFocusMode, setFocusMode: setIsFocusMode }}>
      {children}
    </FocusModeContext.Provider>
  );
}
