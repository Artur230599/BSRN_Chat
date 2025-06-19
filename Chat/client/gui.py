import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import asyncio
import threading

class ChatGUI:
    def __init__(self, config, messenger):
        self.config = config
        self.messenger = messenger

        # --- GUI setup ---
        self.root = tk.Tk()
        self.root.title(f"SLCP Chat GUI ({self.config.handle})")
        self.root.geometry("600x500")

        # Chat display
        self.chat_display = tk.Text(self.root, state="disabled", width=70, height=20, wrap="word")
        self.chat_display.pack(padx=10, pady=10)

        # Entry for message
        self.entry_msg = tk.Entry(self.root, width=50)
        self.entry_msg.pack(side="left", padx=10, pady=5, expand=True, fill="x")

        # Send button
        self.send_btn = tk.Button(self.root, text="Send", command=self.send_msg_gui)
        self.send_btn.pack(side="left", padx=5)

        # Peer list dropdown
        self.peers_var = tk.StringVar()
        self.peers_menu = ttk.Combobox(self.root, textvariable=self.peers_var, width=15, state="readonly")
        self.peers_menu.pack(side="left", padx=10)
        self.peers_menu["values"] = ["<Refresh...>"]

        # Image send button
        self.img_btn = tk.Button(self.root, text="Send Image", command=self.send_img_gui)
        self.img_btn.pack(side="left", padx=5)

        # Update peers periodically
        self.root.after(2000, self.update_peer_list)

        # Add button bar for Join, Leave, Who
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(padx=10, pady=5, fill="x")

        self.join_btn = tk.Button(btn_frame, text="Join", width=8,
            command=lambda: asyncio.run_coroutine_threadsafe(
                self.messenger.send_join(), asyncio.get_event_loop()))
        self.join_btn.pack(side="left", padx=3)

        self.leave_btn = tk.Button(btn_frame, text="Leave", width=8,
            command=lambda: asyncio.run_coroutine_threadsafe(
                self.messenger.send_leave(), asyncio.get_event_loop()))
        self.leave_btn.pack(side="left", padx=3)

        self.who_btn = tk.Button(btn_frame, text="Who", width=8,
            command=lambda: asyncio.run_coroutine_threadsafe(
                self.messenger.send_who(), asyncio.get_event_loop()))
        self.who_btn.pack(side="left", padx=3)

        # Messenger callbacks
        messenger.set_message_callback(self.display_message)
        messenger.set_image_callback(self.display_image_notice)
        messenger.set_knownusers_callback(self.update_peers_menu)

    def display_message(self, sender, message):
        # Callback, async not needed
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", f"\n💬 {sender}: {message}")
        self.chat_display.config(state="disabled")

    def display_image_notice(self, sender, filename):
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", f"\n🖼️ Image from {sender}: {filename}")
        self.chat_display.config(state="disabled")
        messagebox.showinfo("Image Received", f"Image from {sender} saved:\n{filename}")

    def update_peers_menu(self, user_list):
        # Callback when receive new peer from Messenger
        handles = list({handle for handle, _, _ in user_list if handle != self.config.handle})
        if not handles:
            handles = ["<No peers>"]
        self.peers_menu["values"] = handles
        if handles:
            self.peers_var.set(handles[0])

    def send_msg_gui(self):
        msg = self.entry_msg.get()
        handle = self.peers_var.get()
        if not msg or handle.startswith("<"):
            return
        asyncio.run_coroutine_threadsafe(
            self.messenger.send_message(handle, msg),
            asyncio.get_event_loop()
        )
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", f"\nYou to {handle}: {msg}")
        self.chat_display.config(state="disabled")
        self.entry_msg.delete(0, "end")

    def send_img_gui(self):
        handle = self.peers_var.get()
        if handle.startswith("<"):
            messagebox.showerror("No peer", "Please select a peer!")
            return
        file_path = filedialog.askopenfilename(
            title="Choose image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if file_path:
            asyncio.run_coroutine_threadsafe(
                self.messenger.send_image(handle, file_path),
                asyncio.get_event_loop()
            )
            messagebox.showinfo("Image", f"Sending image to {handle}...")

    def update_peer_list(self):
        asyncio.run_coroutine_threadsafe(
            self.messenger.send_who(),
            asyncio.get_event_loop()
        )
        self.root.after(5000, self.update_peer_list)  # peer list update

    def start(self):
        self.root.mainloop()
