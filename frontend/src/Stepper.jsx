import {useTranslation} from "react-i18next";

const STEPS = [["form", "1", "stepDetails", "Details"], ["pay", "2", "stepPay", "Payment"], ["sym", "3", "stepSym", "Symptoms"], ["done", "4", "stepToken", "Token"]];

export default function Stepper({step}) {
  const {t} = useTranslation();
  const idx = STEPS.findIndex(s => s[0] === step);
  if (idx < 0) return null;
  return (
    <div className="stepper" role="list" aria-label="Progress">
      {STEPS.map(([k, n, key, def], i) => (
        <div key={k} style={{display: "contents"}}>
          {i > 0 && <div className={"bar" + (i <= idx ? " ok" : "")}><i /></div>}
          <div role="listitem" aria-current={i === idx ? "step" : undefined} className={"st" + (i === idx ? " on" : "") + (i < idx ? " ok" : "")}>
            <span className="dot">{i < idx ? "✓" : n}</span>
            {t(key, {defaultValue: def})}
          </div>
        </div>
      ))}
    </div>
  );
}
