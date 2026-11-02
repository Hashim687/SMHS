const TAG = {en: "en-IN", ur: "ur-PK", ks: "ur-PK"};

export const canSpeak = () => typeof window !== "undefined" && "speechSynthesis" in window;

export const stop = () => { if (canSpeak()) window.speechSynthesis.cancel(); };

export const speak = (text, lang) => {
  if (!canSpeak() || !text) return;
  const s = window.speechSynthesis;
  s.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = TAG[lang] || "en-IN";
  u.rate = 0.9;
  const v = s.getVoices().find(x => x.lang.toLowerCase().startsWith(u.lang.slice(0, 2)));
  if (v) u.voice = v;
  s.speak(u);
};
