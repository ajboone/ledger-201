import { textInputStyles } from "../TextInput/styles";

export const TextInput = () => {
  return (
    <input
      style={textInputStyles}
      type="text"
      placeholder="How can Ledger201 help you today?"
    />
  );
};

export default TextInput;
