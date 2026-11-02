export const pick = (o, lang, key = "name") => [o[key + "_" + lang], lang === "ks" && o[key + "_ur"], o[key + "_en"]].find(Boolean) || "";
