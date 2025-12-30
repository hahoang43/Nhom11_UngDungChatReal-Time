import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading

class ChatGUI:
    def __init__(self, client):
        self.client = client
        self.root = tk.Tk()
        self.root.title("Chat Application - Group 11")
        self.root.geometry("400x500")
        
        self.build_login_screen()
        
        # Set callback for incoming messages
        self.client.on_message_received = self.on_message

    def build_login_screen(self):
        self.clear_screen()
        
        tk.Label(self.root, text="Enter Username:", font=("Arial", 12)).pack(pady=20)
        
        self.username_entry = tk.Entry(self.root, font=("Arial", 12))
        self.username_entry.pack(pady=10)
        self.username_entry.bind("<Return>", lambda event: self.login())
        
        tk.Button(self.root, text="Login", command=self.login, font=("Arial", 12), bg="#4CAF50", fg="white").pack(pady=20)

    def login(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showerror("Error", "Username cannot be empty")
            return
            
        if self.client.connect(username):
            self.build_chat_screen()
        else:
            messagebox.showerror("Error", "Could not connect to server")

    def build_chat_screen(self):
        self.clear_screen()
        
        # Chat History Area
        self.chat_area = scrolledtext.ScrolledText(self.root, state='disabled', font=("Arial", 10))
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Input Area
        input_frame = tk.Frame(self.root)
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        self.msg_entry = tk.Entry(input_frame, font=("Arial", 12))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.msg_entry.bind("<Return>", lambda event: self.send_message())
        
        send_btn = tk.Button(input_frame, text="Send", command=self.send_message, bg="#2196F3", fg="white")
        send_btn.pack(side=tk.RIGHT, padx=5)

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def send_message(self):
        msg = self.msg_entry.get().strip()
        if msg:
            self.client.send_message(msg)
            self.display_message(f"You: {msg}")
            self.msg_entry.delete(0, tk.END)

    def on_message(self, message):
        # Update GUI from background thread safely
        self.root.after(0, self.display_message, message)

    def display_message(self, message):
        if hasattr(self, 'chat_area'):
            self.chat_area.config(state='normal')
            self.chat_area.insert(tk.END, message + "\n")
            self.chat_area.yview(tk.END) # Auto scroll to bottom
            self.chat_area.config(state='disabled')

    def start(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        self.client.disconnect()
        self.root.destroy()
