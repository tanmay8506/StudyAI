import type { Metadata } from "next";
import { Syne, DM_Mono, Instrument_Serif } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const syne = Syne({ subsets: ["latin"], variable: '--font-sans', weight: ["400", "500", "600", "700", "800"] });
const dmMono = DM_Mono({ subsets: ["latin"], variable: '--font-mono', weight: ["400", "500"] });
const instrumentSerif = Instrument_Serif({ 
  weight: "400", 
  style: ["normal", "italic"], 
  subsets: ["latin"],
  variable: '--font-serif' 
});

export const metadata: Metadata = {
  title: "StudyAI | Spatial Glass",
  description: "Study notes built from your DU question paper, powered by Kinetic Aurora.",
};

import { GrainOverlay } from "@/components/GrainOverlay";
import { BottomNav } from "@/components/BottomNav";
import { PageTransition } from "@/components/PageTransition";


export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${syne.variable} ${dmMono.variable} ${instrumentSerif.variable} font-sans antialiased bg-transparent text-foreground selection:bg-accent/30 selection:text-accent-foreground`}>
        <Providers>

          <BottomNav />
          <PageTransition>
            {children}
          </PageTransition>
        </Providers>
      </body>
    </html>
  );
}