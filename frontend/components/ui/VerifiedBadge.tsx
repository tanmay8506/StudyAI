import React from 'react';
import { Check, CheckCheck, AlertCircle } from 'lucide-react';

export function VerifiedBadge({ 
  verified, 
  verificationMode, 
  verificationPassed 
}: { 
  verified: boolean; 
  verificationMode: string; 
  verificationPassed: boolean; 
}) {
  if (!verified) return null;

  return (
    <span 
      className="inline-flex items-center text-success ml-2" 
      title={`Mode: ${verificationMode}`}
    >
      {!verificationPassed ? (
        <AlertCircle className="w-4 h-4 text-warning" />
      ) : verificationMode === 'numerical_dual' ? (
        <CheckCheck className="w-4 h-4" />
      ) : (
        <Check className="w-4 h-4" />
      )}
    </span>
  );
}
