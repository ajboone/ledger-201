import { faCircleUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Button from "../../Button";
import {
  sendButtonStyles,
  sendButtonWrapperStyles,
  textAreaStyles,
  textInputWrapperStyles,
} from "../TextInput/styles";

export const TextInput = () => {
  return (
    <div style={textInputWrapperStyles}>
      <div>
        <textarea
          style={textAreaStyles}
          placeholder="How can Ledger201 help you today...?"
        />
      </div>
      <div style={sendButtonWrapperStyles}>
        <Button
          style={sendButtonStyles}
          label="Send"
          icon={<FontAwesomeIcon icon={faCircleUp} />}
          orientation="right"
        />
      </div>
    </div>
  );
};

export default TextInput;
