# Manual de Usuario — Client-Server 4 Students (C4SS)

> **v1.0.0** — Un proyecto de [Sxnnyside Scholarships](https://www.sxnnysideproject.com)

¡Bienvenido! Este manual te guiará paso a paso por la instalación, configuración y uso de la aplicación. No te preocupes si eres nuevo en redes — para eso mismo existe este proyecto.

---

## Tabla de Contenidos

1. [¿Qué es esto?](#1-qué-es-esto)
2. [Instalación](#2-instalación)
3. [Iniciar la Aplicación](#3-iniciar-la-aplicación)
4. [El Lanzador](#4-el-lanzador)
5. [Usar el Servidor](#5-usar-el-servidor)
6. [Usar el Cliente](#6-usar-el-cliente)
7. [Temas e Idiomas](#7-temas-e-idiomas)
8. [Archivos de Configuración](#8-archivos-de-configuración)
9. [Solución de Problemas](#9-solución-de-problemas)
10. [Preguntas Frecuentes](#10-preguntas-frecuentes)

---

## 1. ¿Qué es esto?

**Client-Server 4 Students** es una aplicación de escritorio que simula un servidor de archivos, similar a FTP pero mucho más simple. Tiene dos partes:

- **Servidor** — Un programa que espera conexiones y almacena archivos.
- **Cliente** — Un programa que se conecta al servidor para subir o descargar archivos.

Ambas partes tienen interfaces gráficas para que puedas ver todo lo que está pasando.

> **Importante:** Esta es una herramienta educativa. Está diseñada para uso en aulas y laboratorios, no para compartir archivos de verdad por internet.

---

## 2. Instalación

### Lo que necesitas

- **Python 3.12** o más reciente — [Descargar Python](https://www.python.org/downloads/)
- **pip** — Viene incluido con Python.

### Pasos

1. **Descarga el proyecto** (o clónalo con Git):

   ```bash
   git clone https://github.com/HoujouSxnnyside/client-server-4-students.git
   ```

2. **Abre una terminal** y navega a la carpeta del proyecto:

   ```bash
   cd client-server-4-students
   ```

3. **Instala la biblioteca requerida** (PyQt6):

   ```bash
   pip install -r requirements.txt
   ```

   Esto instala **PyQt6**, que proporciona la interfaz gráfica. Es la única biblioteca externa necesaria.

¡Eso es todo — estás listo!

---

## 3. Iniciar la Aplicación

Ejecuta el siguiente comando desde la carpeta del proyecto:

```bash
python main.py
```

Aparecerá la ventana del **Lanzador**.

---

## 4. El Lanzador

El Lanzador es tu punto de partida. Ofrece dos botones grandes:

- **Iniciar como Cliente** — Abre la ventana del Cliente.
- **Iniciar como Servidor** — Abre la ventana del Servidor.

En la parte inferior encontrarás dos menús desplegables:

- **Idioma** — Cambia entre Inglés y Español. El cambio se aplica al instante.
- **Tema** — Cambia entre *Menta Claro* (fondo blanco) y *Menta Oscuro* (fondo oscuro).

Cuando abres una ventana de Cliente o Servidor y luego la cierras, volverás al Lanzador.

---

## 5. Usar el Servidor

### Iniciar el Servidor

1. Haz clic en **Iniciar como Servidor** en el Lanzador.
2. Configura la **Dirección** (por defecto `0.0.0.0` — acepta conexiones de cualquier máquina en la red).
3. Configura el **Puerto** (por defecto `2121`).
4. Haz clic en **Iniciar Servidor**.

El panel de registro mostrará: *"Server started on 0.0.0.0:2121"*.

### Gestionar Usuarios

En el lado derecho de la ventana del Servidor hay una sección de **Gestión de Usuarios**:

- **Agregar un usuario:** Escribe un nombre de usuario y contraseña, luego haz clic en **Agregar Usuario**.
- **Eliminar un usuario:** Selecciona un usuario de la lista y haz clic en **Eliminar**.

Dos cuentas predeterminadas se crean automáticamente:

| Usuario | Contraseña |
|---|---|
| `student` | `student` |
| `teacher` | `teacher` |

### Ver Clientes Conectados

La lista de **Clientes Conectados** muestra cada cliente que está actualmente conectado, identificado por su dirección IP y puerto.

### Ver el Registro

El área principal muestra un registro en tiempo real de todo lo que sucede en el servidor: conexiones, autenticaciones, subidas, descargas y errores.

### Detener el Servidor

Haz clic en **Detener Servidor**. Todas las conexiones activas se cerrarán.

---

## 6. Usar el Cliente

### Conectarse al Servidor

1. Haz clic en **Iniciar como Cliente** en el Lanzador.
2. Completa los campos de conexión:
   - **Servidor** — La dirección del servidor (usa `localhost` si ambos están en la misma máquina).
   - **Puerto** — Debe coincidir con el puerto del servidor (por defecto `2121`).
   - **Usuario** — por ejemplo `student`.
   - **Contraseña** — por ejemplo `student`.
3. Haz clic en **Conectar**.

Si tiene éxito, la barra de estado mostrará *"Authenticated as student"* y se cargará el explorador de archivos.

### Navegar Archivos

- La tabla de archivos muestra el contenido de tu carpeta personal en el servidor.
- Las **Carpetas** están marcadas con el tipo *"Carpeta"*. **Haz doble clic** en una carpeta para entrar.
- Haz clic en **↑ Subir** para volver al directorio padre.
- Haz clic en **Actualizar** para recargar el directorio actual.

### Subir un Archivo

1. Navega a la carpeta donde quieres que vaya el archivo.
2. Haz clic en **Subir**.
3. Aparecerá un diálogo de selección de archivos — elige un archivo de tu computadora.
4. El archivo se transferirá y la lista se actualizará automáticamente.

### Descargar un Archivo

1. Haz clic en un archivo de la tabla para seleccionarlo.
2. Haz clic en **Descargar**.
3. Elige dónde guardarlo en tu computadora.
4. El archivo se transferirá.

### Crear una Carpeta

1. Navega al directorio donde quieres la nueva carpeta.
2. Haz clic en **Nueva Carpeta**.
3. Ingresa un nombre y confirma.
4. El directorio se crea en el servidor y la lista se actualiza.

### Desconectarse

Haz clic en **Desconectar** para cerrar la conexión limpiamente.

---

## 7. Temas e Idiomas

### Cambiar el Tema

Desde el **Lanzador**, usa el menú desplegable **Tema**:

- **Menta Claro** — Fondo blanco con acentos verde menta.
- **Menta Oscuro** — Fondo azul oscuro con acentos verde menta.

El tema se aplica instantáneamente a toda la aplicación.

### Cambiar el Idioma

Desde el **Lanzador**, usa el menú desplegable **Idioma**:

- **English** (Inglés)
- **Español**

Todo el texto de la interfaz se actualiza inmediatamente — no es necesario reiniciar.

Tu tema e idioma preferidos se guardan automáticamente y se restauran la próxima vez que abras la aplicación.

---

## 8. Archivos de Configuración

### `config/settings.json`

Este archivo almacena tus preferencias en JSON legible:

```json
{
    "locale": "es",
    "theme": "mint_dark",
    "server": {
        "host": "0.0.0.0",
        "port": 2121,
        "max_connections": 5
    },
    "client": {
        "default_host": "localhost",
        "default_port": 2121
    }
}
```

Puedes editarlo manualmente si lo prefieres.

### `config/users.json`

Este archivo se genera automáticamente y almacena las cuentas de usuario (contraseñas hasheadas + sales). Normalmente gestionas usuarios a través de la interfaz del Servidor, pero puedes inspeccionar este archivo si tienes curiosidad.

### `server_files/`

Aquí se almacenan los archivos subidos. Cada usuario tiene su propia subcarpeta:

```
server_files/
├── student/
│   ├── tarea.pdf
│   └── apuntes/
└── teacher/
    └── programa.docx
```

---

## 9. Solución de Problemas

| Problema | Solución |
|---|---|
| **"Connection failed"** | Asegúrate de que el servidor esté corriendo y que el host/puerto coincidan. |
| **"Authentication failed"** | Verifica tu usuario y contraseña. Son sensibles a mayúsculas/minúsculas. |
| **El servidor no inicia** | Otro programa puede estar usando el puerto 2121. Prueba un puerto diferente. |
| **La interfaz se ve rota** | Asegúrate de haber instalado `PyQt6>=6.6.0`. Ejecuta `pip install --upgrade PyQt6`. |
| **Los archivos no aparecen** | Haz clic en **Actualizar**. Verifica que estés en el directorio correcto. |
| **Módulo no encontrado** | Ejecuta desde la carpeta raíz del proyecto, no desde dentro de `src/`. |

---

## 10. Preguntas Frecuentes

**P: ¿Puedo usar esto por internet?**
R: Técnicamente sí, pero por favor no lo hagas. Este proyecto no tiene cifrado y está diseñado solo para uso local o en aulas.

**P: ¿Pueden varios clientes conectarse al mismo tiempo?**
R: ¡Sí! El servidor maneja cada cliente en su propio hilo de ejecución.

**P: ¿Dónde se almacenan mis archivos?**
R: Dentro de `server_files/<tu_nombre_de_usuario>/`.

**P: ¿Puedo agregar más idiomas?**
R: ¡Por supuesto! Copia `src/localization/en.json`, traduce los valores y registra el nuevo código en `LocaleManager.SUPPORTED_LOCALES`. Consulta [CONTRIBUTING.md](../CONTRIBUTING.md).

**P: ¿El sistema de contraseñas es seguro?**
R: Usa SHA-256 con una sal aleatoria — suficiente para un aula, pero no para producción. Un sistema real usaría bcrypt o argon2 y transmitiría las contraseñas sobre TLS.

---

**¿Necesitas más ayuda?** Contáctanos en: **[support.sxnnyside@sxnnysideproject.com](mailto:support.sxnnyside@sxnnysideproject.com)**

---

<sub>© 2026 Sxnnyside Scholarships · [Sxnnyside Project](https://www.sxnnysideproject.com)</sub>
