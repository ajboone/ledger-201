import type { CSSProperties } from "react";

export const textInputWrapperStyles: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  padding: "2rem",
  marginTop: "9rem",
  borderRadius: "2rem",
  width: "75%",
  border: "15px solid rgba(6, 224, 86, 0.2)",
  boxShadow: "0 0 24px rgba(6, 224, 86, 0.18)",
  backgroundColor: "#fff",
};

export const textAreaStyles: CSSProperties = {
  width: "100%",
  height: "5rem",
  border: "none",
  outline: "none",
  resize: "none",
};

export const sendButtonWrapperStyles: CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
};

export const sendButtonStyles: CSSProperties = {
  width: "8rem",
  backgroundColor: "var(--green)",
  borderRadius: ".5rem",
  fontWeight: "500",
  cursor: "pointer",
};
