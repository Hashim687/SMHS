import {useEffect, useRef} from "react";

export default function Modal({title, onClose, children, wide}) {
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const k = e => e.key === "Escape" && close.current();
    addEventListener("keydown", k);
    document.body.style.overflow = "hidden";
    return () => { removeEventListener("keydown", k); document.body.style.overflow = ""; };
  }, []);
  return (
    <div className="overlay" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className={"modal" + (wide ? " wide" : "")} role="dialog" aria-modal="true" aria-label={title}>
        <div className="mhead"><h3>{title}</h3><button type="button" className="iconbtn" onClick={onClose} aria-label="Close">✕</button></div>
        <div className="mbody">{children}</div>
      </div>
    </div>
  );
}
