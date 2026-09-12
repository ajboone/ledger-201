import type { CSSProperties, ReactNode } from "react";
import { baseButtonStyles } from "./styles.css.ts";

type ButtonProps = {
  label: string;
  type?: "button" | "submit" | "reset";
  style?: CSSProperties;
  icon?: ReactNode;
  orientation?: "left" | "right";
  className?: string;
};

export const Button = ({
  label,
  type = "button",
  style,
  icon,
  orientation = "left",
}: ButtonProps) => {
  return (
    <>
      <button type={type} className={baseButtonStyles} style={style}>
        {orientation === "left" && icon}
        <span>{label}</span>
        {orientation === "right" && icon}
      </button>
    </>
  );
};

export default Button;
