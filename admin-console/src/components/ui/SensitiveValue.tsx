import React, { useEffect, useMemo, useState } from "react";

export const EyeIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className ?? "h-3 w-3"} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path strokeLinecap="round" strokeLinejoin="round" d="M1.5 12s4-7.5 10.5-7.5S22.5 12 22.5 12s-4 7.5-10.5 7.5S1.5 12 1.5 12Z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

export const EyeOffIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className ?? "h-3 w-3"} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
    <path strokeLinecap="round" strokeLinejoin="round" d="m3 3 18 18M10.477 5.317A9.46 9.46 0 0 1 12 5.25c6.5 0 10.5 6.75 10.5 6.75a17.511 17.511 0 0 1-3.123 4.318M6.228 6.24C2.899 8.37 1.5 12 1.5 12s3.02 5.013 7.989 6.437" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75a3 3 0 0 0 4.5 4.5" />
  </svg>
);

type SensitiveValueProps = {
  value?: string | null;
  maskSuffix?: number;
  className?: string;
  valueClassName?: string;
  buttonClassName?: string;
  labelClassName?: string;
  revealLabel?: string;
  hideLabel?: string;
  revealIcon?: React.ReactNode;
  hideIcon?: React.ReactNode;
  disableHide?: boolean;
};

const maskValue = (value: string, maskSuffix: number): string => {
  if (maskSuffix <= 0) {
    return value;
  }
  const length = value.length;
  if (length <= maskSuffix) {
    return "*".repeat(length);
  }
  const visiblePart = value.slice(0, length - maskSuffix);
  return `${visiblePart}${"*".repeat(maskSuffix)}`;
};

export const SensitiveValue: React.FC<SensitiveValueProps> = ({
  value,
  maskSuffix = 4,
  className,
  valueClassName,
  buttonClassName,
  labelClassName,
  revealLabel = "แสดงข้อมูลเต็ม",
  hideLabel = "ซ่อนข้อมูลเต็ม",
  revealIcon,
  hideIcon,
  disableHide = false
}: SensitiveValueProps) => {
  const [revealed, setRevealed] = useState<boolean>(false);

  useEffect(() => {
    setRevealed(false);
  }, [value]);

  const maskedValue = useMemo(() => {
    if (!value) {
      return "-";
    }
    return maskValue(value, maskSuffix);
  }, [value, maskSuffix]);

  const displayValue = revealed && value ? value : maskedValue;

  if (!value) {
    return <span className={valueClassName}>{"-"}</span>;
  }

  const containerClasses = ["inline-flex items-center gap-2", className].filter(Boolean).join(" ");
  const valueClasses = ["font-mono tracking-wide", valueClassName].filter(Boolean).join(" ");
  const buttonClasses = [
    "inline-flex items-center justify-center gap-1 rounded-full border border-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-100",
    buttonClassName
  ]
    .filter(Boolean)
    .join(" ");

  const handleToggle = () => {
    if (!revealed || !disableHide) {
      setRevealed((current) => (disableHide ? true : !current));
    }
  };

  const effectiveRevealIcon = revealIcon ?? <EyeIcon />;
  const effectiveHideIcon = hideIcon ?? <EyeOffIcon />;
  const showIcon = revealed && !disableHide ? effectiveHideIcon : effectiveRevealIcon;
  const showLabel = revealed && !disableHide ? hideLabel : revealLabel;
  const labelClasses = [labelClassName ?? "sr-only"].filter(Boolean).join(" ");
  const ariaLabel = revealed && !disableHide ? hideLabel : revealLabel;

  return (
    <span className={containerClasses}>
      <span className={valueClasses}>{displayValue}</span>
      <button
        type="button"
        className={buttonClasses}
        onClick={handleToggle}
        aria-pressed={revealed}
        aria-label={ariaLabel}
        title={ariaLabel}
      >
        {showIcon}
        {showLabel ? <span className={labelClasses}>{showLabel}</span> : null}
      </button>
    </span>
  );
};

export default SensitiveValue;
