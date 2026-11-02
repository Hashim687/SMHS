import {useEffect, useState} from "react";
import QRCode from "qrcode";

export default function Qr({uri, label}) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    let live = true;
    QRCode.toDataURL(uri, {width: 260, margin: 2, errorCorrectionLevel: "M"}).then(u => live && setSrc(u)).catch(() => live && setSrc(""));
    return () => { live = false; };
  }, [uri]);
  if (!src) return null;
  return (
    <figure className="qr">
      <img src={src} width="260" height="260" alt={label} />
      <figcaption>{label}</figcaption>
    </figure>
  );
}
