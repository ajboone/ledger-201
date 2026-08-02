type ButtonProps = {
  label: string;
  type?: "button" | "submit" | "reset";
};

export const Button = ({ label, type = "button" }: ButtonProps) => {
  return <button type={type}>{label}</button>;
};

export default Button;
