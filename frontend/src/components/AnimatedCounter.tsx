"use client";

import { useEffect, useState } from "react";
import { motion, animate } from "framer-motion";

interface AnimatedCounterProps {
  from?: number;
  to: number;
  suffix?: string;
  decimals?: number;
  duration?: number;
  className?: string;
}

export default function AnimatedCounter({
  from = 0,
  to,
  suffix = "",
  decimals = 0,
  duration = 1.2,
  className = "",
}: AnimatedCounterProps) {
  const [display, setDisplay] = useState(from.toFixed(decimals));

  useEffect(() => {
    const controls = animate(from, to, {
      duration,
      ease: "easeOut",
      onUpdate: (v) => {
        setDisplay(v.toFixed(decimals));
      },
    });
    return controls.stop;
  }, [from, to, decimals, duration]);

  return (
    <motion.span
      key={`${to}-${decimals}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={className}
    >
      {display}
      {suffix}
    </motion.span>
  );
}
