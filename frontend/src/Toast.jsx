import {createContext, useCallback, useContext, useState} from "react";

const Ctx = createContext(() => {});
export const useToast = () => useContext(Ctx);

export function ToastProvider({children}) {
  const [items, setItems] = useState([]);
  const toast = useCallback((msg, type = "ok") => {
    const id = Math.random();
    setItems(l => [...l.slice(-3), {id, msg, type}]);
    setTimeout(() => setItems(l => l.filter(x => x.id !== id)), 4500);
  }, []);
  return (
    <Ctx.Provider value={toast}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map(i => (
          <div key={i.id} className={"toast " + i.type} onClick={() => setItems(l => l.filter(x => x.id !== i.id))}>
            <span>{i.type === "err" ? "⚠️" : "✅"}</span> {i.msg}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
