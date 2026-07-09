# Formularios Publicos

## Crear un show o sesion

1. Entrar como `ADMIN`, `SUPER_ADMIN` o `SUPERVISOR` asignado al evento.
2. Abrir el evento.
3. Ir a la pestaña `Programacion`.
4. Crear una sesion/show con nombre, fecha, horario y venue si aplica.

La sesion queda asociada al evento. Un formulario puede apuntar a todo el evento o a una sesion especifica.

## Crear un formulario

1. Abrir el evento.
2. Ir a la pestaña `Formularios`.
3. Presionar `Crear formulario`.
4. Elegir tipo:
   - `TRANSPORT_SURVEY`
   - `BIKE_ZONE_REGISTRATION`
   - `EXPERIENCE_SURVEY`
   - `CUSTOM`
5. Seleccionar sesion si el formulario corresponde a un show especifico.
6. Activar seleccion de idioma si se necesita pantalla previa.
7. Crear con plantilla.

El formulario se crea como borrador si no se publica explicitamente. Los formularios `DRAFT`, `CLOSED` o fuera de fecha no se muestran al publico.

## Publicar y cerrar

En la pestaña `Formularios`:

- `Publicar`: cambia el formulario a `ACTIVE`.
- `Cerrar`: cambia el formulario a `CLOSED`.

Solo los formularios `ACTIVE`, dentro de `opens_at` y `closes_at` cuando existan, pueden abrirse y recibir respuestas.

## Abrir el formulario publico

Cada formulario tiene una ruta:

```text
/f/[slug]
```

Ejemplo:

```text
/f/transporte-show-1
```

Si el formulario requiere idioma y no viene `lang`, primero se muestra el selector:

```text
/f/transporte-show-1
```

Luego se carga traducido con:

```text
/f/transporte-show-1?lang=en
```

Idiomas soportados por defecto:

- `es`
- `en`
- `pt`
- `ko`

Si falta una traduccion, el sistema intenta usar el idioma por defecto y luego el label base del campo.

## Probar submit publico

Endpoint:

```http
POST /api/v1/public/forms/{slug}/submit
```

Body:

```json
{
  "language": "es",
  "answers": {
    "email": "persona@example.com",
    "transport_mode": "metro"
  }
}
```

Errores por campo:

```json
{
  "detail": [
    {
      "field_key": "email",
      "message": "Correo inválido"
    }
  ]
}
```

Validaciones actuales:

- `TEXT` y `TEXTAREA`: deben ser texto y respetar `max_length`.
- `EMAIL`: debe tener formato de correo.
- `PHONE`: permite `+`, numeros, espacios y guiones.
- `NUMBER`: debe ser numero y respetar `min_value`/`max_value`.
- `DATE`: debe ser fecha ISO.
- `YES_NO` y `CHECKBOX`: deben ser boolean.
- `SELECT` y `RADIO`: el valor debe existir en opciones.
- `MULTI_SELECT`: debe ser lista y cada valor debe existir en opciones.
- `RATING_1_5`: numero entre 1 y 5.
- `RATING_1_7`: numero entre 1 y 7.
- `FILE`: no esta soportado en formularios publicos por ahora.

## Multilenguaje

El formulario tiene:

- `default_language`
- `available_languages`
- `requires_language_selection`

El publico puede elegir idioma antes de responder. La respuesta guarda el idioma seleccionado en `form_responses.language`.

## QR de formularios

Desde la pestaña `Formularios`, cada formulario tiene accion `QR`.

Acciones disponibles:

- Generar QR general del formulario.
- Generar QR por idioma si el formulario tiene mas de un idioma disponible.
- Descargar PNG.
- Copiar link publico.

Targets:

```text
{PUBLIC_APP_URL}/f/{public_slug}
```

Para idioma:

```text
{PUBLIC_APP_URL}/f/{public_slug}?lang=en
```

Si `PUBLIC_APP_URL` o `FRONTEND_PUBLIC_URL` no estan configurados en backend, se usa:

```text
http://localhost:3000
```

Los archivos PNG se guardan localmente cuando R2 no esta configurado:

```text
uploads/qrcodes
```

En produccion se recomienda configurar R2 igual que evidencias. Si las variables R2 estan completas, los QR se suben a R2 y `file_url` guarda la URL publica. El endpoint de descarga redirige al archivo remoto.

Reglas por rol:

- `ADMIN` y `SUPER_ADMIN`: crear, listar, descargar y eliminar QR.
- `SUPERVISOR` asignado: crear, listar y descargar QR. No elimina desde la UI.
- `CLIENT`: puede listar/descargar QR de sus eventos, pero no crear ni eliminar.

Bike Zone deja preparado QR personal con target:

```text
{PUBLIC_APP_URL}/bike-zone/{code}
```

No se crea pantalla publica nueva para esa ruta en esta fase.

## Que ve cada rol

### Admin y Super Admin

- Crear formularios.
- Publicar y cerrar.
- Ver respuestas completas.
- Ver resumen.
- Exportar CSV.
- Operar Bike Zone.

### Supervisor asignado

- Gestionar formularios del evento asignado.
- Ver respuestas completas.
- Operar Bike Zone del evento asignado.

### Supervisor no asignado

- No puede gestionar formularios de ese evento.

### Cliente

- Puede ver formularios de sus eventos.
- Puede ver summary anonimizado.
- No puede listar respuestas completas.
- No recibe `raw_data`, emails, telefonos ni nombres desde endpoints de respuestas.

### Publico

- Solo puede abrir formularios `ACTIVE` disponibles.
- Solo recibe datos visuales y campos publicos.
- No recibe IDs internos de evento, sesion, campos u opciones.
- Puede enviar respuestas publicas.
