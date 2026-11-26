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
  return items.map((t) => <div class="toast" key={t.id}>{t.msg}</div>);
}
