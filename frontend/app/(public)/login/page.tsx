import Link from "next/link";
import { Leaf } from "lucide-react";

import { LoginForm } from "@/components/auth/LoginForm";
import { Card, CardContent } from "@/components/ui/card";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen grid-cols-1 bg-background lg:grid-cols-[1fr_.95fr]">
      <section className="flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-md space-y-7">
          <Link className="flex items-center gap-3" href="/">
            <span className="grid h-11 w-11 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Leaf className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-xl font-bold">EcoEvent 360</h1>
              <p className="text-sm text-muted-foreground">Acceso seguro a la plataforma</p>
            </div>
          </Link>
          <Card className="shadow-soft">
            <CardContent className="space-y-5">
              <div>
                <h2 className="text-2xl font-bold">Ingresar</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Usa tus credenciales para continuar a tu panel.
                </p>
              </div>
              <LoginForm />
            </CardContent>
          </Card>
        </div>
      </section>
      <section className="hidden bg-[linear-gradient(135deg,#073b3f_0%,#0f766e_54%,#d9f99d_120%)] p-10 text-white lg:flex lg:items-end">
        <div className="max-w-xl space-y-4">
          <p className="text-sm font-semibold uppercase tracking-[0.2em]">SaaS operacional</p>
          <h2 className="text-5xl font-bold">Datos ambientales confiables para eventos sostenibles.</h2>
          <p className="text-base text-white/82">
            Gestiona operación, evidencias, residuos, carbono y reportes desde un solo lugar.
          </p>
        </div>
      </section>
    </main>
  );
}
