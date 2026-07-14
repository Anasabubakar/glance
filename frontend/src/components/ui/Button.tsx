import clsx from "clsx";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

export default function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center font-medium rounded-xl transition-all",
        {
          "bg-gradient-brand text-white hover:opacity-90 glow-brand":
            variant === "primary",
          "border border-border-medium text-text-muted hover:text-text-primary hover:border-text-muted":
            variant === "secondary",
          "text-text-muted hover:text-text-primary": variant === "ghost",
        },
        {
          "px-3 py-1.5 text-xs gap-1.5": size === "sm",
          "px-5 py-2.5 text-sm gap-2": size === "md",
          "px-8 py-3.5 text-base gap-2.5": size === "lg",
        },
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
