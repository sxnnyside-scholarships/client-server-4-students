# Protocol Specification: CS4S/2.0

## 1. Overview
The **Client-Server 4 Students (CS4S)** protocol is a custom, line-based, application-layer networking protocol designed specifically for educational networking laboratories. It runs over standard TCP (and optionally TLS). 

The primary goal of the protocol is to be **observable**—it deliberately uses plain UTF-8 text framing so students can easily read packet captures (e.g., in Wireshark) and observe socket interactions.

## 2. Message Format
Messages follow a strictly defined text format, with a single command per line.

```text
COMMAND|param1|param2|...\n
```

- **Encoding:** UTF-8
- **Delimiter:** The pipe character (`|`) separates the command and its arguments.
- **Terminator:** A newline character (`\n`) terminates every control message.

### Binary Streaming Exception
For bulk data transfers (e.g., uploading or downloading a file), the protocol momentarily abandons newline-framing. The text command announcing the transfer is followed immediately by raw bytes representing the file contents, dictated by the transmitted file size.

## 3. Client Commands
These are the requests sent from the Client to the Server.

### Connection Lifecycle
- **`HELLO|CS4S/2.0`**
  - **Purpose:** Initiates the protocol handshake.
  - **Response:** `220|OK|CS4S/2.0`
- **`QUIT`**
  - **Purpose:** Politely terminates the socket connection.
  - **Response:** `221|OK|GOODBYE`
- **`PING`**
  - **Purpose:** Network latency probe for RTT measurements.
  - **Response:** `200|OK`

### Authentication
- **`AUTH|<username>|<password>`**
  - **Purpose:** Authenticates the user. Note that passwords are intentionally sent in plaintext over standard TCP for educational observation. 
  - **Response:** `230|OK|AUTH_OK` or `430|ERROR|AUTH_FAIL`

### File Operations (Sandbox)
- **`LIST`** or **`LIST|<subpath>`**
  - **Purpose:** Requests a directory listing of the user's isolated sandbox.
  - **Response:** `200|OK|<json_string>`
- **`MKDIR|<dirname>`**
  - **Purpose:** Creates a directory in the sandbox.
  - **Response:** `250|OK|DONE`
- **`DELETE|<filename>`**
  - **Purpose:** Removes a file or directory.
  - **Response:** `250|OK|DONE`
- **`RENAME|<old_name>|<new_name>`**
  - **Purpose:** Renames a file or directory.
  - **Response:** `250|OK|DONE`
- **`MOVE|<filename>|<dest_dir>`**
  - **Purpose:** Moves a file into a target directory.
  - **Response:** `250|OK|DONE`

### Binary Transfers
- **`UPLOAD|<filename>|<size>`**
  - **Purpose:** Announces an incoming file stream. The client immediately writes `<size>` bytes to the socket after the server acknowledges.
  - **Response:** `200|OK|READY` followed by `250|OK|DONE` after bytes are received.
- **`DOWNLOAD|<filename>`**
  - **Purpose:** Requests a file. The server responds with the size, then immediately writes `<size>` bytes to the socket.
  - **Response:** `200|OK|<size>` followed by the raw bytes.

## 4. Server Response Codes
Responses from the server mimic HTTP/FTP-style numeric status codes for ease of learning.

- **`200 CODE_OK`**: Generic success.
- **`220 CODE_GREETING`**: Server handshake response.
- **`221 CODE_GOODBYE`**: Server acknowledging disconnection.
- **`226 CODE_TRANSFER_DONE`**: End of binary transfer.
- **`230 CODE_AUTH_OK`**: Authentication successful.
- **`250 CODE_ACTION_OK`**: File/directory operation successful.
- **`400 CODE_BAD_REQ`**: Malformed request or missing arguments.
- **`401 CODE_UNAUTHORIZED`**: Command requires authentication.
- **`403 CODE_FORBIDDEN`**: Permission denied (e.g., path traversal attempted).
- **`404 CODE_NOT_FOUND`**: Target file or directory does not exist.
- **`409 CODE_CONFLICT`**: Target file already exists.
- **`430 CODE_AUTH_FAIL`**: Bad credentials.
- **`500 CODE_INTERNAL_ERR`**: Server-side exception.
- **`503 CODE_UNAVAILABLE`**: Server at maximum connection capacity.
- **`505 CODE_VERSION_ERR`**: Protocol version mismatch.

## 5. Security & Extensions
CS4S implements optional Transport Layer Security (TLS) wrapping.
If TLS is active, the raw TCP socket is wrapped using `ssl.wrap_socket` *before* the `HELLO` handshake begins. This completely obfuscates the plaintext protocol framing from packet sniffers, creating an educational contrast for classroom demonstration.
