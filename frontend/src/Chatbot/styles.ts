import type { CSSProperties } from "react";

export const chatbotContainerStyles: CSSProperties = {
  width: "80%",
  height: "100%",
  padding: "2rem",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "1rem",
  background:
    "linear-gradient(146deg,rgba(243, 243, 243, 1) 76%, rgba(192, 239, 210, 1) 96%, rgba(151, 236, 183, 1) 98%, rgba(88, 231, 141, 1) 100%)",
  borderRadius: "2rem",
};

export const ledgerSpanStyles: CSSProperties = {
  color: "var(--green)",
  display: "inline-block",
  animation: "ledgerFadeUp 700ms ease-out both",
};
