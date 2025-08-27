import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { getTypeNames } from './api';

/* eslint-disable react-refresh/only-export-components */

const TypeNameContext = createContext<Record<number, string>>({});

export function TypeNameProvider({ children }: { children: ReactNode }) {
  const [names, setNames] = useState<Record<number, string>>({});

  useEffect(() => {
    getTypeNames([])
      .then(setNames)
      .catch(() => {
        // ignore errors; fall back to type IDs
      });
  }, []);

  return (
    <TypeNameContext.Provider value={names}>
      {children}
    </TypeNameContext.Provider>
  );
}

export function useTypeNames(): Record<number, string> {
  return useContext(TypeNameContext);
}

export function useTypeName(id: number): string {
  const names = useTypeNames();
  return names[id] || String(id);
}
