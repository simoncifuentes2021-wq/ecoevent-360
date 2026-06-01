export type FilterOption = {
  label: string;
  value: string;
};

export function FilterSelect({
  value,
  onChange,
  options,
  label
}: {
  value: string;
  onChange: (value: string) => void;
  options: FilterOption[];
  label: string;
}) {
  return (
    <label className="grid gap-1 text-xs font-semibold uppercase text-muted-foreground">
      {label}
      <select
        className="h-10 rounded-md border bg-white px-3 text-sm font-medium normal-case text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
