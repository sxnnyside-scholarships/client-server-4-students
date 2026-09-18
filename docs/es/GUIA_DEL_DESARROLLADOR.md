# Guía del Desarrollador CS4S

¡Bienvenido al repositorio de Client-Server 4 Students (CS4S)! Esta guía explica cómo extender, probar y empaquetar la aplicación.

## 1. Organización del Repositorio

CS4S separa las responsabilidades claramente en módulos distintos:

- **`src/core/`**: Utilidades compartidas como `config.py` y `protocol.py`. Tanto el cliente como el servidor dependen de estos.
- **`src/network/client/`**: El gestor de conexión del lado del cliente y los hilos de fondo del socket.
- **`src/network/server/`**: El motor TCP multihilo del servidor y los despachadores de comandos.
- **`src/storage/`**: Utilidades vinculadas al disco para autenticar usuarios (`auth.py`) y gestionar el sandbox (`file_manager.py`).
- **`src/ui/`**: Componentes GUI de PyQt6. ¡Evite poner lógica de negocio en estos archivos!
- **`tests/`**: Suites de pruebas unitarias e integración usando `pytest`.

## 2. Flujo de Trabajo de Ingeniería

Usamos **uv** para la gestión rápida y determinista de dependencias y **just** como ejecutor de tareas estándar.

### Configuración del Entorno
```bash
# Instalar dependencias, entorno virtual y hooks de git
just install

# Ejecutar la aplicación
just dev
```

### Análisis Estático y Control de Calidad
Antes de enviar una solicitud de extracción (pull request), asegúrese de que el código base pase nuestras compuertas de calidad automatizadas:
```bash
# Ejecutar la compuerta de calidad completa (formato, lint, tipos, pruebas)
just check

# O verificaciones individuales:
just format     # Formateo con Ruff
just lint       # Linting con Ruff
just typecheck  # Verificación de tipos con MyPy
just test       # Pruebas automatizadas con PyTest
```

### Pruebas
Aplicamos pruebas sin estado. No confíe en rutas fijas o acceso a redes externas.
```bash
just test
```

- Las **pruebas unitarias** validan la lógica de forma aislada (p. ej., `test_auth.py`).
- Las **pruebas de integración** activan servidores efímeros locales y validan flujos de socket completos (p. ej., `test_protocol.py`).

## 3. Extender el Protocolo

Si desea agregar un nuevo comando de protocolo (p. ej., `COMPRESS`), debe modificar el código en tres lugares:

1. **Definición del Protocolo**: Agregue la constante del comando en `src/core/protocol.py`.
2. **Despachador del Servidor**: Implemente la lógica en `src/network/server/handlers/` y asígnela en `src/network/server/dispatcher.py`.
3. **Operaciones del Cliente**: Exponga el comando a través de `src/network/client/operations.py` para que la GUI pueda activarlo.

Siempre actualice `docs/PROTOCOL_SPECIFICATION.md` (o su equivalente en español) cuando modifique el protocolo.

## 4. Empaquetado y Distribución

CS4S incluye un robusto script de distribución que utiliza PyInstaller para empaquetar PyQt6 y los activos de la aplicación.

```bash
# Generar ejecutable nativo
just build
```
Esto genera una aplicación portable en el directorio `dist/` adecuada para Windows, macOS o Linux, según el sistema operativo anfitrión.
