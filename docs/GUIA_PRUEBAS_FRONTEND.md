# Guia de pruebas frontend - EcoEvent 360

Esta guia sirve para probar manualmente todo lo implementado en el frontend de EcoEvent 360 por rol, modulo y flujo completo.

> Fecha de referencia: 2026-05-29  
> Frontend: Next.js App Router + TypeScript + Tailwind  
> API esperada: `http://localhost:8000/api/v1`

## 1. Objetivo

Validar que el frontend permita operar la plataforma completa implementada hasta ahora:

- Landing publica.
- Login JWT.
- Layout privado por rol.
- Dashboard admin con fallback.
- CRUD administrativo de clientes, usuarios, servicios y eventos.
- Detalle operativo del evento.
- Servicios contratados, zonas, personal y tareas.
- Worker mobile.
- Incidencias y evidencias.
- Residuos y resumen ambiental.
- Huella de carbono, factores y consumos.
- Encuestas Google Forms/Sheets e importacion CSV.
- QR con fallback.
- Dashboard consolidado del evento.
- Reportes PDF con fallback profesional.

## 2. Preparacion del entorno

### 2.1 Levantar PostgreSQL

Desde la raiz del proyecto:

```powershell
docker compose up -d postgres
docker compose ps
```

### 2.2 Levantar backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app
```

Healthcheck:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

### 2.3 Crear SUPER_ADMIN inicial

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.scripts.create_super_admin
```

Credenciales por defecto si no cambiaste `.env`:

```text
Email: admin@ecoevent.cl
Password: 123456
Rol: SUPER_ADMIN
```

### 2.4 Levantar frontend

```powershell
cd frontend
npm run dev
```

Frontend:

```text
http://localhost:3000
```

Variable esperada en `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## 3. Datos minimos para probar todo

### 3.1 Cliente

Ruta:

```text
/admin/clientes/nuevo
```

Datos sugeridos:

```text
Razon social: Productora Sur Eventos
RUT: 76.123.456-7
Contacto: Maria Gonzalez
Email: contacto@productora.cl
Telefono: +56912345678
Direccion: Temuco, Chile
Industria:  
Notas: Cliente de prueba QA
```

Validar:

- Se crea sin error.
- Aparece en `/admin/clientes`.
- Se puede ver detalle.
- Se puede editar.
- Se puede desactivar con confirmacion.

### 3.2 Usuarios

Ruta:

```text
/admin/usuarios/nuevo
```

Crear:

```text
Nombre: Admin Demo
Email: admin.demo@ecoevent.cl
Password: 123456
Rol: ADMIN
Cliente: vacio
```

```text
Nombre: Cliente Demo
Email: cliente.demo@ecoevent.cl
Password: 123456
Rol: CLIENT
Cliente: Productora Sur Eventos
```

```text
Nombre: Supervisor Demo
Email: supervisor.demo@ecoevent.cl
Password: 123456
Rol: SUPERVISOR
Cliente: vacio o Productora Sur Eventos
```

```text
Nombre: Worker Demo
Email: worker.demo@ecoevent.cl
Password: 123456
Rol: WORKER
Cliente: vacio o Productora Sur Eventos
```

Validar:

- No se muestra `password_hash`.
- Si role = CLIENT, exige cliente.
- ADMIN no puede crear SUPER_ADMIN.
- SUPER_ADMIN si puede crear cualquier rol.
- WORKER y SUPERVISOR aparecen disponibles para asignar a eventos.

Importante:

- En Personal solo aparecen usuarios activos con rol `WORKER` o `SUPERVISOR`.
- Usuarios `CLIENT` no son personal operativo.

### 3.3 Servicios

Ruta:

```text
/admin/servicios/nuevo
```

Crear:

```text
Nombre: Punto limpio
Categoria: Residuos
Descripcion: Gestion y segregacion de residuos reciclables
Unidad: unidad
Precio base: 150000
```

```text
Nombre: Banos quimicos
Categoria: Sanitario
Unidad: unidad
Precio base: 90000
```

Validar:

- Se listan.
- Se editan.
- Se desactivan.
- Precio negativo muestra error.

### 3.4 Evento

Ruta:

```text
/admin/eventos/nuevo
```

Datos sugeridos:

```text
Cliente: Productora Sur Eventos
Nombre: Festival QA EcoEvent
Tipo: Festival
Descripcion: Evento de prueba integral
Lugar: Parque Central
Direccion: Av. Prueba 123
Ciudad: Temuco
Region: Araucania
Pais: Chile
Fecha inicio: manana 09:00
Fecha termino: manana 20:00
Asistentes estimados: 500
Estado: PLANNING
```

Validar:

- Queda asociado al cliente.
- En `/admin/eventos` aparece el cliente correcto.
- El detalle muestra cliente, fecha, ubicacion y asistentes.

## 4. Pruebas publicas y Auth

### 4.1 Landing

Ruta:

```text
/
```

Validar:

- Carga visual profesional.
- Hero muestra `EcoEvent 360`.
- Boton `Ingresar` lleva a `/login`.
- Cards de beneficios visibles.
- Responsive en mobile.

### 4.2 Login--------------------------------

Ruta:

```text
/login
```

Probar:

```text
admin@ecoevent.cl
123456
```

Validar:

- Login exitoso.
- Guarda token.
- Llama a `/auth/me`.
- Redirige segun rol.
- Credenciales malas muestran error.
- Backend apagado muestra error de conexion.

## 5. Pruebas por rol

### 5.1 SUPER_ADMIN

Credencial:

```text
admin@ecoevent.cl / 123456
```

Debe poder:

- Ver dashboard admin.
- Gestionar clientes, usuarios, servicios y eventos.
- Crear usuarios SUPER_ADMIN.
- Gestionar factores de emision.
- Gestionar todos los tabs del evento.
- Generar reportes.

Rutas:

```text
/admin/dashboard
/admin/clientes
/admin/usuarios
/admin/servicios
/admin/eventos
/admin/huella/factores
/admin/residuos/tipos
```

### 5.2 ADMIN

Credencial:

```text
admin.demo@ecoevent.cl / 123456
```

Debe poder:

- Gestionar clientes, usuarios, servicios y eventos.
- Gestionar operacion del evento.
- Generar reportes.

Validar:

- No puede crear/promover SUPER_ADMIN.
- No ve opciones que solo son SUPER_ADMIN.

### 5.3 CLIENT

Credencial:

```text
cliente.demo@ecoevent.cl / 123456
```

Rutas:

```text
/client/mis-eventos
/client/indicadores
/client/evidencias
/client/reportes
/client/cuenta
```

Validar:

- No ve menu Admin.
- No ve botones Crear/Editar/Eliminar internos.
- Ve informacion en modo lectura si la ruta existe.
- Si no hay datos, ve EmptyState profesional.

### 5.4 SUPERVISOR

Credencial:

```text
supervisor.demo@ecoevent.cl / 123456
```

Rutas:

```text
/supervisor/eventos
/supervisor/eventos/{event_id}
/worker/mis-tareas
/worker/reportar-incidencia
/worker/subir-evidencia
/worker/registrar-residuo
/worker/registrar-consumo
```

Debe poder:

- Ver eventos asignados.
- Gestionar zonas/tareas/incidencias/evidencias/residuos/huella segun permisos.
- No ver CRUD global administrativo.

### 5.5 WORKER

Credencial:

```text
worker.demo@ecoevent.cl / 123456
```

Rutas:

```text
/worker/mis-tareas
/worker/tareas/{task_id}
/worker/reportar-incidencia
/worker/subir-evidencia
/worker/registrar-residuo
/worker/registrar-consumo
/worker/cuenta
```

Debe poder:

- Ver tareas propias.
- Iniciar y completar tareas.
- Reportar incidencia.
- Subir evidencia.
- Registrar residuo.
- Registrar consumo.

Validar:

- Vista mobile first.
- No ve Admin ni Reportes.
- No ve tareas ajenas.

## 6. CRUD administrativo

### 6.1 Clientes

Rutas:

```text
/admin/clientes
/admin/clientes/nuevo
/admin/clientes/{id}
/admin/clientes/{id}/editar
```

Checklist:

- [ ] Listado carga.
- [ ] Buscador funciona.
- [ ] Crear cliente.
- [ ] Ver detalle.
- [ ] Ver eventos asociados.
- [ ] Editar cliente.
- [ ] Desactivar cliente.
- [ ] EmptyState si no hay datos.
- [ ] ErrorState si backend falla.

### 6.2 Usuarios

Rutas:

```text
/admin/usuarios
/admin/usuarios/nuevo
/admin/usuarios/{id}/editar
```

Checklist:

- [ ] Listado carga.
- [ ] Filtro por rol.
- [ ] Filtro por estado.
- [ ] Crear CLIENT exige cliente.
- [ ] Crear WORKER/SUPERVISOR.
- [ ] Editar usuario.
- [ ] Cambiar password opcional.
- [ ] Desactivar usuario.
- [ ] No se muestra `password_hash`.

### 6.3 Servicios

Rutas:

```text
/admin/servicios
/admin/servicios/nuevo
/admin/servicios/{id}/editar
```

Checklist:

- [ ] Listado carga.
- [ ] Crear servicio.
- [ ] Precio negativo muestra error.
- [ ] Editar servicio.
- [ ] Desactivar servicio.

### 6.4 Eventos

Rutas:

```text
/admin/eventos
/admin/eventos/nuevo
/admin/eventos/{id}
/admin/eventos/{id}/editar
```

Checklist:

- [ ] Listado carga.
- [ ] Cliente aparece correctamente.
- [ ] Crear evento exige cliente.
- [ ] Fecha inicio menor que termino.
- [ ] Asistentes no negativos.
- [ ] Ver detalle.
- [ ] Editar evento.
- [ ] Cambiar estado.
- [ ] Cancelar evento si corresponde.

## 7. Detalle operativo del evento

Ruta admin:

```text
/admin/eventos/{event_id}
```

Ruta supervisor:

```text
/supervisor/eventos/{event_id}
```

Tabs esperados:

- Resumen.
- Servicios.
- Zonas.
- Personal.
- Tareas.
- Incidencias.
- Evidencias.
- Residuos.
- Huella.
- Encuestas.
- Alertas.
- Reportes.

### 7.1 Resumen / Dashboard

Validar:

- [ ] KPIs operativos.
- [ ] Tareas totales/completadas.
- [ ] Incidencias abiertas/resueltas.
- [ ] Residuos kg y recuperacion.
- [ ] Huella tCO2e.
- [ ] Encuestas si existen.
- [ ] Graficos.
- [ ] Si `/events/{id}/dashboard` no existe, usa fallback.

### 7.2 Servicios contratados

Flujo:

1. Tab Servicios.
2. Agregar servicio.
3. Seleccionar `Punto limpio`.
4. Cantidad `3`.
5. Guardar.

Validar:

- [ ] Servicio aparece.
- [ ] Total se calcula.
- [ ] Editar cantidad/precio/notas.
- [ ] Quitar con confirmacion.
- [ ] Roles sin permiso no ven acciones.

### 7.3 Zonas

Crear:

```text
Acceso Norte
Patio Comida
```

Validar:

- [ ] Lista en cards/tabla.
- [ ] Crear zona.
- [ ] Editar zona.
- [ ] Eliminar si no tiene datos asociados.
- [ ] No duplicar nombre si backend valida.

### 7.4 Personal

Flujo:

1. Tab Personal.
2. Asignar `Worker Demo`.
3. Rol evento: `Operador residuos`.
4. Asignar `Supervisor Demo`.

Validar:

- [ ] Solo aparecen WORKER/SUPERVISOR.
- [ ] No aparecen CLIENT.
- [ ] No duplica asignacion.
- [ ] Personal asignado se lista.
- [ ] Si no aparece nadie, revisar rol activo y cliente/evento.

### 7.5 Tareas

Crear:

```text
Titulo: Instalar punto limpio
Zona: Acceso Norte
Responsable: Worker Demo
Prioridad: HIGH
```

Validar admin/supervisor:

- [ ] Crear tarea.
- [ ] Filtrar por estado/prioridad/zona/responsable.
- [ ] Ver detalle.
- [ ] Editar.
- [ ] Cambiar estado.
- [ ] Completar tarea.
- [ ] `completed_at` aparece.

Validar worker:

- [ ] `/worker/mis-tareas` lista tarea propia.
- [ ] Iniciar tarea.
- [ ] Completar tarea.
- [ ] No ve tareas ajenas.

### 7.6 Incidencias

Crear:

```text
Zona: Patio Comida
Tipo: WASTE
Prioridad: HIGH
Titulo: Contenedor desbordado
Descripcion: Se detecta acumulacion de residuos en zona de comida
```

Validar:

- [ ] Crear incidencia.
- [ ] Ver en tabla.
- [ ] Filtros.
- [ ] Ver detalle.
- [ ] Editar/asignar.
- [ ] Resolver con solucion.
- [ ] Cerrar.
- [ ] Worker reporta desde `/worker/reportar-incidencia`.

### 7.7 Evidencias

Archivos:

- JPG.
- PNG.
- PDF.

Validar:

- [ ] Subir evidencia.
- [ ] Asociar a evento.
- [ ] Asociar a tarea/incidencia si aplica.
- [ ] Preview imagen/PDF.
- [ ] Galeria carga.
- [ ] Eliminar con confirmacion segun permiso.
- [ ] Worker sube desde `/worker/subir-evidencia`.

### 7.8 Residuos

Registrar:

```text
Zona: Patio Comida
Tipo: Plastico/carton/organico o tipo backend
Peso kg: 25
Destino: RECYCLING
```

Validar:

- [ ] Registro aparece.
- [ ] Summary actualiza total kg.
- [ ] Recuperado kg y tasa.
- [ ] Graficos por tipo/destino/zona.
- [ ] Filtros.
- [ ] Editar.
- [ ] Eliminar/anular.
- [ ] Worker registra desde `/worker/registrar-residuo`.

### 7.9 Huella y consumos

Crear factor en:

```text
/admin/huella/factores
```

Ejemplo:

```text
Nombre: Diesel Chile
Categoria: TRANSPORT
Unidad: L
Factor: 2.68
Scope: SCOPE_1
Activo: true
```

Registrar carbono:

```text
Categoria: TRANSPORT
Scope: SCOPE_1
Fuente: Generador diesel
Valor actividad: 100
Unidad: L
Factor: Diesel Chile
```

Validar:

- [ ] Estimacion previa visible.
- [ ] Tabla muestra kgCO2e.
- [ ] Summary kgCO2e/tCO2e.
- [ ] Graficos por categoria/scope/fuente.
- [ ] Editar recalcula.
- [ ] Eliminar/anular.

Consumos:

```text
Combustible: DIESEL, 50 L
Energia: GRID, 120 kWh
Agua: NETWORK, 5 m3
```

Worker:

```text
/worker/registrar-consumo
```

Validar:

- [ ] Selecciona tipo consumo.
- [ ] Formulario cambia segun tipo.
- [ ] Valores mayores que 0.

### 7.10 Encuestas

Crear encuesta:

```text
Titulo: Encuesta satisfaccion Festival QA
Descripcion: Encuesta a asistentes
Google Form URL: https://forms.gle/demo
Google Sheet URL: https://docs.google.com/spreadsheets/d/demo
Estado: ACTIVE
```

CSV de prueba:

```csv
fecha,zona,transporte,limpieza,banos,separo_residuos,nota_general,comentarios
2026-05-29,Acceso Norte,Metro,5,4,SI,5,Muy buena organizacion
2026-05-29,Patio Comida,Auto,4,3,NO,4,Faltaron puntos limpios
```

Validar:

- [ ] Crear encuesta.
- [ ] Editar encuesta.
- [ ] Cerrar encuesta.
- [ ] Importar CSV.
- [ ] Ver respuestas.
- [ ] Ver resumen.
- [ ] Graficos por zona/transporte/problemas.
- [ ] QR funciona o muestra fallback profesional.

### 7.11 Reportes

Validar:

- [ ] Preview ejecutiva carga.
- [ ] Checklist de secciones carga.
- [ ] Generar reporte final.
- [ ] Si backend devuelve PDF blob, descarga.
- [ ] Si devuelve `pdf_url`, abre/descarga.
- [ ] Si devuelve metadata, refresca listado.
- [ ] Ver detalle.
- [ ] Descargar.
- [ ] Marcar entregado si backend existe.
- [ ] Anular con confirmacion.
- [ ] CLIENT/SUPERVISOR solo ven/descargan segun permiso.

## 8. Seguridad visual por rol

Validar:

- [ ] SUPER_ADMIN ve todo.
- [ ] ADMIN no puede crear SUPER_ADMIN.
- [ ] CLIENT no ve acciones internas.
- [ ] SUPERVISOR no ve CRUD global.
- [ ] WORKER no ve admin ni reportes.
- [ ] No se muestra `password_hash`.
- [ ] Botones de eliminar/generar no aparecen si el rol no debe usarlos.

## 9. Responsive

Probar con DevTools:

```text
390 x 844
768 x 1024
1440 x 900
```

Validar:

- [ ] Sidebar mobile abre/cierra.
- [ ] Worker usa cards, no tablas complejas.
- [ ] Tablas admin tienen scroll horizontal.
- [ ] Modales no se salen de pantalla.
- [ ] Texto no se superpone.
- [ ] Botones quedan visibles.

## 10. Errores esperados

Probar:

- Backend apagado.
- Email invalido.
- Password corto.
- Precio negativo.
- Fecha inicio mayor a termino.
- Peso negativo.
- Actividad carbono negativa.
- Archivo no permitido.
- CSV no valido.
- Endpoint no implementado para QR/reportes/dashboard.

Validar:

- [ ] ErrorState claro.
- [ ] EmptyState profesional.
- [ ] No hay pantalla blanca.
- [ ] No hay errores runtime en consola.

## 11. Checklist final global

### Publico/Auth

- [ ] Landing.
- [ ] Login.
- [ ] Logout.
- [ ] Redireccion por rol.
- [ ] Sesion persistente.

### Admin

- [ ] Dashboard.
- [ ] Clientes.
- [ ] Usuarios.
- [ ] Servicios.
- [ ] Eventos.

### Operacion

- [ ] Servicios contratados.
- [ ] Zonas.
- [ ] Personal.
- [ ] Tareas.
- [ ] Worker mobile.
- [ ] Supervisor eventos.

### Terreno

- [ ] Incidencias.
- [ ] Evidencias.
- [ ] Residuos.
- [ ] Consumos.

### Ambiental

- [ ] Waste summary.
- [ ] Waste charts.
- [ ] Carbon summary.
- [ ] Carbon charts.
- [ ] Factores.

### Experiencia y entrega

- [ ] Encuestas.
- [ ] CSV.
- [ ] QR/fallback.
- [ ] Dashboard evento.
- [ ] Reportes.

### Calidad

- [ ] LoadingState.
- [ ] ErrorState.
- [ ] EmptyState.
- [ ] ConfirmDialog.
- [ ] Modales responsive.
- [ ] Sin errores consola.
- [ ] `npm run typecheck` OK.

## 12. Comandos finales de validacion

Frontend:

```powershell
cd frontend
npm run typecheck
npm run dev
```

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m compileall app
alembic current
uvicorn app.main:app
```

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

## 13. Notas importantes

- Algunos modulos tienen fallback profesional si el backend aun no expone endpoints agregados: QR, dashboards avanzados y reportes PDF.
- Para que Personal muestre usuarios disponibles, deben existir usuarios activos con rol `WORKER` o `SUPERVISOR`.
- Para que Worker vea tareas, debe estar asignado al evento y tener tareas asignadas.
- Para que Client vea datos, su usuario debe tener `client_id`.
- Un `403` puede ser correcto segun rol.
- Un `404` de endpoint no implementado debe mostrar fallback o ErrorState, no romper la pagina.
