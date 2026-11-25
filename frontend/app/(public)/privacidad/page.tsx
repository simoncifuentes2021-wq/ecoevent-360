import type { Metadata } from "next";
import { LegalPageShell } from "@/components/legal/LegalPageShell";

export const metadata: Metadata = {
  title: "Política de privacidad | Greenway App",
  description: "Información sobre el tratamiento de datos personales en Greenway App."
};

export default function PrivacyPage() {
  return (
    <LegalPageShell
      title="Política de privacidad"
      description="Te explicamos qué información se utiliza en Greenway App, para qué se usa y cómo puedes consultar o solicitar cambios sobre tus datos."
      updatedAt="25 de noviembre de 2026"
    >
      <section>
        <h2>1. Quién es responsable</h2>
        <p>Greenway App es operada por <strong>Servicios y Asesorías Ambientales SpA (Greenway)</strong>, RUT <strong>76.747.233-1</strong>, Chile. Para consultas sobre privacidad o para ejercer tus derechos, escríbenos a <a href="mailto:gonzalo@greenway.cl">gonzalo@greenway.cl</a>. También puedes llamar al <a href="tel:+56961253554">+56 9 6125 3554</a>.</p>
        <p>En los datos que una empresa cliente incorpora para organizar sus eventos, esa empresa puede determinar los fines y medios del tratamiento, mientras Greenway presta y mantiene la plataforma siguiendo sus instrucciones. Greenway también trata datos para administrar cuentas, seguridad, soporte y funcionamiento del servicio.</p>
      </section>

      <section>
        <h2>2. Datos que podemos tratar</h2>
        <p>Según las funciones utilizadas, Greenway App puede tratar:</p>
        <ul>
          <li>Datos de cuenta y acceso, como nombre, correo, organización, perfil y registros técnicos de inicio de sesión.</li>
          <li>Datos de clientes, eventos y personal asignado, que pueden incluir nombre, RUT, datos de contacto, funciones y documentos laborales cargados por usuarios autorizados.</li>
          <li>Registros operativos de voluntariado, activaciones, residuos, materiales, tareas, formularios y aportes.</li>
          <li>Archivos y evidencias que se adjuntan a la operación, como fotografías, documentos y comprobantes.</li>
          <li>Datos técnicos necesarios para proteger y mantener el servicio, como registros de actividad, errores y solicitudes.</li>
        </ul>
        <p>Los usuarios que cargan información deben contar con autorización para hacerlo y evitar incorporar datos que no sean necesarios para el evento o proceso correspondiente.</p>
      </section>

      <section>
        <h2>3. Para qué usamos la información</h2>
        <ul>
          <li>Crear y administrar cuentas, roles, eventos y equipos de trabajo.</li>
          <li>Registrar actividades ambientales, residuos, voluntariado, evidencias y resultados.</li>
          <li>Preparar documentos, reportes, certificados y comunicaciones solicitados desde la plataforma.</li>
          <li>Enviar invitaciones, avisos operativos y correos relacionados con los servicios habilitados.</li>
          <li>Proteger la plataforma, atender solicitudes, resolver incidentes y mejorar su funcionamiento.</li>
        </ul>
        <p>No utilizamos la información de Greenway App para vender bases de datos ni para publicidad basada en perfiles personales.</p>
      </section>

      <section>
        <h2>4. Integraciones y proveedores</h2>
        <p>Para prestar el servicio, cierta información puede ser procesada por proveedores tecnológicos que alojan o ejecutan partes de la plataforma, como Vercel, Render, Supabase y Cloudflare. Resend puede procesar datos de contacto y contenido necesario para entregar correos.</p>
        <p>Si un administrador conecta Google Calendar, Greenway usa esa autorización para crear, actualizar o retirar invitaciones de los eventos administrados desde la plataforma y compartir con Google los datos incluidos en esas invitaciones. La plataforma no utiliza esa integración para consultar el calendario personal con fines ajenos a la coordinación de eventos.</p>
        <p>Cuando una persona autorizada utiliza funciones de inteligencia artificial, los datos necesarios para generar la propuesta solicitada pueden enviarse al proveedor de IA configurado por Greenway. El uso depende de la función y configuración habilitadas; se recomienda no incluir información personal o sensible que no sea necesaria.</p>
        <p>Estos proveedores pueden procesar información desde distintos países, según la infraestructura y configuración del servicio. Greenway procura utilizar cada integración solo para la finalidad correspondiente y aplicar medidas de seguridad razonables.</p>
      </section>

      <section>
        <h2>5. Conservación y seguridad</h2>
        <p>Conservamos la información mientras sea necesaria para prestar el servicio, mantener la trazabilidad de eventos, atender obligaciones contractuales o legales y resolver reclamos. Los plazos pueden variar según el tipo de registro y las instrucciones de la organización que administra el evento. Cuando deja de ser necesaria, se elimina o se anonimiza, salvo que exista una obligación legítima de conservarla.</p>
        <p>Aplicamos controles de acceso por perfil, medidas técnicas de protección y resguardo de archivos. Ningún servicio conectado puede garantizar seguridad absoluta; por eso también es importante proteger las credenciales y reportar cualquier acceso no autorizado.</p>
      </section>

      <section>
        <h2>6. Tus derechos y solicitudes</h2>
        <p>Puedes solicitar información sobre tus datos y pedir su actualización, rectificación, eliminación u otras medidas que reconozca la legislación aplicable. Si los datos fueron incorporados por una empresa cliente, podemos derivar la solicitud a esa organización o pedirle instrucciones para responder correctamente.</p>
        <p>Envía tu solicitud a <a href="mailto:gonzalo@greenway.cl">gonzalo@greenway.cl</a>, indicando tu nombre, medio de contacto, organización o evento relacionado y qué necesitas. No envíes contraseñas ni documentos completos por correo salvo que sean necesarios y te indiquemos un canal adecuado.</p>
      </section>

      <section>
        <h2>7. Cookies y almacenamiento del navegador</h2>
        <p>La plataforma puede utilizar almacenamiento técnico del navegador para mantener la sesión, recordar preferencias esenciales y proteger el acceso. No usamos cookies publicitarias para seguir la navegación de usuarios dentro de Greenway App.</p>
      </section>

      <section>
        <h2>8. Actualizaciones de esta política</h2>
        <p>Podemos actualizar esta política cuando cambien las funciones, proveedores o requisitos aplicables. Publicaremos la versión vigente en esta página e indicaremos su fecha de actualización.</p>
      </section>
    </LegalPageShell>
  );
}
