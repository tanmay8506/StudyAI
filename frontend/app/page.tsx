"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { getPaper } from '@/lib/queries';

export default function Home() {
  const [upc, setUpc] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!upc.trim()) return;
    
    setLoading(true);
    setError('');

    try {
      // Check if paper already exists
      const paper = await getPaper(upc.trim());
      
      if (paper) {
        // Pipeline already ran, go to paper
        router.push(`/paper/${upc.trim()}`);
      } else {
        // Trigger the backend pipeline API
        try {
          await fetch('http://localhost:8000/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ upc: upc.trim() })
          });
        } catch (e) {
          console.error("Failed to trigger backend. Ensure FastAPI is running on port 8000.", e);
          // We still route to the pipeline page so the user can see if it was manually triggered
        }
        router.push(`/pipeline/${upc.trim()}`);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred');
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-md w-full">
        <h1 className="text-4xl font-serif font-bold mb-4">StudyAI</h1>
        <p className="text-lg text-muted-foreground mb-12">
          Study notes built from your DU question paper.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="text"
              value={upc}
              onChange={(e) => setUpc(e.target.value)}
              placeholder="Enter your paper code (UPC)"
              className="w-full p-4 border border-border rounded-lg bg-card text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-accent transition-all text-center text-lg uppercase"
              disabled={loading}
              required
            />
            <p className="text-sm text-muted-foreground mt-2 text-left px-1">e.g. MATH1001</p>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <button
            type="submit"
            disabled={loading || !upc.trim()}
            className="w-full flex items-center justify-center gap-2 bg-foreground text-background font-medium p-4 rounded-lg hover:bg-foreground/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Processing...' : 'Generate Notes'}
            {!loading && <ArrowRight className="w-5 h-5" />}
          </button>
        </form>
      </div>
    </main>
  );
}
