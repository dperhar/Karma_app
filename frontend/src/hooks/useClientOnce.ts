import { useRef } from 'react';

// Track functions that have been called
const calledFunctions = new WeakMap<Function, boolean>();

export function useClientOnce(fn: () => void): void {
  const fnRef = useRef(fn);
  
  // Only execute if we're on the client and this function hasn't been called before
  if (typeof window !== 'undefined' && !calledFunctions.has(fnRef.current)) {
    // Mark this function as called
    calledFunctions.set(fnRef.current, true);
    
    // Execute the function
    fnRef.current();
  }
}