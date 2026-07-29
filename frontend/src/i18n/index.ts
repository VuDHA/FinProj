// ---------------------------------------------------------------------------
// react-i18next configuration (Vietnamese only).
//
// This module is self-initializing: simply importing it anywhere will boot
// i18next with the Vietnamese resource bundle. The app entry point
// (`src/main.tsx`) should add the following side-effect import near the top:
//
//     import "./i18n";
//
// (That line is intentionally NOT added here to main.tsx because main.tsx is
// owned by another agent — see the task notes.)
// ---------------------------------------------------------------------------

import i18n, { type InitOptions } from "i18next";
import { initReactI18next } from "react-i18next";

import { vi, formatCurrency, formatNumber, formatPercent, formatDate } from "./vi";

const initOptions: InitOptions = {
  lng: "vi",
  fallbackLng: "vi",
  resources: {
    vi: {
      translation: vi,
    },
  },
  interpolation: {
    escapeValue: false,
  },
};

i18n.use(initReactI18next).init(initOptions);

// Register custom Vietnamese formatters so `{{value, formatCurrency}}`,
// `{{value, formatNumber}}`, `{{value, formatPercent}}` and
// `{{value, formatDate}}` work inside t() interpolation calls.
i18n.services.formatter?.add("formatCurrency", (value) => formatCurrency(Number(value)));
i18n.services.formatter?.add("formatNumber", (value) => formatNumber(Number(value)));
i18n.services.formatter?.add("formatPercent", (value) => formatPercent(Number(value)));
i18n.services.formatter?.add("formatDate", (value) => formatDate(value as string | number | Date));

export default i18n;
