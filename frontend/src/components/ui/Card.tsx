import clsx from "clsx";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export default function Card({ children, className, hover = false }: CardProps) {
  return (
    <div
      className={clsx(
        "rounded-2xl border border-border-subtle bg-bg-card/50 p-6",
        hover && "hover:border-border-medium transition-colors",
        className
      )}
    >
      {children}
    </div>
  );
}
