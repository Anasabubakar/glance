import clsx from "clsx";

interface BadgeProps {
  variant?: "default" | "indigo" | "green" | "orange" | "violet";
  children: React.ReactNode;
  className?: string;
}

export default function Badge({
  variant = "default",
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        {
          "bg-bg-elevated text-text-muted border border-border-subtle":
            variant === "default",
          "bg-indigo/10 text-indigo border border-indigo/20":
            variant === "indigo",
          "bg-green/10 text-green border border-green/20": variant === "green",
          "bg-orange/10 text-orange border border-orange/20":
            variant === "orange",
          "bg-violet/10 text-violet border border-violet/20":
            variant === "violet",
        },
        className
      )}
    >
      {children}
    </span>
  );
}
