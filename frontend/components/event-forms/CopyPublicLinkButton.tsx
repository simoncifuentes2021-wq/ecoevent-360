"use client";

import { Copy } from "lucide-react";

import { Button } from "@/components/ui/button";

export function CopyPublicLinkButton({ url, label = "Copiar link" }: { url: string; label?: string }) {
  return (
    <Button size="sm" type="button" variant="secondary" onClick={() => navigator.clipboard.writeText(url)}>
      <Copy className="h-4 w-4" />
      {label}
    </Button>
  );
}
