import Button from "../Button";
import TextInput from "../TextInput";
import { chatbotContainerStyles } from "./styles";

export const Chatbot = () => {
  return (
    <div style={chatbotContainerStyles}>
      <TextInput />
      <Button label="Send" />
    </div>
  );
};

export default Chatbot;
