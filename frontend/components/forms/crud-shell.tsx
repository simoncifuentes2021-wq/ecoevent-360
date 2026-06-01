"use client";

import { motion } from "framer-motion";
import { Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Column, DataTable } from "@/components/ui/table";

type CrudShellProps<T extends Record<string, string | number>> = {
  title: string;
  description: string;
  columns: Column<T>[];
  rows: T[];
};

export function CrudShell<T extends Record<string, string | number>>({
  title,
  description,
  columns,
  rows
}: CrudShellProps<T>) {
  return (
    <motion.div
      className="space-y-5"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        <Button>
          <Plus className="h-4 w-4" />
          Nuevo
        </Button>
      </div>
      <Card>
        <CardContent className="flex flex-col gap-4">
          <div className="relative max-w-md">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input className="pl-9" placeholder="Buscar" />
          </div>
          <div className="overflow-x-auto">
            <DataTable columns={columns} rows={rows} />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

