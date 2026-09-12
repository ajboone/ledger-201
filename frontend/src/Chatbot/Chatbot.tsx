import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import pulseAnimation from "../assets/pulse-green.lottie";
import { typography } from "../typography";
import TextInput from "./TextInput";
import { chatbotContainerStyles, ledgerSpanStyles } from "./styles";

export const Chatbot = () => {
  return (
    <>
      <div style={chatbotContainerStyles}>
        <DotLottieReact
          src={pulseAnimation}
          autoplay
          loop
          style={{
            width: "180px",
            height: "180px",
            pointerEvents: "none",
          }}
        />
        <h2 style={typography.h2}>
          Hey, I'm <span style={ledgerSpanStyles}>ledger</span>. How can I help
          you today?
        </h2>
        <TextInput />
      </div>
    </>
  );
};

export default Chatbot;
