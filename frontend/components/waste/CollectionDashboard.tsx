"use client";

import { useCallback, useEffect, useState } from "react";
import { BarChart3, Boxes, CalendarDays, FileText, House, Layers, Leaf, Lightbulb, MapPin, Package, Recycle, Scale, Smartphone, Sprout, Users, Zap } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { getWasteCollectionSummary } from "@/lib/api/waste";
import type { WasteCollectionSummary } from "@/types/waste";

const format = (value: number | string | undefined, digits = 1) => new Intl.NumberFormat("es-CL", { maximumFractionDigits: digits }).format(Number(value || 0));

export function CollectionDashboard({ summary }: { summary?: WasteCollectionSummary | null }) {
  const [activeView, setActiveView] = useState<"indicators" | "equivalences">("indicators");
  if (!summary) return <section className="rounded-2xl border border-dashed bg-white p-8 text-center text-sm text-slate-500">No hay datos de acopios disponibles para este evento.</section>;

  return <div className="space-y-4">
    <CollectionViewTabs activeView={activeView} onChange={setActiveView} />
    {activeView === "indicators" ? <CollectionIndicators summary={summary} /> : <CollectionEquivalencesView summary={summary} />}
  </div>;
}

export function CollectionViewTabs({ activeView, onChange }: { activeView: "indicators" | "equivalences"; onChange: (view: "indicators" | "equivalences") => void }) {
  const tabs = [
    { id: "indicators" as const, label: "Indicadores", icon: BarChart3 },
    { id: "equivalences" as const, label: "Ecoequivalencias", icon: Leaf },
  ];
  return <nav aria-label="Vistas de acopios" className="flex flex-wrap gap-2 border-b border-slate-200 pb-3" role="tablist">
    {tabs.map(({ id, label, icon: Icon }) => <button key={id} type="button" role="tab" aria-selected={activeView === id} onClick={() => onChange(id)} className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ${activeView === id ? "bg-emerald-700 text-white" : "border bg-white text-slate-700 hover:bg-slate-50"}`}><Icon className="h-4 w-4"/>{label}</button>)}
  </nav>;
}

export function CollectionIndicators({ summary }: { summary: WasteCollectionSummary }) {
  const total = Number(summary.total_kg || 0);
  const recyclable = Number(summary.recyclable_kg || 0);
  const potentialRate = total ? recyclable / total * 100 : 0;
  const charts = [
    { title: "Material recibido", icon: Boxes, rows: summary.by_type.map(item => ({ key: item.id, label: item.name, kg: Number(item.total_kg), hint: item.is_recyclable ? "Potencialmente reciclable" : "Sin clasificación reciclable" })) },
    { title: "Recepción por acopio", icon: MapPin, rows: summary.by_point.map(item => ({ key: item.id, label: `${item.code} · ${item.name}`, kg: Number(item.total_kg), hint: `${item.records_count} registros` })) },
  ];
  const cards = [
    { label: "Peso recibido", value: `${format(total)} kg`, hint: "Registros de Acopios", icon: Scale },
    { label: "Registros", value: format(summary.records_count, 0), hint: "Recepciones registradas", icon: Boxes },
    { label: "Acopios activos", value: format(summary.active_points, 0), hint: "Puntos habilitados", icon: MapPin },
    { label: "Personas registradas", value: format(summary.unique_submitters, 0), hint: "Identificadores únicos", icon: Users },
  ];

  return <div className="space-y-5">
    <section className="rounded-2xl bg-gradient-to-r from-emerald-950 to-emerald-800 p-5 text-white shadow-sm sm:p-7">
      <div className="flex items-center gap-2 text-emerald-100"><BarChart3 className="h-5 w-5"/><span className="text-sm font-semibold">Desempeño de acopios</span></div>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-5"><div><p className="text-sm text-emerald-100">Material recibido en el evento</p><p className="mt-1 text-4xl font-black tracking-tight">{format(total)} <span className="text-xl font-semibold">kg</span></p></div><div className="rounded-xl border border-white/15 bg-white/10 px-4 py-3"><p className="text-xs text-emerald-100">Potencialmente reciclable según catálogo</p><p className="mt-1 text-2xl font-bold">{format(recyclable)} kg <span className="text-sm font-medium">· {format(potentialRate, 0)}%</span></p></div></div>
    </section>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{cards.map(({ label, value, hint, icon: Icon }) => <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm" key={label}><div className="flex items-center justify-between"><p className="text-sm text-slate-500">{label}</p><Icon className="h-4 w-4 text-emerald-700"/></div><p className="mt-2 text-2xl font-bold text-slate-950">{value}</p><p className="mt-1 text-xs text-slate-500">{hint}</p></article>)}</div>
    <div className="grid gap-4 lg:grid-cols-2">{charts.map(({ title, icon: Icon, rows }) => { const max = Math.max(...rows.map(row => row.kg), 1); return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" key={title}><h3 className="flex items-center gap-2 font-bold text-slate-900"><Icon className="h-4 w-4 text-emerald-700"/>{title}</h3>{rows.length ? <div className="mt-4 space-y-4">{rows.map(row => <div key={row.key}><div className="mb-1 flex justify-between gap-3 text-sm"><span className="truncate font-medium">{row.label}</span><span className="shrink-0 font-semibold">{format(row.kg)} kg</span></div><div className="h-2.5 rounded-full bg-slate-100"><div className="h-2.5 rounded-full bg-emerald-600" style={{ width: `${Math.max(row.kg > 0 ? 2 : 0, row.kg / max * 100)}%` }}/></div><p className="mt-1 text-xs text-slate-500">{row.hint}</p></div>)}</div> : <p className="mt-4 text-sm text-slate-500">Aún no hay registros.</p>}</section>; })}</div>
  </div>;
}

export function CollectionEquivalencesView({ summary }: { summary: WasteCollectionSummary }) {
  const equivalents = summary.eco_equivalences ?? [];
  const featured = equivalents.find((item) => item.kind === "FAMILY_DAYS");
  const value = Number(featured?.value || 0);
  const familyDailyKg = Number(featured?.reference_kg || 4.5);
  const familyMonthlyKg = familyDailyKg * 30;
  const familyAnnualKg = familyDailyKg * 365;
  const progress = featured ? Math.min(100, Math.max(0, (value / 60) * 100)) : 0;
  const materialGroups = new Map<string, typeof equivalents>();
  equivalents.filter((item) => item.kind === "MATERIAL_UNITS").forEach((item) => {
    const key = item.waste_type_name || "Otros materiales";
    materialGroups.set(key, [...(materialGroups.get(key) ?? []), item]);
  });
  const materialEquivalenceCount = Array.from(materialGroups.values()).reduce((count, items) => count + items.length, 0);
  const sortedMaterialGroups = Array.from(materialGroups, ([material, items]) => {
    const materialKg = Number(summary.by_type.find((item) => item.name === material)?.total_kg || 0);
    const isOrganic = /org[aá]nic|compost/i.test(material);
    return { material, items, materialKg, share: Number(summary.total_kg) > 0 ? materialKg / Number(summary.total_kg) * 100 : 0, destination: isOrganic ? "Compostaje" : "Reciclaje", isOrganic };
  }).sort((a, b) => b.materialKg - a.materialKg);

  if (!equivalents.length) return <section className="rounded-2xl border border-dashed bg-white p-6"><h3 className="font-bold text-slate-900">Ecoequivalencias</h3><p className="mt-1 text-sm text-slate-600">Las comparaciones aparecerán cuando se configuren y existan registros para esos materiales.</p></section>;

  return <section className="mx-auto max-w-7xl overflow-hidden rounded-3xl border border-emerald-100 bg-gradient-to-br from-emerald-50 via-white to-teal-50 p-4 shadow-sm sm:p-6">
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3 sm:mb-5"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">Impacto en perspectiva</p><h3 className="mt-1 flex items-center gap-2 text-xl font-bold text-emerald-950"><Leaf className="h-5 w-5"/>Ecoequivalencias</h3><p className="mt-1 text-sm text-emerald-900">Lo recibido en los acopios, expresado en referencias cotidianas.</p></div><span className="rounded-full border border-emerald-200 bg-white/80 px-3 py-1 text-xs font-semibold text-emerald-800">Valores aproximados</span></div>
    {materialGroups.size ? <div className="mb-5 flex flex-wrap gap-2 text-xs font-semibold text-emerald-900"><span className="rounded-full border border-emerald-200 bg-white/80 px-3 py-1.5">{materialGroups.size} {materialGroups.size === 1 ? "material con registros" : "materiales con registros"}</span><span className="rounded-full border border-emerald-200 bg-white/80 px-3 py-1.5">{materialEquivalenceCount} {materialEquivalenceCount === 1 ? "referencia calculada" : "referencias calculadas"}</span></div> : null}

    {featured ? <article className="relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-950 via-emerald-900 to-teal-800 p-5 text-white shadow-md sm:p-6">
      <Leaf aria-hidden="true" className="pointer-events-none absolute -right-5 -top-7 -z-10 h-40 w-40 rotate-[-24deg] text-white/[0.07]" strokeWidth={1.2}/>
      <div className="flex items-center gap-2 text-sm font-medium text-emerald-100"><span className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/10"><House className="h-4 w-4"/></span>Una referencia familiar</div>
      <p className="mt-5 text-sm font-medium text-emerald-100">Los {format(summary.total_kg)} kg recibidos equivalen a lo que genera una familia de 4 personas en</p>
      <p className="mt-1 text-4xl font-black tracking-tight sm:text-5xl">{format(featured.value)} <span className="text-lg font-semibold tracking-normal text-emerald-100 sm:text-xl">días</span></p>
      <div className="mt-5 max-w-2xl"><div className="h-3 overflow-hidden rounded-full bg-white/15" role="img" aria-label={`${format(featured.value)} días de generación familiar, en una escala de 60 días`}><div className="h-full rounded-full bg-gradient-to-r from-lime-300 to-emerald-300" style={{ width: `${progress}%` }}/></div><div className="mt-2 flex justify-between text-[11px] text-emerald-100"><span>0 días</span><span>30 días · 1 mes</span><span>60 días · 2 meses</span></div></div>
      <div className="mt-4 grid max-w-2xl gap-3 sm:grid-cols-3"><div className="rounded-xl border border-white/10 bg-white/10 p-3"><p className="text-xs text-emerald-100">Equivalencia aproximada</p><p className="mt-1 text-xl font-bold">{format(value / 7)} semanas</p><p className="text-[11px] text-emerald-100">de generación familiar</p></div><div className="rounded-xl border border-white/10 bg-white/10 p-3"><p className="text-xs text-emerald-100">En meses</p><p className="mt-1 text-xl font-bold">{format(value / 30)} meses</p><p className="text-[11px] text-emerald-100">considerando 30 días</p></div><div className="rounded-xl border border-white/10 bg-white/10 p-3"><p className="text-xs text-emerald-100">Del año familiar</p><p className="mt-1 text-xl font-bold">{format((value / 365) * 100)}%</p><p className="text-[11px] text-emerald-100">de 365 días</p></div></div>
      <p className="mt-4 flex items-start gap-2 rounded-xl border border-white/10 bg-white/[0.07] px-3 py-2.5 text-xs leading-relaxed text-emerald-100"><CalendarDays className="mt-0.5 h-4 w-4 shrink-0 text-lime-200"/><span>Referencia utilizada: {format(familyDailyKg, 1)} kg al día · {format(familyMonthlyKg, 0)} kg en 30 días · {format(familyAnnualKg, 1)} kg en 365 días.</span></p>
    </article> : null}

    {sortedMaterialGroups.length ? <div className="mt-5 grid items-start gap-4 xl:grid-cols-2">{sortedMaterialGroups.map(({ material, items, materialKg, share, destination, isOrganic }) => {
      return <section className="rounded-2xl border border-emerald-100 bg-white/80 p-4 sm:p-5" key={material}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div className="flex min-w-0 items-center gap-3"><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${isOrganic ? "bg-lime-50 text-lime-700" : "bg-emerald-50 text-emerald-700"}`}><Boxes className="h-5 w-5"/></span><div className="min-w-0"><h4 className="truncate font-bold text-slate-900">{material}</h4><span className={`mt-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${isOrganic ? "bg-lime-50 text-lime-800" : "bg-emerald-50 text-emerald-800"}`}>{isOrganic ? <Sprout className="h-3 w-3"/> : <Recycle className="h-3 w-3"/>}{destination}</span></div></div><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-800">{format(materialKg, 2)} kg</span><span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600">{format(share, 1)}% del total</span></div></div>
      <div className="mb-4"><div className="mb-1 flex justify-between text-[11px] font-medium text-slate-500"><span>Participación en los acopios</span><span>{format(share, 1)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${isOrganic ? "bg-lime-500" : "bg-emerald-600"}`} style={{ width: `${Math.min(100, share)}%` }}/></div></div>
      <div className="mx-auto grid min-w-0 max-w-6xl gap-3" style={{ gridTemplateColumns: items.length === 1 ? "minmax(0, 1fr)" : "repeat(auto-fit, minmax(min(100%, 19rem), 1fr))" }}>{items.map((item) => {
        const isContents = /contenido/i.test(item.name);
        const isOrganic = /compost/i.test(item.name);
        const isEnergy = /kwh/i.test(item.unit);
        const isPhoneCharging = /celular/i.test(item.unit);
        const isLedLighting = /iluminación led/i.test(item.unit);
        const EquivalenceIcon = isOrganic
          ? Sprout
          : isContents
            ? /fibra|cartón/i.test(item.name) ? FileText : /aluminio/i.test(item.name) ? Package : Layers
            : isPhoneCharging ? Smartphone : isLedLighting ? Lightbulb : isEnergy ? Zap : Recycle;
        const iconTone = isOrganic
          ? "bg-lime-50 text-lime-700 ring-lime-100"
          : isContents
            ? "bg-violet-50 text-violet-700 ring-violet-100"
            : isPhoneCharging
              ? "bg-sky-50 text-sky-700 ring-sky-100"
              : isLedLighting
                ? "bg-amber-50 text-amber-700 ring-amber-100"
                : isEnergy
                  ? "bg-yellow-50 text-yellow-700 ring-yellow-100"
                  : "bg-emerald-50 text-emerald-700 ring-emerald-100";
        const categoryLabel = isContents
          ? "Composición estimada"
          : isOrganic
            ? "Compostaje"
            : isPhoneCharging
              ? "Equivalencia climática"
              : isLedLighting || isEnergy
                ? "Ahorro energético potencial"
                : "Valorización del material";
        const explanation = isContents
          ? "Proporción estimada de componentes presentes en este tipo de envase; puede variar según su formato."
          : isOrganic
            ? "Compara el compostaje de los residuos orgánicos con su disposición en relleno sanitario."
            : isEnergy
              ? "Ahorro de energía potencial asociado a reciclar este material para fabricar nuevos productos."
              : isPhoneCharging
                ? "Equivalencia climática expresada en cargas completas de celular."
                : isLedLighting
                  ? "Energía potencial equivalente al uso de una ampolleta LED de 10 W durante este tiempo."
                  : "Referencia potencial asociada a la valorización de este material.";
        const result = <p className="break-words text-2xl font-bold leading-tight text-emerald-800">{format(item.value, 2)} <span className="text-sm font-semibold">{item.unit}</span></p>;
        const detail = <p className="mt-2 text-xs leading-relaxed text-slate-600">{explanation}</p>;
        return <article className="group min-w-0 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-200 hover:shadow-md sm:p-5" key={`${material}-${item.name}-${item.unit}`}>
          <div className="flex min-w-0 items-start gap-3">
            <span aria-hidden="true" className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl ring-1 ${iconTone}`}><EquivalenceIcon className="h-5 w-5" strokeWidth={1.9}/></span>
            <div className="min-w-0 flex-1">
              <p className="break-words text-sm font-semibold text-slate-800">{item.name}</p>
              <p className="mt-1.5 text-[11px] font-bold uppercase tracking-wide text-emerald-700">{categoryLabel}</p>
              <div className="mt-3 min-w-0">{result}</div>
              {detail}
            </div>
          </div>
        </article>;
      })}</div>
    </section>;
    })}</div> : null}
    <p className="mt-4 border-t border-emerald-200/80 pt-3 text-xs leading-relaxed text-emerald-950/70">Las ecoequivalencias son referenciales y aproximadas, basadas en referencias internacionales. El resultado real depende de la composición, el proceso y el destino de valorización.</p>
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-emerald-950/70"><span>{format(summary.total_kg)} kg recibidos</span><span>{format(summary.records_count, 0)} registros</span><span>{format(summary.active_points, 0)} acopios activos</span></div>
  </section>;
}

export function CollectionDashboardPanel({ eventId, view = "indicators" }: { eventId: string; view?: "indicators" | "equivalences" }) {
  const [summary, setSummary] = useState<WasteCollectionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSummary(await getWasteCollectionSummary(eventId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar esta vista de Acopios.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);
  if (loading) return <LoadingState label={view === "indicators" ? "Cargando indicadores de acopios..." : "Cargando ecoequivalencias..."} />;
  if (error) return <ErrorState title={view === "indicators" ? "Indicadores no disponibles" : "Ecoequivalencias no disponibles"} message={error} onRetry={() => void load()} />;
  if (!summary) return null;
  return view === "indicators" ? <CollectionIndicators summary={summary} /> : <CollectionEquivalencesView summary={summary} />;
}
