import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = Math.max(now.getTime() - date.getTime(), 0)
  const sec = Math.floor(diffMs / 1000)
  const min = Math.floor(sec / 60)
  const hour = Math.floor(min / 60)
  const day = Math.floor(hour / 24)

  if (sec < 60) return `${sec}s ago`
  if (min < 60) return `${min}m ago`
  if (hour < 24) return `${hour}h ago`
  return `${day}d ago`
}
