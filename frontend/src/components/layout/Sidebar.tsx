"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart2, GitCompare, HeartPulse, FlaskConical } from "lucide-react";
import { clsx } from "clsx";

const navItems = [
  { name: "Live Trading", href: "/", icon: Activity },
  { name: "Model Studio", href: "/train", icon: FlaskConical },
  { name: "Backtests", href: "/backtests", icon: BarChart2 },
  { name: "Compare", href: "/compare", icon: GitCompare },
  { name: "Pipeline Health", href: "/health", icon: HeartPulse },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-16 md:w-64 flex flex-col h-full bg-[var(--color-surface)] border-r border-[var(--color-hairline)]">
      <div className="h-14 flex items-center justify-center md:justify-start md:px-6 border-b border-[var(--color-hairline)]">
        <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center font-bold text-white shadow-sm">N</div>
        <span className="hidden md:block ml-3 font-semibold text-[var(--color-primary)] tracking-wide">NIFTY AI</span>
      </div>
      
      <nav className="flex-1 py-4 flex flex-col gap-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                "flex items-center justify-center md:justify-start h-12 mx-2 px-0 md:px-4 rounded-md transition-colors",
                isActive 
                  ? "bg-[var(--color-panel)] text-[var(--color-primary)] border border-[var(--color-subtle)]" 
                  : "text-[var(--color-muted)] hover:text-[var(--color-primary)] hover:bg-[var(--color-panel)] border border-transparent"
              )}
              title={item.name}
            >
              <item.icon className="w-5 h-5" />
              <span className="hidden md:block ml-3 text-sm font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
