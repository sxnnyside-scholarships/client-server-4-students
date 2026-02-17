# User Manual — Client-Server 4 Students (C4SS)

> **v1.0.0** — A project by [Sxnnyside Scholarships](https://www.sxnnysideproject.com)

Welcome! This manual will guide you through installing, configuring, and using the application step by step. Don't worry if you're new to networking — that's exactly what this project is for.

---

## Table of Contents

1. [What Is This?](#1-what-is-this)
2. [Installation](#2-installation)
3. [Starting the Application](#3-starting-the-application)
4. [The Launcher](#4-the-launcher)
5. [Using the Server](#5-using-the-server)
6. [Using the Client](#6-using-the-client)
7. [Themes and Languages](#7-themes-and-languages)
8. [Configuration Files](#8-configuration-files)
9. [Troubleshooting](#9-troubleshooting)
10. [Frequently Asked Questions](#10-frequently-asked-questions)

---

## 1. What Is This?

**Client-Server 4 Students** is a small desktop application that simulates a file server, similar to FTP but much simpler. It has two parts:

- **Server** — A program that waits for connections and stores files.
- **Client** — A program that connects to the server to upload or download files.

Both parts have graphical interfaces so you can see everything that's happening.

> **Important:** This is an educational tool. It is designed for use in classrooms and labs, not for real-world file sharing over the internet.

---

## 2. Installation

### What You Need

- **Python 3.12** or newer — [Download Python](https://www.python.org/downloads/)
- **pip** — Comes bundled with Python.

### Steps

1. **Download the project** (or clone it with Git):

   ```bash
   git clone https://github.com/HoujouSxnnyside/client-server-4-students.git
   ```

2. **Open a terminal** and navigate to the project folder:

   ```bash
   cd client-server-4-students
   ```

3. **Install the required library** (PyQt6):

   ```bash
   pip install -r requirements.txt
   ```

   This installs **PyQt6**, which provides the graphical interface. It's the only external library needed.

That's it — you're ready to go!

---

## 3. Starting the Application

Run the following command from the project folder:

```bash
python main.py
```

The **Launcher** window will appear.

---

## 4. The Launcher

The Launcher is your starting point. It offers two large buttons:

- **Start as Client** — Opens the Client window.
- **Start as Server** — Opens the Server window.

At the bottom you'll find two dropdowns:

- **Language** — Switch between English and Spanish. The change applies instantly.
- **Theme** — Switch between *Mint Light* (white background) and *Mint Dark* (dark background).

When you open a Client or Server window and later close it, you'll return to the Launcher.

---

## 5. Using the Server

### Starting the Server

1. Click **Start as Server** in the Launcher.
2. Set the **Bind Address** (default `0.0.0.0` — accepts connections from any machine on the network).
3. Set the **Port** (default `2121`).
4. Click **Start Server**.

The log panel will show: *"Server started on 0.0.0.0:2121"*.

### Managing Users

The right side of the Server window has a **User Management** section:

- **Add a user:** Type a username and password, then click **Add User**.
- **Remove a user:** Select a user from the list and click **Remove**.

Two default accounts are created automatically:

| Username | Password |
|---|---|
| `student` | `student` |
| `teacher` | `teacher` |

### Viewing Connected Clients

The **Connected Clients** list shows every client that is currently connected, identified by their IP address and port.

### Viewing Logs

The main area shows a real-time log of everything happening on the server: connections, authentications, uploads, downloads, and errors.

### Stopping the Server

Click **Stop Server**. All active connections will be dropped.

---

## 6. Using the Client

### Connecting to the Server

1. Click **Start as Client** in the Launcher.
2. Fill in the connection fields:
   - **Host** — The server's address (use `localhost` if both are on the same machine).
   - **Port** — Must match the server's port (default `2121`).
   - **Username** — e.g. `student`.
   - **Password** — e.g. `student`.
3. Click **Connect**.

If successful, the status bar will show *"Authenticated as student"* and the file browser will load.

### Browsing Files

- The file table shows the contents of your personal folder on the server.
- **Folders** are marked with the type *"Folder"*. **Double-click** a folder to enter it.
- Click **↑ Up** to go back to the parent directory.
- Click **Refresh** to reload the current directory.

### Uploading a File

1. Navigate to the folder where you want the file to go.
2. Click **Upload**.
3. A file picker dialog appears — choose a file from your computer.
4. The file will be transferred and the list will refresh automatically.

### Downloading a File

1. Click on a file in the table to select it.
2. Click **Download**.
3. Choose where to save it on your computer.
4. The file will be transferred.

### Creating a Folder

1. Navigate to the directory where you want the new folder.
2. Click **New Folder**.
3. Enter a name and confirm.
4. The directory is created on the server and the list refreshes.

### Disconnecting

Click **Disconnect** to close the connection cleanly.

---

## 7. Themes and Languages

### Changing the Theme

From the **Launcher**, use the **Theme** dropdown:

- **Mint Light** — White background with mint-green accents.
- **Mint Dark** — Dark navy background with mint-green accents.

The theme applies instantly to the entire application.

### Changing the Language

From the **Launcher**, use the **Language** dropdown:

- **English**
- **Español**

All UI text updates immediately — no restart needed.

Your preferred theme and language are saved automatically and restored next time you open the application.

---

## 8. Configuration Files

### `config/settings.json`

This file stores your preferences in human-readable JSON:

```json
{
    "locale": "en",
    "theme": "mint_light",
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

You can edit it manually if you prefer.

### `config/users.json`

This file is auto-generated and stores user accounts (hashed passwords + salts). You normally manage users through the Server UI, but you can inspect this file if you're curious.

### `server_files/`

This is where uploaded files are stored. Each user gets a subfolder:

```
server_files/
├── student/
│   ├── homework.pdf
│   └── notes/
└── teacher/
    └── syllabus.docx
```

---

## 9. Troubleshooting

| Problem | Solution |
|---|---|
| **"Connection failed"** | Make sure the server is running and the host/port match. |
| **"Authentication failed"** | Check your username and password. They are case-sensitive. |
| **Server won't start** | Another program may be using port 2121. Try a different port. |
| **GUI looks broken** | Make sure you installed `PyQt6>=6.6.0`. Run `pip install --upgrade PyQt6`. |
| **Files not showing** | Click **Refresh**. Check you're in the right directory. |
| **Module not found** | Run from the project root folder, not from inside `src/`. |

---

## 10. Frequently Asked Questions

**Q: Can I use this over the internet?**
A: Technically yes, but please don't. This project has no encryption and is designed for local or classroom use only.

**Q: Can multiple clients connect at the same time?**
A: Yes! The server handles each client in its own thread.

**Q: Where are my files stored?**
A: Inside `server_files/<your_username>/`.

**Q: Can I add more languages?**
A: Absolutely! Copy `src/localization/en.json`, translate the values, and register the new code in `LocaleManager.SUPPORTED_LOCALES`. See [CONTRIBUTING.md](../CONTRIBUTING.md).

**Q: Is the password system secure?**
A: It uses SHA-256 with a random salt — good enough for a classroom, but not for production. A real system would use bcrypt or argon2 and transmit passwords over TLS.

---

**Need more help?** Contact us at: **[support.sxnnyside@sxnnysideproject.com](mailto:support.sxnnyside@sxnnysideproject.com)**

---

<sub>© 2026 Sxnnyside Scholarships · [Sxnnyside Project](https://www.sxnnysideproject.com)</sub>
