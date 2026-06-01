import { Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function ReportsPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Reportes PDF</h1>
        <p className="text-sm text-muted-foreground">Generacion de informes para clientes.</p>
      </div>
      <Card>
        <CardHeader>
          <h2 className="font-semibold">Reporte operacional y ambiental</h2>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-medium">Festival Puerto Verde</p>
            <p className="text-sm text-muted-foreground">Incluye residuos, incidencias y CO2e.</p>
          </div>
          <Button>
            <Download className="h-4 w-4" />
            Descargar
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

