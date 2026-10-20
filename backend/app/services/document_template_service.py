from __future__ import annotations

import base64
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from html import escape
from pathlib import Path

from app.services.document_people_service import normalize_person_name


_MONTHS_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_TEMPLATE_ROOT = Path(__file__).resolve().parents[3] / "docs" / "document-templates-source"
_EPP_SOURCE = _TEMPLATE_ROOT / "REGISTRO DE RECEPCION DE DOCUMENTOS.docx"


def _value(value: object, *, blank: str = "________________________") -> str:
    return escape(str(value)) if value is not None and str(value).strip() else blank


def _long_date(value: object) -> str:
    if value is None or value == "":
        return "________________________"
    try:
        parsed = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return escape(str(value))
    month = _MONTHS_ES[parsed.month - 1].capitalize()
    return f"{parsed.day} de {month} de {parsed.year}"


def _short_date(value: object) -> str:
    if value is None or value == "":
        return ""
    try:
        parsed = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return escape(str(value))
    return parsed.strftime("%d / %m / %Y")


def _money(value: object) -> str:
    if value is None or value == "":
        return "________________________"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return escape(str(value))
    rendered = f"{amount:,.2f}"
    rendered = rendered.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return rendered[:-3] if rendered.endswith(",00") else rendered


def _simulated_signature(label: str, name: object, timestamp: object) -> str:
    if not timestamp:
        return f"<div class='sign-slot'><div class='signature-rule'></div><strong>{label}</strong></div>"
    stamp = "FIRMA SIMULADA · ENTORNO LOCAL"
    when = _signature_time(timestamp)
    return (
        "<div class='sign-slot signed'>"
        f"<div class='simulated-mark'>{stamp}</div><strong>{label}</strong>"
        f"<span>{_value(name, blank='')}</span><small>{when}</small></div>"
    )


def _signature_mark(label: str, name: object, timestamp: object, image_data_url: object) -> str:
    if not timestamp:
        return f"<div class='sign-slot'><div class='signature-rule'></div><strong>{label}</strong></div>"
    if not isinstance(image_data_url, str) or not image_data_url.startswith("data:image/png;base64,"):
        return _simulated_signature(label, name, timestamp)
    return (
        "<div class='sign-slot signed'>"
        f"<img class='signature-image' src='{escape(image_data_url, quote=True)}' alt='Firma dibujada' />"
        f"<strong>{label}</strong><span>{_value(name, blank='')}</span>"
        f"<small>{_signature_time(timestamp)}</small></div>"
    )


def _signature_time(value: object) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return escape(parsed.strftime("%d / %m / %Y %H:%M"))
    except (TypeError, ValueError):
        return escape(str(value))


@lru_cache(maxsize=1)
def _epp_logo_data_uri() -> str:
    if not _EPP_SOURCE.is_file():
        raise FileNotFoundError(f"No se encuentra la plantilla EPP fuente: {_EPP_SOURCE}")
    with zipfile.ZipFile(_EPP_SOURCE) as source:
        image = source.read("word/media/image1.png")
    encoded = base64.b64encode(image).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _contract_html(snapshot: dict, signatures: dict) -> str:
    person = snapshot.get("person") or {}
    employment = snapshot.get("employment") or {}
    event = snapshot.get("event") or {}
    data = snapshot.get("data") or {}
    worker_name = normalize_person_name(
        " ".join(
            part
            for part in (
                str(person.get("first_name") or "").strip(),
                str(person.get("last_name") or "").strip(),
            )
            if part
        )
    )
    duties = data.get("duties") or employment.get("duties") or employment.get("position")
    workplace = (
        data.get("workplace")
        or event.get("venue")
        or event.get("address")
        or employment.get("workplace")
    )
    employer_commune = data.get("employer_commune") or "Santiago"
    clauses = (
        (
            "PRIMERO:",
            " El trabajador se compromete a prestar las labores de "
            f"{_value(duties)}, desde el día <strong>{_long_date(employment.get('start_date'))}</strong> "
            f"hasta el <strong>{_long_date(employment.get('end_date'))}</strong>, en el evento denominado "
            f"<strong>{_value(event.get('name'))}</strong> en las dependencias de "
            f"<strong>{_value(workplace)}</strong>.",
        ),
        (
            "SEGUNDO:",
            " El trabajador percibirá una remuneración correspondiente a "
            f"<strong>{_money(employment.get('remuneration'))}</strong> diarios, "
            "por las labores indicadas en la cláusula anterior.",
        ),
        (
            "",
            "Además, el empleador pagará gratificación legal de conformidad a lo dispuesto en el artículo 47 del Código del Trabajo, "
            "la que se pagará de acuerdo a la siguiente modalidad Empleador deducirá de la remuneración mensual del Trabajador "
            "los descuentos que establece la ley tales como cotizaciones previsionales e impuestos y efectuará cualquier otro "
            "descuento que legalmente proceda, ingresándolos en las respectivas instituciones previsionales o en arcas fiscales, "
            "según corresponda.",
        ),
        (
            "TERCERO:",
            " El presente contrato tendrá duración hasta la conclusión de las labores precisas y determinadas para las que ha sido "
            "contratado el trabajador y a las que se ha hecho referencia en la cláusula primera.",
        ),
        (
            "CUARTO:",
            " El trabajador deberá desempeñarse ininterrumpidamente (en el lugar de la obra señalada en la cláusula primera) / "
            "(en las dependencias del empleador) y, exclusivamente para las labores señaladas en la cláusula primera.",
        ),
        (
            "QUINTO:",
            " La jornada ordinaria de trabajo será de 45 horas semanales y/o 8 a 10 horas diaria. "
            "El tiempo destinado a colación (1 hora), no será imputable a la jornada de trabajo.",
        ),
        (
            "SEXTO:",
            " El trabajador se compromete y obliga expresamente a cumplir las instrucciones que le sean impartidas por su jefe "
            "inmediato o por la Gerencia, a desarrollar su trabajo con el debido cuidado, evitando comprometer la seguridad y salud "
            "del resto de los trabajadores de la empresa, y a respetar las normas del Reglamento Interno de Orden, Higiene y Seguridad, "
            "las cuales declara conocer y que para estos efectos se consideran parte integrante del presente contrato, reglamento "
            "del cual el trabajador recibe un ejemplar en este acto.",
        ),
        (
            "SEPTIMO:",
            " Se deja constancia que el trabajador ingresó al servicio del empleador con fecha "
            f"<strong>{_long_date(employment.get('start_date'))}</strong>.",
        ),
        (
            "OCTAVO:",
            " Para todos los efectos derivados del presente contrato las partes fijan domicilio en la ciudad de Santiago y se someten "
            "a la Jurisdicción de sus Tribunales.",
        ),
        (
            "NOVENO:",
            " El presente contrato se firma en dos ejemplares, declarando el trabajador haber recibido en este acto un ejemplar de "
            "dicho instrumento, que es el fiel reflejo de la relación laboral convenida.",
        ),
    )
    clauses_html = "".join(
        f"<p class='clause{' source-page-break-after' if label == 'QUINTO:' else ''}'>"
        f"{f'<strong>{label}</strong>' if label else ''}{text}</p>"
        for label, text in clauses
    )
    intro = (
        f"En Santiago, a <strong>{_long_date(data.get('contract_date'))}</strong>, entre la Empresa "
        f"<strong>{_value(data.get('employer_name'))}</strong>., Rut "
        f"<strong>{_value(data.get('employer_rut'))}</strong>, representada por don "
        f"<strong>{_value(data.get('representative_name'))}</strong>, Cedula Nacional de identidad N°"
        f"<strong>{_value(data.get('representative_rut'))}</strong>, en su calidad de Representante legal, ambos con domicilio en "
        f"<strong>{_value(data.get('employer_address'))}</strong>, comuna de <strong>{_value(employer_commune)}</strong>, "
        f"en adelante “el empleador” y don (a) <strong>{_value(worker_name)}</strong>, cédula de identidad Nº "
        f"<strong>{_value(person.get('rut'))}</strong>, domiciliado en <strong>{_value(person.get('address'))}</strong>, "
        f"comuna de <strong>{_value(person.get('commune'))}</strong> en, en adelante “el trabajador”, "
        "se conviene el siguiente contrato de trabajo:"
    )
    employer_signature = snapshot.get("employer_signature") or {}
    signature_html = (
        "<section class='signatures'>"
        + _signature_mark(
            "Firma manuscrita del trabajador",
            signatures.get("worker_name") or worker_name,
            signatures.get("worker_signed_at"),
            signatures.get("worker_signature_data_url"),
        )
        + _signature_mark(
            "Firma del empleador / representante legal",
            employer_signature.get("signer_name") or signatures.get("supervisor_name"),
            employer_signature.get("applied_at") or signatures.get("supervisor_signed_at"),
            employer_signature.get("signature_data_url") or signatures.get("employer_signature_data_url"),
        )
        + "</section>"
    )
    title = "CONTRATO POR OBRA O FAENA"
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
@page {{ size: Letter; margin: 25mm 30mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #111; font: 11pt/1.24 Arial, sans-serif; text-align: justify; }}
h1 {{ margin: 0 0 25pt; font-size: 18pt; line-height: 1.1; text-align: center; font-weight: 700; }}
p {{ margin: 0 0 10pt; orphans: 2; widows: 2; }}
.intro {{ margin-bottom: 14pt; }}
.clause {{ margin-bottom: 10pt; }}
.source-page-break-after {{ break-after: page; page-break-after: always; }}
.signatures {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10mm; margin-top: 18mm; page-break-inside: avoid; break-inside: avoid; text-align: center; }}
.sign-slot {{ min-width: 0; display: flex; flex-direction: column; align-items: stretch; justify-content: end; min-height: 30mm; font-size: 9pt; }}
.signature-rule {{ height: 19mm; border-bottom: 0.7pt solid #111; margin-bottom: 2mm; }}
.signature-image {{ width: 100%; height: 19mm; object-fit: contain; object-position: center bottom; border-bottom: 0.7pt solid #111; margin-bottom: 2mm; }}
.signed .simulated-mark {{ min-height: 16mm; display: grid; place-items: center; border-bottom: 0.7pt solid #111; margin-bottom: 2mm; color: #8a1c1c; font-size: 8.5pt; font-weight: 700; }}
.sign-slot span, .sign-slot small {{ display: block; margin-top: 2mm; font-size: 8.5pt; }}
</style></head><body><h1>{title}</h1><p class="intro">{intro}</p>{clauses_html}{signature_html}</body></html>"""


def _epp_html(snapshot: dict, signatures: dict) -> str:
    person = snapshot.get("person") or {}
    employment = snapshot.get("employment") or {}
    data = snapshot.get("data") or {}
    epp = snapshot.get("epp") or {}
    worker_ack = snapshot.get("worker_acknowledgments") or {}
    if worker_ack:
        received_codes = set(worker_ack.get("received_item_codes") or [])
        epp = {**epp, "items": [
            {**item, "received_conformity": item.get("item_code") in received_codes}
            for item in epp.get("items", [])
        ]}
    worker_name = normalize_person_name(
        " ".join(
            part
            for part in (
                str(person.get("first_name") or "").strip(),
                str(person.get("last_name") or "").strip(),
            )
            if part
        )
    )
    employer_name = _value(
        data.get("employer_name") or snapshot.get("employer_name"),
        blank="________________________",
    )
    rows = []
    for item in epp.get("items", []):
        label = str(item.get("label") or "")
        rows.append(
            "<tr>"
            f"<td>{_value(label, blank='')}</td><td>{_short_date(item.get('received_at'))}</td>"
            f"<td class='conformity'>{'Sí' if item.get('received_conformity') else ''}</td></tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='3'>Sin elementos EPP configurados</td></tr>")
    logo = _epp_logo_data_uri()
    worker_sig = _signature_mark(
        "Firma del Trabajador",
        signatures.get("worker_name") or worker_name,
        signatures.get("worker_signed_at"),
        signatures.get("worker_signature_data_url"),
    )
    employer_signature = snapshot.get("employer_signature") or {}
    supervisor_sig = _signature_mark(
        "Firma / Timbre del Instructor o Supervisor",
        employer_signature.get("signer_name") or signatures.get("supervisor_name"),
        employer_signature.get("applied_at") or signatures.get("supervisor_signed_at"),
        employer_signature.get("signature_data_url") or signatures.get("employer_signature_data_url"),
    )
    acknowledgment_html = ""
    if worker_ack:
        acknowledgment_html = (
            "<p><strong>Constancias confirmadas por el trabajador:</strong> "
            f"RIOHS: {'Recibido' if worker_ack.get('riohs_received') else 'No confirmado'}; "
            f"EIRL: {'Realizada / informada' if worker_ack.get('eirl_completed') else 'No confirmada'}; "
            f"revisión de elementos EPP: {'confirmada' if worker_ack.get('items_reviewed') else 'no confirmada'}; "
            f"confirmación registrada el {_value(worker_ack.get('confirmed_at'))}.</p>"
        )
        worker_sig = acknowledgment_html + worker_sig
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
@page {{ size: Letter; margin: 12.7mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #111; font: 10.5pt/1.18 Arial, sans-serif; }}
.logo {{ display: block; width: 54mm; height: auto; margin: 0 auto 5mm; }}
h1 {{ margin: 0 0 6mm; font-size: 18pt; line-height: 1.1; font-weight: 700; text-align: left; }}
.identity {{ width: 100%; border-collapse: collapse; margin: 0 0 5mm; }}
.identity td {{ height: 7mm; padding: 1.2mm 2mm; border: 0.5pt solid #333; }}
.identity strong {{ font-weight: 400; }}
h2 {{ margin: 5mm 0 3mm; font-size: 12pt; line-height: 1.15; font-weight: 700; }}
p {{ margin: 0 0 3mm; text-align: justify; orphans: 2; widows: 2; }}
.epp-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin: 3mm 0 4mm; font-size: 9pt; }}
.epp-table col:nth-child(1) {{ width: 43%; }} .epp-table col:nth-child(2) {{ width: 30%; }}
.epp-table col:nth-child(3) {{ width: 27%; }}
.epp-table th, .epp-table td {{ border: 0.5pt solid #333; padding: 2mm 1.5mm; vertical-align: middle; overflow-wrap: anywhere; }}
.epp-table th {{ text-align: center; font-weight: 700; }} .epp-table td:first-child {{ text-align: left; }}
.epp-table td:not(:first-child) {{ text-align: center; }} .epp-table .source-blank-row td {{ height: 5mm; }}
ul {{ margin: 0 0 3mm 7mm; padding-left: 5mm; }} li {{ margin: 0 0 1.5mm; padding-left: 1mm; }}
.signature-stack {{ margin-top: 5mm; page-break-inside: avoid; break-inside: avoid; }}
.sign-slot {{ max-width: 95mm; min-height: 21mm; display: flex; flex-direction: column; justify-content: end; margin: 0 auto 5mm; text-align: center; font-size: 10pt; }}
.signature-rule {{ height: 11mm; border-bottom: 0.6pt solid #111; margin-bottom: 1.5mm; }}
.signature-image {{ width: 100%; height: 11mm; object-fit: contain; object-position: center bottom; border-bottom: 0.6pt solid #111; margin-bottom: 1.5mm; }}
.signed .simulated-mark {{ height: 11mm; display: grid; place-items: center; border-bottom: 0.6pt solid #111; margin-bottom: 1.5mm; color: #8a1c1c; font-size: 8pt; font-weight: 700; }}
.sign-slot span, .sign-slot small {{ display: block; margin-top: 1mm; font-size: 8pt; }}
.delivery-date {{ margin: 1mm 0 4mm; text-align: center; }}
</style></head><body>
<img class="logo" src="{logo}" alt="Greenway" />
<h1>REGISTRO DE RECEPCIÓN DE DOCUMENTOS Y ELEMEMENTOS DE PROTECCIÓN PERSONAL</h1>
<table class="identity"><tbody>
<tr><td> NOMBRE TRABAJADOR : <strong>{_value(worker_name)}</strong></td></tr>
<tr><td> RUT: <strong>{_value(person.get('rut'))}</strong></td></tr>
<tr><td>CARGO : <strong>{_value(employment.get('position'), blank='STAFF')}</strong> </td></tr>
<tr><td>ÁREA : <strong>{_value(employment.get('area'), blank='LIMPIEZA')}</strong></td></tr>
</tbody></table>
<h2>ELEMENENTOS DE PROTECCIÓN PERSONAL</h2>
<p>De acuerdo a lo estipulado en la Ley 16.744, Art. 68 inciso tres “Las empresas deberán proporcionar a sus trabajadores, los equipos e implementos de protección necesarios, no pudiendo en caso alguno cobrarles su valor”.</p>
<table class="epp-table"><colgroup><col/><col/><col/></colgroup><thead><tr>
<th>ELEMENTO ENTREGADO</th><th>FECHA DE RECEPCIÓN</th><th>RECIBÍ CONFORME</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table>
<p>El trabajador se compromete a mantener los elementos de protección personal en buen estado y declara haberlos recibido en forma gratuita.</p>
<h2>RECEPCIÓN DE Reglamento Interno de Orden, Higiene y Seguridad (RIOHS)</h2>
<p>Declaro haber recibido de parte de la empresa {employer_name}, en forma totalmente gratuita, un ejemplar físico / digital del Reglamento Interno de Orden, Higiene y Seguridad (RIOHS), de acuerdo con lo establecido en la legislación laboral vigente (Ley N° 16.744 y el Código del Trabajo).</p>
<p>Asumo la responsabilidad de leer íntegramente su contenido, así como de cumplir de manera estricta con todas las obligaciones, prohibiciones, normas de orden, procedimientos de seguridad y el correcto uso de los Elementos de Protección Personal (EPP) señalados en dicho texto.</p>
<p>Entiendo que el desonocimiento de las normas contenidas en este reglamento no exime de su cumplimiento ni de las responsabilidades administrativas o legales que de ello se deriven</p>
<h2>RECEPCIÓN DE EVALUACIÓN INICIAL DE RIESGOS LABORALES (EIRL)</h2>
<p>Declaro que {employer_name}, a través de su área técnica / supervisor, me ha hecho entrega y explicado detalladamente la Evaluación Inicial de Riesgos Laborales correspondiente a mi puesto de trabajo.</p>
<p>Asimismo, certifico que he sido debidamente informado y capacitado respecto a:</p>
<ul><li>Los riesgos específicos y peligros inherentes a las funciones que voy a desempeñar.</li>
<li>Las medidas preventivas y los métodos de trabajo correctos que debo aplicar de forma obligatoria.</li>
<li>El uso correcto, mantenimiento y reposición de los Elementos de Protección Personal (EPP) asignados.</li>
<li>Las medidas de emergencia, vías de evacuación y acciones en caso de accidentes laborales.</li></ul>
<p>Me comprometo a cumplir rigurosamente con todas las instrucciones de seguridad entregadas, velando por mi integridad física y la de mis compañeros de trabajo.</p>
<section class="signature-stack">{worker_sig}<p class="delivery-date">Fecha de Entrega: {_short_date(epp.get('delivery_date'))}</p>{supervisor_sig}</section>
</body></html>"""


def render_document_html(snapshot: dict, signatures: dict | None = None) -> str:
    employer_signature = snapshot.get("employer_signature") or {}
    sig = {
        **(signatures or {}),
        "employer_signature_data_url": employer_signature.get("signature_data_url"),
    }
    if snapshot.get("kind") == "EPP":
        return _epp_html(snapshot, sig)
    return _contract_html(snapshot, sig)
