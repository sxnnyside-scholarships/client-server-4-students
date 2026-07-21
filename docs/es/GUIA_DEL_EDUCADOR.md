# Guía del Educador CS4S

Client-Server 4 Students (CS4S) está diseñado para brindar a los estudiantes experiencia práctica con protocolos de red, programación de sockets y seguridad de transporte sin empantanarse en la fragmentación de bytes de bajo nivel o código repetitivo multihilo.

## 1. Integración en el Aula

CS4S funciona completamente a través de Redes de Área Local (LAN) y el bucle local (127.0.0.1). No requiere servidores en la nube, configuración de DNS ni cuentas de terceros, lo que lo hace ideal para entornos de laboratorio aislados.

### Configuración del Servidor de Laboratorio
1. Seleccione una máquina para actuar como el Servidor principal.
2. Inicie la aplicación y haga clic en **Iniciar Servidor**.
3. Anote la dirección IP y el Puerto proporcionados en el panel de control del servidor.
4. Distribuya esta IP y Puerto a sus estudiantes.

### Gestión de Sandboxes de Estudiantes
CS4S crea automáticamente un directorio "sandbox" separado para cada usuario autenticado dentro de la carpeta `~/.cs4s/sandbox/` en el servidor anfitrión.
- Los estudiantes no pueden escapar de este sandbox.
- Puede pre-sembrar estos directorios con archivos (p. ej., plantillas de tareas o capturas de paquetes) antes de que comience el laboratorio.

## 2. Ejercicios de Laboratorio Recomendados

### Laboratorio A: Observación de Protocolo en Texto Plano
**Objetivo:** Entender cómo los protocolos de capa de aplicación sin cifrar transmiten datos.
1. Haga que los estudiantes inicien su aplicación Cliente y se conecten al servidor (con TLS desactivado).
2. Indíqueles que abran el panel **Inspector de Protocolo**.
3. A medida que navegan por los directorios y descargan archivos, pídales que observen la sintaxis `COMANDO|param`.
4. **Punto de Discusión:** Pida a los estudiantes que inicien sesión. Señale que el comando `AUTH` transmite su contraseña en texto plano.

### Laboratorio B: Contraste con Seguridad de Capa de Transporte (TLS)
**Objetivo:** Demostrar la opacidad de los túneles de transporte cifrados.
1. Habilite TLS en el panel de Configuración del servidor (requiere reiniciar el servidor).
2. Pida a los estudiantes que se vuelvan a conectar.
3. Cuando abran el Inspector de Protocolo, todos los datos de la aplicación (como el comando `AUTH`) se representarán como `[Registro TLS Cifrado]`.
4. **Punto de Discusión:** Discuta cómo la conexión TCP subyacente sigue siendo idéntica, pero los analizadores de paquetes (como Wireshark) ya no pueden analizar la capa de aplicación.

### Laboratorio C: Ciclos de Vida del Estado del Socket
**Objetivo:** Correlacionar las acciones de la interfaz del cliente con los estados de socket TCP de larga duración.
1. Pida a los estudiantes que inicien una carga de archivo grande (p. ej., un archivo ficticio de 100 MB).
2. Use el monitor de conexión del Servidor para observar cómo el socket del cliente pasa de `IDLE` a `TRANSFERRING`.
3. Desconecte al cliente a mitad de la transferencia para observar el manejo de excepciones y las rutinas de limpieza del servidor.

## 3. Secuenciación del Currículo
Recomendamos introducir CS4S después de enseñar el modelo OSI y los fundamentos básicos de TCP/UDP, pero *antes* de enseñar HTTP. CS4S proporciona un trampolín más simple hacia los protocolos de la capa de aplicación debido a que su estructura de comandos es significativamente menos verbosa que los encabezados HTTP.
