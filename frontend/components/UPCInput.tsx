"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fadeUp, transitionInputBase, springInputSubmit, springSnappy } from "@/lib/animations";

/**
 * UPCInput — The primary entry point.
 * 
 * Underline style only. No border, no background, no card wrapper.
 * Communicates focus state back up to the page to trigger ZAxisText blur.
 */

interface UPCInputProps {
  onFocusChange: (isFocused: boolean) => void;
  onSubmit: (upc: string) => Promise<void>;
}

export function UPCInput({ onFocusChange, onSubmit }: UPCInputProps) {
  const [upc, setUpc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const val = upc.trim();
    if (!val) {
      setError("Please enter a paper code");
      return;
    }
    if (!/^\d+$/.test(val)) {
      setError("Numeric characters only");
      return;
    }
    if (val.length !== 10) {
      setError("Must be exactly 10 digits");
      return;
    }

    setLoading(true);
    try {
      await onSubmit(val);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      // If we route away, component unmounts. If error, stop loading.
      setLoading(false);
    }
  };

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      animate="visible"
      // Fades up 620ms after page load per sequence
      transition={transitionInputBase}
      className="w-full flex flex-col items-center mt-6"
    >
      <form onSubmit={handleSubmit} className="flex flex-row items-center gap-3">
        <input
          type="text"
          value={upc}
          onChange={(e) => setUpc(e.target.value)}
          onFocus={() => onFocusChange(true)}
          onBlur={() => onFocusChange(false)}
          placeholder="Paper code — e.g. 2352203601"
          className="bg-transparent border-0 border-b border-solid border-border-default px-0 py-3 font-sans text-[16px] text-text-primary placeholder:text-text-tertiary w-[320px] focus:outline-none focus:border-accent transition-colors duration-150"
          data-cursor="input"
          disabled={loading}
        />
        
        <motion.button
          type="submit"
          disabled={loading}
          whileHover={{ scale: 1.02 }}
          transition={springInputSubmit}
          className="font-sans font-bold text-[14px] bg-accent text-bg-base rounded-lg px-6 py-3 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed hover:bg-accent-2 transition-colors duration-150"
          data-cursor="hover"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-bg-base border-t-transparent rounded-full animate-spin" />
              Generating...
            </span>
          ) : (
            "Generate →"
          )}
        </motion.button>
      </form>

      {/* Validation Error */}
      <div className="h-6 mt-2 w-full text-center">
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={springSnappy}
              className="text-[12px] font-sans text-red"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
