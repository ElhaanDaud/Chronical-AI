import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-border py-8 px-6 bg-card">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="font-serif font-semibold">Chronicle AI</span>
          <span className="metadata text-muted-foreground">
            © 2024 Chronicle AI. Intelligence Synthesis Platform.
          </span>
        </div>
        <nav className="flex items-center gap-6">
          <Link href="#" className="metadata text-muted-foreground hover:text-foreground transition-colors">
            Ethics Policy
          </Link>
          <Link href="#" className="metadata text-muted-foreground hover:text-foreground transition-colors">
            API Access
          </Link>
          <Link href="#" className="metadata text-muted-foreground hover:text-foreground transition-colors">
            Privacy Ledger
          </Link>
          <Link href="#" className="metadata text-muted-foreground hover:text-foreground transition-colors">
            Terms of Use
          </Link>
        </nav>
      </div>
    </footer>
  );
}
