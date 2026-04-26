"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import MaterialIcon from "@/components/material-icon";
import { cn } from "@/lib/utils";
export default function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const currentTheme = mounted
    ? (theme === "dark" || resolvedTheme === "dark" ? "dark" : "light")
    : "light";

  const nextTheme = currentTheme === "dark" ? "light" : "dark";
  const iconName = currentTheme === "dark" ? "light_mode" : "dark_mode";

  return (
    <button
      aria-label={`Switch to ${nextTheme} theme`}
      className={cn(
        "relative inline-flex items-center justify-center rounded-full p-2 transition-colors duration-150 hover:bg-accent"
      )}
      onClick={() => setTheme(nextTheme)}
      title={`Theme: ${currentTheme}`}
    >
      <MaterialIcon name={iconName} />
    </button>
  );
}
