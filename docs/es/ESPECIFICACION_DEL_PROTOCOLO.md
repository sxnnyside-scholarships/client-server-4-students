# Especificación del Protocolo: CS4S/2.0

## 1. Visión General
El protocolo **Client-Server 4 Students (CS4S)** es un protocolo de red personalizado, de capa de aplicación y basado en líneas de texto, diseñado específicamente para laboratorios educativos de redes. Funciona sobre TCP estándar (y opcionalmente TLS).

El objetivo principal del protocolo es ser **observable**—deliberadamente utiliza la estructura de texto plano UTF-8 para que los estudiantes puedan leer fácilmente las capturas de paquetes (p. ej., en Wireshark) y observar las interacciones del socket.

## 2. Formato del Mensaje
Los mensajes siguen un formato de texto estrictamente definido, con un solo comando por línea.

```text
COMANDO|param1|param2|...\n
```

- **Codificación:** UTF-8
- **Delimitador:** El carácter de barra vertical (`|`) separa el comando y sus argumentos.
- **Terminador:** Un carácter de nueva línea (`\n`) termina cada mensaje de control.

### Excepción de Transmisión Binaria
Para transferencias de datos en masa (p. ej., subir o descargar un archivo), el protocolo abandona momentáneamente el encuadre de nueva línea. El comando de texto que anuncia la transferencia es seguido inmediatamente por bytes crudos que representan el contenido del archivo, dictado por el tamaño del archivo transmitido.

## 3. Comandos del Cliente
Estas son las solicitudes enviadas desde el Cliente al Servidor.

### Ciclo de Vida de la Conexión
- **`HELLO|CS4S/2.0`**
  - **Propósito:** Inicia el protocolo de apretón de manos (handshake).
  - **Respuesta:** `220|OK|CS4S/2.0`
- **`QUIT`**
  - **Propósito:** Termina amablemente la conexión del socket.
  - **Respuesta:** `221|OK|GOODBYE`
- **`PING`**
  - **Propósito:** Sonda de latencia de red para mediciones RTT.
  - **Respuesta:** `200|OK`

### Autenticación
- **`AUTH|<nombre_de_usuario>|<contraseña>`**
  - **Propósito:** Autentica al usuario. Tenga en cuenta que las contraseñas se envían intencionalmente en texto plano a través de TCP estándar para la observación educativa.
  - **Respuesta:** `230|OK|AUTH_OK` o `430|ERROR|AUTH_FAIL`

### Operaciones de Archivo (Sandbox)
- **`LIST`** o **`LIST|<subruta>`**
  - **Propósito:** Solicita un listado de directorio del sandbox aislado del usuario.
  - **Respuesta:** `200|OK|<json_string>`
- **`MKDIR|<nombre_dir>`**
  - **Propósito:** Crea un directorio en el sandbox.
  - **Respuesta:** `250|OK|DONE`
- **`DELETE|<nombre_archivo>`**
  - **Propósito:** Elimina un archivo o directorio.
  - **Respuesta:** `250|OK|DONE`
- **`RENAME|<nombre_viejo>|<nombre_nuevo>`**
  - **Propósito:** Renombra un archivo o directorio.
  - **Respuesta:** `250|OK|DONE`
- **`MOVE|<nombre_archivo>|<dir_destino>`**
  - **Propósito:** Mueve un archivo a un directorio de destino.
  - **Respuesta:** `250|OK|DONE`

### Transferencias Binarias
- **`UPLOAD|<nombre_archivo>|<tamaño>`**
  - **Propósito:** Anuncia un flujo de archivo entrante. El cliente escribe inmediatamente `<tamaño>` bytes al socket después de que el servidor lo reconoce.
  - **Respuesta:** `200|OK|READY` seguido de `250|OK|DONE` después de recibir los bytes.
- **`DOWNLOAD|<nombre_archivo>`**
  - **Propósito:** Solicita un archivo. El servidor responde con el tamaño y luego escribe inmediatamente `<tamaño>` bytes en el socket.
  - **Respuesta:** `200|OK|<tamaño>` seguido por los bytes crudos.

## 4. Códigos de Respuesta del Servidor
Las respuestas del servidor imitan los códigos de estado numéricos estilo HTTP/FTP para facilitar el aprendizaje.

- **`200 CODE_OK`**: Éxito genérico.
- **`220 CODE_GREETING`**: Respuesta al apretón de manos del servidor.
- **`221 CODE_GOODBYE`**: El servidor reconoce la desconexión.
- **`226 CODE_TRANSFER_DONE`**: Fin de la transferencia binaria.
- **`230 CODE_AUTH_OK`**: Autenticación exitosa.
- **`250 CODE_ACTION_OK`**: Operación de archivo/directorio exitosa.
- **`400 CODE_BAD_REQ`**: Solicitud malformada o argumentos faltantes.
- **`401 CODE_UNAUTHORIZED`**: El comando requiere autenticación.
- **`403 CODE_FORBIDDEN`**: Permiso denegado (p. ej., se intentó el cruce de rutas).
- **`404 CODE_NOT_FOUND`**: El archivo o directorio de destino no existe.
- **`409 CODE_CONFLICT`**: El archivo de destino ya existe.
- **`430 CODE_AUTH_FAIL`**: Credenciales incorrectas.
- **`500 CODE_INTERNAL_ERR`**: Excepción en el lado del servidor.
- **`503 CODE_UNAVAILABLE`**: Servidor en capacidad máxima de conexión.
- **`505 CODE_VERSION_ERR`**: Discrepancia de versión de protocolo.

## 5. Seguridad y Extensiones
CS4S implementa Seguridad de Capa de Transporte (TLS) opcional.
Si TLS está activo, el socket TCP en bruto se envuelve utilizando `ssl.wrap_socket` *antes* de que comience el apretón de manos `HELLO`. Esto ofusca por completo el protocolo en texto plano para los rastreadores de paquetes (sniffers), creando un contraste educativo para la demostración en el aula.
