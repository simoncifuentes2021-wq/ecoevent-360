import type { Metadata } from "next";
import { LegalPageShell } from "@/components/legal/LegalPageShell";

export const metadata: Metadata = {
  title: "Condiciones de uso | Greenway App",
  description: "Condiciones para utilizar la plataforma Greenway App."
};

export default function TermsPage() {
  return (
    <LegalPageShell
      title="Condiciones de uso"
      description="Estas condiciones explican las reglas básicas para acceder y utilizar Greenway App y sus formularios públicos."
      updatedAt="25 de noviembre de 2026"
    >
      <section>
        <h2>1. Sobre la plataforma</h2>
        <p>Greenway App es una plataforma operada por <strong>Servicios y Asesorías Ambientales SpA (Greenway)</strong>, RUT <strong>76.747.233-1</strong>, que permite organizar información ambiental y operativa de eventos, gestionar equipos, registrar actividades y evidencias, y preparar documentos y reportes.</p>
      </section>

      <section>
        <h2>2. Acceso y cuentas</h2>
        <p>El acceso a las áreas privadas requiere una cuenta habilitada por Greenway o por la organización correspondiente. Cada persona debe cuidar sus credenciales, mantener sus datos de contacto actualizados y utilizar únicamente los permisos que le fueron asignados. No debes compartir tu cuenta ni intentar acceder a información fuera de tu autorización.</p>
      </section>

      <section>
        <h2>3. Uso responsable</h2>
        <p>Al utilizar la plataforma, te comprometes a:</p>
        <ul>
          <li>Ingresar información veraz y relacionada con la actividad que estás registrando.</li>
          <li>Contar con autorización para cargar datos personales, fotografías, documentos y evidencias de otras personas.</li>
          <li>No alterar registros para inducir a error, vulnerar derechos, interferir con el servicio o acceder sin permiso a cuentas o datos.</li>
          <li>Respetar las instrucciones de la organización responsable del evento y las leyes aplicables.</li>
        </ul>
      </section>

      <section>
        <h2>4. Información, evidencias y resultados</h2>
        <p>La organización que administra cada evento es responsable de revisar los datos, cantidades, documentos y evidencias que su equipo incorpora. Los cálculos ambientales, equivalencias, borradores y propuestas generadas por herramientas automatizadas son apoyo para el trabajo; deben ser revisados por una persona responsable antes de utilizarlos como resultados oficiales o presentarlos a terceros.</p>
        <p>La plataforma no reemplaza asesoría profesional, validaciones regulatorias ni comprobantes emitidos por autoridades o gestores autorizados.</p>
      </section>

      <section>
        <h2>5. Correos e integraciones</h2>
        <p>Algunas funciones pueden enviar correos operativos o invitaciones de calendario a las direcciones indicadas por usuarios autorizados. Si la organización conecta Google Calendar, autoriza a Greenway App a gestionar las invitaciones de los eventos creados o administrados desde la plataforma. El envío depende de la configuración y disponibilidad de los servicios externos.</p>
      </section>

      <section>
        <h2>6. Disponibilidad y cambios</h2>
        <p>Greenway realiza esfuerzos razonables para mantener la plataforma disponible, pero pueden existir interrupciones por mantenimiento, conectividad, incidentes o servicios de terceros. Las funciones pueden actualizarse para mejorar el servicio, la seguridad o el cumplimiento de requisitos aplicables.</p>
      </section>

      <section>
        <h2>7. Suspensión de acceso</h2>
        <p>Greenway o la organización administradora pueden limitar o suspender el acceso cuando detecten un uso no autorizado, riesgos para la seguridad, incumplimiento de estas condiciones o cuando termine la necesidad de acceso al evento o servicio.</p>
      </section>

      <section>
        <h2>8. Consultas</h2>
        <p>Para consultas sobre estas condiciones, escribe a <a href="mailto:gonzalo@greenway.cl">gonzalo@greenway.cl</a> o llama al <a href="tel:+56961253554">+56 9 6125 3554</a>.</p>
      </section>
    </LegalPageShell>
  );
}
