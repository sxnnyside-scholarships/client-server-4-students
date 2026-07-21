# CS4S Educator Guide

Client-Server 4 Students (CS4S) is designed to give students practical, hands-on experience with networking protocols, socket programming, and transport security without getting bogged down in low-level byte fragmentation or multi-threading boilerplate.

## 1. Classroom Integration

CS4S works entirely over Local Area Networks (LAN) and local loopback (127.0.0.1). It requires no cloud servers, DNS setup, or third-party accounts, making it ideal for isolated laboratory environments.

### Setting Up the Lab Server
1. Select a machine to act as the primary Server.
2. Launch the application and click **Start Server**.
3. Note the IP address and Port provided in the server's control panel.
4. Distribute this IP and Port to your students.

### Managing Student Sandboxes
CS4S automatically creates a separate "sandbox" directory for each authenticated user inside the `~/.cs4s/sandbox/` folder on the host server. 
- Students cannot escape this sandbox.
- You can pre-seed these directories with files (e.g., assignment templates or packet captures) before the lab begins.

## 2. Recommended Laboratory Exercises

### Lab A: Plaintext Protocol Observation
**Objective:** Understand how unencrypted application-layer protocols transmit data.
1. Have students launch their Client application and connect to the server (with TLS disabled).
2. Instruct them to open the **Protocol Inspector** panel.
3. As they browse directories and download files, have them observe the `COMMAND|param` syntax.
4. **Discussion Point:** Have students execute a login. Point out that the `AUTH` command transmits their password in plain text.

### Lab B: Transport Layer Security (TLS) Contrast
**Objective:** Demonstrate the opacity of encrypted transport tunnels.
1. Enable TLS in the server's Settings panel (requires restarting the server listener).
2. Have students reconnect.
3. When they open the Protocol Inspector, all application data (like the `AUTH` command) will be represented as `[Encrypted TLS Record]`.
4. **Discussion Point:** Discuss how the underlying TCP connection remains identical, but packet-sniffers (like Wireshark) can no longer parse the application layer.

### Lab C: Socket State Lifecycles
**Objective:** Correlate client UI actions with long-lived TCP socket states.
1. Have students initiate a large file upload (e.g., a 100MB dummy file).
2. Use the Server's connection monitor to watch the client socket transition from `IDLE` to `TRANSFERRING`.
3. Disconnect the client mid-transfer to observe the server's exception handling and cleanup routines.

## 3. Curriculum Sequencing
We recommend introducing CS4S after teaching the OSI model and basic TCP/UDP fundamentals, but *before* teaching HTTP. CS4S provides a simpler stepping stone to application-layer protocols because its command structure is significantly less verbose than HTTP headers.
