import { Link } from "wouter";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="text-center">
        <div className="text-eyebrow">404</div>
        <h1 className="mt-1 font-display text-[24px] font-semibold tracking-tight">Page not found</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          That route isn't part of the workspace.
        </p>
        <div className="mt-4">
          <Link href="/">
            <Button>Back to overview</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
