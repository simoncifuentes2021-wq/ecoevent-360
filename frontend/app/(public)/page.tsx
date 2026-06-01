"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  BarChart3,
  Camera,
  CheckCircle2,
  ClipboardList,
  FileText,
  Leaf,
  Recycle,
  Sparkles
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const benefits = [
  { title: "Control operativo", icon: ClipboardList },
  { title: "Evidencias fotográficas", icon: Camera },
  { title: "Gestión de residuos", icon: Recycle },
  { title: "Huella de carbono", icon: Leaf },
  { title: "Encuestas a asistentes", icon: BarChart3 },
  { title: "Reportes profesionales", icon: FileText }
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white">
      <nav className="sticky top-0 z-30 border-b bg-white/88 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <Link className="flex items-center gap-3" href="/">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Leaf className="h-5 w-5" />
            </span>
            <span className="font-bold">EcoEvent 360</span>
          </Link>
          <Link href="/login">
            <Button>Ingresar</Button>
          </Link>
        </div>
      </nav>

      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,#073b3f_0%,#0f766e_48%,#d9f99d_100%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,.28),transparent_32%)]" />
        <div className="relative mx-auto grid min-h-[620px] max-w-7xl items-center gap-10 px-4 py-16 lg:grid-cols-[1.05fr_.95fr]">
          <motion.div
            animate={{ opacity: 1, y: 0 }}
            className="max-w-3xl text-white"
            initial={{ opacity: 0, y: 18 }}
            transition={{ duration: 0.45 }}
          >
            <p className="inline-flex items-center gap-2 rounded-full bg-white/14 px-3 py-1 text-sm font-semibold">
              <Sparkles className="h-4 w-4" />
              Plataforma ambiental para eventos masivos
            </p>
            <h1 className="mt-6 text-5xl font-black tracking-tight md:text-7xl">EcoEvent 360</h1>
            <p className="mt-5 max-w-2xl text-xl text-white/88">
              Gestión ambiental, sanitaria y operativa para eventos sostenibles.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/login">
                <Button className="h-12 bg-white px-6 text-primary hover:bg-white/92">Ingresar</Button>
              </Link>
              <a className="inline-flex h-12 items-center justify-center rounded-md border border-white/30 px-6 text-sm font-semibold text-white transition hover:bg-white/10" href="#como-funciona">
                Ver cómo funciona
              </a>
            </div>
          </motion.div>
          <motion.div
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-lg border border-white/20 bg-white/12 p-4 shadow-soft backdrop-blur"
            initial={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.45, delay: 0.1 }}
          >
            <div className="rounded-lg bg-white p-5">
              <div className="grid gap-3">
                {["Operación en terreno", "Trazabilidad ambiental", "Reporte cliente"].map((item, index) => (
                  <div className="flex items-center gap-3 rounded-md bg-slate-50 p-4" key={item}>
                    <span className="grid h-9 w-9 place-items-center rounded-md bg-emerald-50 text-primary">
                      <CheckCircle2 className="h-5 w-5" />
                    </span>
                    <div>
                      <p className="font-semibold">{item}</p>
                      <p className="text-sm text-muted-foreground">Flujo {index + 1} conectado a datos reales.</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16">
        <div className="grid gap-4 md:grid-cols-3">
          {benefits.map((benefit) => {
            const Icon = benefit.icon;
            return (
              <Card className="border-slate-200" key={benefit.title}>
                <CardContent>
                  <span className="grid h-11 w-11 place-items-center rounded-lg bg-emerald-50 text-primary">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-5 font-bold">{benefit.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Datos ordenados, trazabilidad y acciones claras para equipos y clientes.
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <section className="bg-slate-50 py-16" id="como-funciona">
        <div className="mx-auto max-w-7xl px-4">
          <h2 className="text-3xl font-bold">Cómo funciona</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {["Planifica el evento", "Opera en terreno", "Entrega indicadores"].map((step, index) => (
              <div className="rounded-lg border bg-white p-6" key={step}>
                <span className="text-sm font-bold text-primary">0{index + 1}</span>
                <h3 className="mt-3 text-lg font-bold">{step}</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Coordina clientes, servicios, equipo y evidencias desde una experiencia única.
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
