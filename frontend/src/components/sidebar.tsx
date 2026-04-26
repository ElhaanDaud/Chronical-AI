"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import MaterialIcon from "@/components/material-icon";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Home Feed", href: "/", icon: "newspaper" },
  { label: "Search", href: "/search", icon: "search" },
];

type SidebarProps = {
  isOpen?: boolean;
  onClose?: () => void;
};

function SidebarContent() {
  const pathname = usePathname();

  return (
    <nav className="flex-1 flex flex-col h-full">
      <div className="p-6 border-b border-border">
        <div className="font-serif text-xl font-semibold">Intelligence Hub</div>
        <p className="text-muted-foreground text-[10px] uppercase tracking-widest mt-1">
          Global Monitoring Active
        </p>
      </div>

      <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname === item.href;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "flex items-center gap-4 px-6 py-4 transition-all duration-200",
                isActive
                  ? "bg-accent border-l-[3px] border-secondary text-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <MaterialIcon name={item.icon} />
              <span className="text-sm font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>

      <div className="border-t border-border p-6 mt-auto">
        <p className="text-muted-foreground text-[10px] tracking-widest uppercase">
          Chronicle AI
        </p>
      </div>
    </nav>
  );
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  return (
    <>
      <aside className="hidden md:flex fixed left-0 top-16 bottom-0 w-64 border-r border-border bg-card z-40 flex-col">
        <SidebarContent />
      </aside>

      {isOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 z-50 bg-black/30"
            onClick={onClose}
          />
          <aside className="md:hidden fixed left-0 top-0 bottom-0 w-64 bg-card border-r border-border z-50 flex flex-col">
            <SidebarContent />
          </aside>
        </>
      )}
    </>
  );
}
