import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function SurveysPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Encuestas CSV</h1>
        <p className="text-sm text-muted-foreground">
          Importacion inicial desde Google Forms y Google Sheets.
        </p>
      </div>
      <Card>
        <CardHeader>
          <h2 className="font-semibold">Nueva importacion</h2>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-[1fr_1fr_auto]">
          <Input placeholder="URL de Google Form" />
          <Input type="file" accept=".csv" />
          <Button>
            <Upload className="h-4 w-4" />
            Importar
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

