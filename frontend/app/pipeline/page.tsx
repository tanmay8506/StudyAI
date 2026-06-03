"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * /pipeline — Redirects to the demo pipeline.
 * The BottomNav links here; since the real pipeline always has a UPC,
 * we bounce to /pipeline/demo which shows the mock simulation.
 */
export default function PipelineIndexPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/pipeline/demo");
  }, [router]);
  return null;
}
