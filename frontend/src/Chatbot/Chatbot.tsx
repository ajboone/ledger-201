import TextInput from "./TextInput";
import { chatbotContainerStyles } from "./styles";

export const Chatbot = () => {
  return (
    <div style={chatbotContainerStyles}>
      <TextInput />
    </div>
  );
};

export default Chatbot;
