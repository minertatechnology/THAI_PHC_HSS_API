import React, { forwardRef, useState } from "react";

export interface PasswordInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  containerClassName?: string;
  inputClassName?: string;
}

const EyeOpenIcon: React.FC = () => (
  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z" />
  </svg>
);

const EyeClosedIcon: React.FC = () => (
  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 3l18 18" />
    <path d="M10.73 6.08A9.945 9.945 0 0 1 12 6c4.478 0 8.268 2.943 9.542 7-.46 1.466-1.27 2.785-2.34 3.864" />
    <path d="M6.16 6.17C4.28 7.6 2.96 9.62 2.458 12c.666 2.119 1.967 3.952 3.663 5.227" />
    <path d="M9.88 9.9a3 3 0 0 1 4.23 4.23" />
    <path d="M14.12 14.12A3 3 0 0 1 9.88 9.9" />
  </svg>
);

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>((props, ref) => {
  const { containerClassName = "", inputClassName, className, ...rest } = props;
  const [isVisible, setIsVisible] = useState(false);
  const toggle = () => setIsVisible((prev) => !prev);
  const combinedInputClassName = [inputClassName ?? className ?? "", "pr-12"].filter(Boolean).join(" ").trim();
  return (
    <div className={["relative", containerClassName].filter(Boolean).join(" ").trim()}>
      <input
        ref={ref}
        {...rest}
        type={isVisible ? "text" : "password"}
        className={combinedInputClassName}
      />
      <button
        type="button"
        onClick={toggle}
        className="absolute inset-y-0 right-0 flex items-center px-3 text-slate-400 transition hover:text-slate-600 focus:text-slate-600 focus:outline-none"
        aria-label={isVisible ? "ซ่อนรหัสผ่าน" : "แสดงรหัสผ่าน"}
        aria-pressed={isVisible}
      >
        {isVisible ? <EyeOpenIcon /> : <EyeClosedIcon />}
      </button>
    </div>
  );
});

PasswordInput.displayName = "PasswordInput";

export default PasswordInput;
