import type { CSSProperties } from "react";

export const textInputWrapperStyles: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  flex: "0 0 auto",
  padding: "1.25rem",
  borderRadius: "1.25rem",
  width: "100%",
  maxWidth: "48rem",
  border: "8px solid rgba(6, 224, 86, 0.16)",
  boxShadow: "0 0 24px rgba(6, 224, 86, 0.12)",
  backgroundColor: "#fff",
  margin: "0 auto",
};

export const textAreaStyles: CSSProperties = {
  width: "100%",
  minHeight: "5rem",
  border: "none",
  outline: "none",
  resize: "none",
  background: "transparent",
  color: "#17231c",
  font: "inherit",
  lineHeight: 1.5,
};

export const sendButtonWrapperStyles: CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
};

export const sendButtonStyles: CSSProperties = {
  minWidth: "7rem",
  padding: ".65rem 1rem",
  backgroundColor: "var(--green)",
  borderRadius: ".5rem",
  border: "none",
  fontWeight: "500",
  cursor: "pointer",
};
