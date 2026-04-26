import Link from "next/link";
import MaterialIcon from "@/components/material-icon";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Action = { label: string; href?: string };

type Props = {
  icon: string;
  title: string;
  description: string;
  actions?: Action[];
};

export default function EmptyState({ icon, title, description, actions }: Props) {
  return (
    <section className="mt-8">
      <div className={cn("border-2 border-dashed border-border rounded-lg p-xl flex flex-col items-center justify-center text-center max-w-md mx-auto")} >
        <MaterialIcon name={icon} size={48} className="text-muted-foreground mb-md" />
        <h3 className="headline-md text-foreground mb-sm">{title}</h3>
        <p className="body-md text-muted-foreground mb-lg">{description}</p>
        {actions && actions.length > 0 && (
          <div className="flex gap-2 flex-wrap justify-center">
            {actions.map((a, idx) => (
              a.href ? (
                <Link key={idx} href={a.href}>
                  <Button variant="default" size="sm" className="label-caps">
                    {a.label}
                  </Button>
                </Link>
              ) : (
                <span key={idx} className={cn("label-caps px-3 py-1 rounded-lg border border-border")}>
                  {a.label}
                </span>
              )
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
