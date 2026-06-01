import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

export function SearchInput({
  value,
  onChange,
  placeholder = "Buscar..."
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
      <Input className="pl-9" onChange={(event) => onChange(event.target.value)} placeholder={placeholder} value={value} />
    </div>
  );
}
