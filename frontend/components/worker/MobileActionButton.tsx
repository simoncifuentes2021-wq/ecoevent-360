import type { ButtonHTMLAttributes, ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function MobileActionButton({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode }) {
  return <Button className="h-14 w-full text-base" {...props}>{children}</Button>;
}
