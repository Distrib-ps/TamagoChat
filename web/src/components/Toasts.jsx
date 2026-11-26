import { useEffect, useState } from "preact/hooks";

let push = () => {};
export const toast = (msg) => push(msg);

export function Toasts() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    let n = 0;
    push = (msg) => {
      const id = ++n;
      setItems((list) => [...list, { id, msg }]);
      setTimeout(() => setItems((list) => list.filter((t) => t.id !== id)), 2600);
    };
  }, []);
  return (
    <div class="pointer-events-none fixed inset-x-0 bottom-5 z-20 flex flex-col items-center gap-2 px-4" role="status">
      {items.map((t) => (
        <div key={t.id} class="animate-rise rounded-chip border-2 border-line bg-ink px-4 py-2 text-sm font-bold text-paper shadow-sticker-sm">
          {t.msg}
        </div>
      ))}
    </div>
  );
}
