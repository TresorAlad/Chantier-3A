import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Full-screen loading state (auth gate, route-level suspense). Keeps its
 * original no-props API — every current call site renders it bare — while
 * picking up the shared motion/elevation language.
 */
export const Spinner = ({ className, label = "Loading" }: { className?: string; label?: string }) => {
  return (
    <div className="fixed inset-0 z-40 flex animate-fade-in items-center justify-center bg-background/60 backdrop-blur-sm" role="status" aria-live="polite">
      <Loader2 className={cn("h-10 w-10 text-primary-emphasis motion-safe:animate-spin", className)} aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </div>
  );
};