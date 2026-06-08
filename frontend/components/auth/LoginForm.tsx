"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Lock, Mail } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { AuthErrorAlert } from "@/components/auth/AuthErrorAlert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

const loginSchema = z.object({
  email: z.string().email("Ingresa un email valido"),
  password: z.string().min(1, "La contraseña es obligatoria")
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginForm() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting }
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" }
  });

  async function onSubmit(values: LoginValues) {
    setError(null);
    try {
      await login(values);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Email o contraseña incorrectos.");
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Tu usuario esta inactivo o no tiene permisos.");
      } else {
        setError("No pudimos iniciar sesion. Revisa la conexion con la API.");
      }
    }
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
      {error ? <AuthErrorAlert message={error} /> : null}
      <label className="grid gap-2 text-sm font-medium">
        Email
        <div className="relative">
          <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="admin@ecoevent.cl" type="email" {...register("email")} />
        </div>
        {errors.email ? <span className="text-xs text-rose-600">{errors.email.message}</span> : null}
      </label>
      <label className="grid gap-2 text-sm font-medium">
        Contraseña
        <div className="relative">
          <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Contraseña" type="password" {...register("password")} />
        </div>
        {errors.password ? <span className="text-xs text-rose-600">{errors.password.message}</span> : null}
      </label>
      <Button className="w-full" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Ingresando..." : "Ingresar"}
      </Button>
    </form>
  );
}
