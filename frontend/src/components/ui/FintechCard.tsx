import { motion } from "framer-motion";
import { ReactNode } from "react";

interface FintechCardProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  hover?: boolean;
  glow?: boolean;
}

export function FintechCard({
  children,
  className = "",
  delay = 0,
  hover = true,
  glow = false,
}: FintechCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      className={`glass-card p-5 ${hover ? "hover:border-accent-blue/30 transition-all duration-300" : ""} ${glow ? "animate-pulse-glow" : ""} ${className}`}
    >
      {children}
    </motion.div>
  );
}
