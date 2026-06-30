"use client";

import { useEffect, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/common/ErrorState";
import { FormActions } from "@/components/common/FormActions";
import { ClientSelect } from "@/components/users/ClientSelect";
import { RoleSelect } from "@/components/users/RoleSelect";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import type { Client } from "@/types/client";
import type { User, UserCreate, UserUpdate } from "@/types/user";
import type { UserRole } from "@/types/roles";

const schema = z
  .object({
    full_name: z.string().min(1, "El nombre es obligatorio"),
    email: z.string().email("Email inválido"),
    phone: z.string().optional(),
    password: z.string().optional(),
    role: z.enum(["SUPER_ADMIN", "ADMIN", "CLIENT", "SUPERVISOR", "LOGISTICS_OPERATOR", "WORKER"]),
    client_id: z.string().optional(),
    is_active: z.boolean().optional()
  })
  .superRefine((data, ctx) => {
    if (data.role === "CLIENT" && !data.client_id) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "El cliente es obligatorio", path: ["client_id"] });
    }
  });

type Values = z.infer<typeof schema>;

export function UserForm({
  initialData,
  user,
  clients,
  currentRole,
  onSubmit,
  cancelHref,
  submitLabel
}: {
  initialData?: User;
  user?: User;
  clients: Client[];
  currentRole: UserRole;
  onSubmit: (data: UserCreate | UserUpdate) => Promise<void>;
  cancelHref: string;
  submitLabel?: string;
}) {
  const [apiError, setApiError] = useState<string | null>(null);
  const formData = initialData || user;
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting }
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      full_name: formData?.full_name ?? "",
      email: formData?.email ?? "",
      phone: formData?.phone ?? "",
      password: "",
      role: formData?.role ?? "WORKER",
      client_id: formData?.client_id ?? "",
      is_active: formData?.is_active ?? true
    }
  });
  const role = watch("role");

  useEffect(() => {
    if (role !== "CLIENT") setValue("client_id", "");
  }, [role, setValue]);

  async function submit(values: Values) {
    setApiError(null);
    try {
      const payload: UserCreate | UserUpdate = {
        full_name: values.full_name,
        phone: values.phone || null,
        role: values.role,
        client_id: values.client_id || null,
        is_active: values.is_active
      };
      if (!formData) {
        (payload as UserCreate).email = values.email;
        (payload as UserCreate).password = values.password ?? "";
        if (!values.password || values.password.length < 6) {
          setApiError("La contraseña debe tener al menos 6 caracteres.");
          return;
        }
      } else if (values.password) {
        if (values.password.length < 6) {
          setApiError("La contraseña debe tener al menos 6 caracteres.");
          return;
        }
        (payload as UserUpdate).password = values.password;
      }
      await onSubmit(payload);
    } catch (error) {
      setApiError(error instanceof ApiError ? error.detail : "No se pudo guardar el usuario.");
    }
  }

  return (
    <Card>
      <CardContent>
        <form className="space-y-5" onSubmit={handleSubmit(submit)}>
          {apiError ? <ErrorState message={apiError} /> : null}
          <div className="grid gap-4 md:grid-cols-2">
            <Field error={errors.full_name?.message} label="Nombre">
              <Input {...register("full_name")} />
            </Field>
            <Field error={errors.email?.message} label="Email">
              <Input disabled={Boolean(formData)} type="email" {...register("email")} />
            </Field>
            <Field label="Teléfono">
              <Input {...register("phone")} />
            </Field>
            <Field label={formData ? "Nueva contraseña opcional" : "Contraseña"}>
              <Input type="password" {...register("password")} />
            </Field>
            <Field error={errors.role?.message} label="Rol">
              <RoleSelect currentRole={currentRole} registration={register("role")} />
            </Field>
            <Field error={errors.client_id?.message} label="Cliente asociado">
              <ClientSelect clients={clients} registration={register("client_id")} />
            </Field>
            <label className="flex items-center gap-2 text-sm font-medium">
              <input className="h-4 w-4" type="checkbox" {...register("is_active")} />
              Usuario activo
            </label>
          </div>
          <FormActions cancelHref={cancelHref} loading={isSubmitting} submitLabel={submitLabel} />
        </form>
      </CardContent>
    </Card>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="grid gap-2 text-sm font-medium">
      {label}
      {children}
      {error ? <span className="text-xs text-rose-600">{error}</span> : null}
    </label>
  );
}
