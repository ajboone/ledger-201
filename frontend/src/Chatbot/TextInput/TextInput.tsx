import type { FormEvent } from "react";
import { faCircleUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  sendButtonStyles,
  sendButtonWrapperStyles,
  textAreaStyles,
  textInputWrapperStyles,
} from "../TextInput/styles";

interface TextInputProps {
  value: string;
  disabled: boolean;
  isSubmitting: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export const TextInput = ({
  value,
  disabled,
  isSubmitting,
  onChange,
  onSubmit,
}: TextInputProps) => {
  return (
    <form onSubmit={onSubmit} style={textInputWrapperStyles}>
      <div>
        <textarea
          aria-label="Ask Ledger a question"
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (!disabled && !isSubmitting && value.trim()) {
                event.currentTarget.form?.requestSubmit();
              }
            }
          }}
          style={textAreaStyles}
          value={value}
          placeholder="Ask about sales, refunds, reconciliation, or top items..."
        />
      </div>
      <div style={sendButtonWrapperStyles}>
        <button
          disabled={disabled || !value.trim()}
          style={sendButtonStyles}
          type="submit"
        >
          {isSubmitting ? "Checking..." : "Send"}{" "}
          <FontAwesomeIcon icon={faCircleUp} />
        </button>
      </div>
    </form>
  );
};

export default TextInput;
