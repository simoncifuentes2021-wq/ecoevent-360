# Diagnóstico formal del bootstrap Alembic

## Hallazgo reproducido

La cadena actual sirve para una base histórica ya preparada, pero no permite
declarar soporte de instalación limpia.

1. `20260528_0001_initial_schema.py` no ejecuta SQL: `upgrade()` y
   `downgrade()` contienen únicamente `pass`. Su comentario indica que sólo
   marca como baseline un esquema creado previamente desde
   `base_datos/ecoevent_360_schema.sql`.
2. En una base vacía, `20260601_0002_add_audit_logs.py` intenta primero
   `CREATE TABLE audit_logs`. Su primera columna usa
   `DEFAULT uuid_generate_v4()`.
3. Sin la extensión `uuid-ossp`, el primer error es que la función
   `uuid_generate_v4()` no existe.
4. Si se instala esa extensión y se repite, la creación todavía falla porque
   las claves foráneas presuponen `users(id)`, `events(id)` y `clients(id)`.
5. La base existente sí contiene esos objetos y está marcada hasta
   `20260722_0035`; por eso puede aplicar la cadena posterior. Una base vacía no
   tiene el esquema que `0001` afirma representar.

No se modificaron migraciones históricas ni `20260722_0034`/`0035`, no se
ejecutó downgrade y no se aplicó una reparación posterior a `0035`.

## Qué necesita realmente el esquema inicial

El archivo SQL incluye las extensiones `uuid-ossp` y `pgcrypto`; nueve enums
(`user_role`, `event_status`, `task_status`, `incident_status`,
`priority_level`, `waste_destination`, `carbon_scope`, `survey_status` y
`report_status`); 22 tablas base desde `clients` hasta `reports`; índices y
claves foráneas; seis funciones de contexto/autorización; activación de RLS y
políticas para tablas operativas y catálogos.

También hay una inconsistencia verificable: el archivo activa RLS y crea una
política para `audit_logs`, pero no crea esa tabla. Por ello
`ecoevent_360_schema.sql` es una fuente histórica útil, pero **no puede
considerarse hoy un bootstrap autónomo verificado**. Además, las migraciones
posteriores amplían roles y esquema, por lo que su salida debe compararse con
la base vigente, no asumirse equivalente.

## Estrategia propuesta (no aplicada): alternativa A

Crear un artefacto de bootstrap oficial, inmutable y versionado para
instalaciones nuevas:

1. Derivar y revisar un SQL base autocontenido que cree extensiones, enums,
   tablas, índices, funciones y políticas en orden válido, sin incluir objetos
   que correspondan a migraciones posteriores.
2. Ejecutarlo dentro de una base PostgreSQL vacía y una transacción controlada.
3. Verificar catálogo, restricciones y RLS; sólo entonces marcar
   `20260528_0001` mediante `alembic stamp`.
4. Ejecutar `alembic upgrade head` y comparar el esquema resultante contra una
   base existente saneada mediante un diff estructural reproducible.

### Tratamiento por entorno

- **Instalaciones existentes:** conservan la cadena y su `alembic_version`; no
  se reaplica el bootstrap ni se reescribe historia.
- **Instalaciones nuevas y CI:** crean una base efímera, ejecutan el bootstrap,
  hacen `stamp 0001`, actualizan a `head` y corren pruebas. CI debe fallar ante
  cualquier diferencia de catálogo.
- **Supabase:** ejecutar el bootstrap con un rol con permisos suficientes para
  extensiones y DDL; validar previamente qué extensiones están disponibles.
  Las políticas deben probarse también con los roles de aplicación.
- **Pruebas:** mantener una ruta sobre la base histórica y otra de instalación
  limpia; ambas deben terminar en el mismo fingerprint de esquema.
- **Recuperación:** usar base nueva o snapshot previo; si falla antes del
  `stamp`, descartar la base parcial. No estampar una ejecución incompleta.
- **Evitar divergencia:** una única especificación versionada, checksum,
  inventario de objetos y comparación automática contra `head`. Todo cambio
  posterior sigue entrando por Alembic.

Editar `0001` o cualquier migración ya aplicada cambiaría su significado sin
actualizar las bases que ya la registraron, produciría instalaciones con el
mismo revision ID pero esquemas distintos y haría inseguras auditorías,
recuperaciones y despliegues. La alternativa B sólo sería preferible si no se
puede construir un baseline fiel; C debe reservarse para un proyecto de
migración explícito con compatibilidad y recuperación probadas.

## Reproducción mínima

En una base PostgreSQL vacía:

```text
alembic upgrade 20260528_0001
alembic upgrade 20260601_0002
```

El segundo comando falla primero por `uuid_generate_v4()` si falta
`uuid-ossp`; habilitarla sólo revela después la ausencia de las tablas
referenciadas. Esto demuestra que una migración nueva posterior a `0035` no
puede reparar el punto de arranque.
