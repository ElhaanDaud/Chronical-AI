export default function Footer() {
  return (
    <footer className="border-t border-border py-8 px-6 bg-card">
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-2">
        <span className="font-serif font-semibold">Chronicle AI</span>
        <span className="metadata text-muted-foreground">
          © {new Date().getFullYear()} Chronicle AI. Intelligence Synthesis Platform.
        </span>
      </div>
    </footer>
  );
}
