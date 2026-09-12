import { style } from "@vanilla-extract/css";

export const baseButtonStyles = style({
  all: "unset",
  appearance: "none",
  border: "none",
  cursor: "pointer",
  height: "3rem",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "1.5rem",
  transition: "transform 180ms ease, box-shadow 180ms ease",

  selectors: {
    "&:hover": {
      transform: "translateY(-2px)",
    },
  },
});
