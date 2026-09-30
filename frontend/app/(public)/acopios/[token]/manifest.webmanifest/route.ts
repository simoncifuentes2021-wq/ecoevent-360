import { NextResponse } from "next/server";

export function GET(_request: Request, { params }: { params: { token: string } }) {
  const token = encodeURIComponent(params.token);
  return NextResponse.json({
    name: "Registro de acopio Greenway",
    short_name: "Acopio Greenway",
    description: "Registro de residuos en terreno",
    start_url: `/acopios/${token}`,
    scope: "/acopios/",
    display: "standalone",
    background_color: "#f4f7f4",
    theme_color: "#064e3b",
    lang: "es",
  }, { headers: { "Cache-Control": "public, max-age=3600" } });
}
