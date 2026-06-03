"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { fadeUp } from "@/lib/animations";

/**
 * ManifestoCTA — The UPC input form at the bottom of the Manifesto.
 */
interface ManifestoCTAProps {
  onSubmit: (upc: string) => void;
}

export function ManifestoCTA({ onSubmit }: ManifestoCTAProps) {
  const [upc, setUpc] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
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

    setIsSubmitting(true);
    // Let the parent handle the transition and routing
    onSubmit(val);
  };

  return (
    <motion.div
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className="w-full max-w-md flex flex-col items-center"
    >
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 w-full">
        <div className="relative flex-1">
          <input
            type="text"
            value={upc}
            onChange={(e) => setUpc(e.target.value)}
            placeholder="Paper code — e.g. 2352203601"
            className="input-underline w-full"
            data-cursor="input"
            disabled={isSubmitting}
          />
        </div>
        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary whitespace-nowrap"
          data-cursor="hover"
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-bg-base border-t-transparent rounded-full animate-spin" />
              Generating...
            </span>
          ) : (
            "Generate →"
          )}
        </button>
      </form>

      {/* Error Message */}
      <div className="h-6 mt-2 w-full text-center">
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-[12px] font-sans text-red"
          >
            {error}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
