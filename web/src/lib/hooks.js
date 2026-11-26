import { useEffect, useRef } from "preact/hooks";

export function usePolling(fn, ms, deps = []) {
  const saved = useRef(fn);
  saved.current = fn;
  useEffect(() => {
    saved.current();
    const id = setInterval(() => saved.current(), ms);
    return () => clearInterval(id);
  }, deps);
}

export function readLocal(key, initial) {
  try { return localStorage.getItem(key) ?? initial; } catch { return initial; }
}
export function saveLocal(key, value) {
  try { localStorage.setItem(key, value); } catch { /* navigation privée */ }
}
