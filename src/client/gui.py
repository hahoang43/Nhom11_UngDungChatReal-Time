import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading

class ChatGUI:
    def __init__(self, client):
        self.client = client
        self.root = tk.Tk()
        self.root.title("Chat Application - Group 11")
        self.root.geometry("450x550")
        self.root.resizable(False, False)
        
        # Center window
        self.center_window()
        
        self.build_login_screen()
        
        # Set callback for incoming messages
        self.client.on_message_received = self.on_message
        self.client.on_login_response = self.handle_login_response

    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def build_login_screen(self):
        self.clear_screen()
        self.is_registering = False
        
        # Title
        title_frame = tk.Frame(self.root)
        title_frame.pack(pady=30)
        tk.Label(title_frame, text="Chat Application", font=("Arial", 20, "bold"), fg="#2196F3").pack()
        tk.Label(title_frame, text="Group 11", font=("Arial", 12), fg="#666").pack()
        
        # Tab frame
        tab_frame = tk.Frame(self.root)
        tab_frame.pack(pady=20)
        
        self.login_btn = tk.Button(tab_frame, text="Đăng Nhập", command=self.show_login, 
                                   font=("Arial", 11, "bold"), bg="#2196F3", fg="white", 
                                   relief=tk.RAISED, padx=20, pady=5)
        self.login_btn.pack(side=tk.LEFT, padx=5)
        
        self.register_btn = tk.Button(tab_frame, text="Đăng Ký", command=self.show_register,
                                      font=("Arial", 11), bg="#E0E0E0", fg="#333",
                                      relief=tk.FLAT, padx=20, pady=5)
        self.register_btn.pack(side=tk.LEFT, padx=5)
        
        # Form frame
        form_frame = tk.Frame(self.root)
        form_frame.pack(pady=20, padx=40, fill=tk.BOTH, expand=True)
        
        # Username
        tk.Label(form_frame, text="Tên đăng nhập:", font=("Arial", 10), anchor="w").pack(fill=tk.X, pady=(10, 5))
        self.username_entry = tk.Entry(form_frame, font=("Arial", 11), relief=tk.SOLID, bd=1)
        self.username_entry.pack(fill=tk.X, pady=(0, 15), ipady=5)
        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus_set())
        
        # Password
        tk.Label(form_frame, text="Mật khẩu:", font=("Arial", 10), anchor="w").pack(fill=tk.X, pady=(0, 5))
        self.password_entry = tk.Entry(form_frame, font=("Arial", 11), show="*", relief=tk.SOLID, bd=1)
        self.password_entry.pack(fill=tk.X, pady=(0, 20), ipady=5)
        self.password_entry.bind("<Return>", lambda event: self.submit())
        
        # Submit button
        self.submit_btn = tk.Button(form_frame, text="Đăng Nhập", command=self.submit,
                                    font=("Arial", 12, "bold"), bg="#4CAF50", fg="white",
                                    relief=tk.FLAT, padx=30, pady=10, cursor="hand2")
        self.submit_btn.pack(pady=10)
        
        # Status label
        self.status_label = tk.Label(form_frame, text="", font=("Arial", 9), fg="red")
        self.status_label.pack(pady=5)
        
        # Focus on username entry
        self.username_entry.focus_set()
        
        # Show login by default
        self.show_login()

    def show_login(self):
        """Switch to login mode"""
        self.is_registering = False
        self.login_btn.config(bg="#2196F3", fg="white", relief=tk.RAISED, font=("Arial", 11, "bold"))
        self.register_btn.config(bg="#E0E0E0", fg="#333", relief=tk.FLAT, font=("Arial", 11))
        self.submit_btn.config(text="Đăng Nhập", bg="#2196F3")
        self.status_label.config(text="")
        self.clear_form()

    def show_register(self):
        """Switch to register mode"""
        self.is_registering = True
        self.register_btn.config(bg="#2196F3", fg="white", relief=tk.RAISED, font=("Arial", 11, "bold"))
        self.login_btn.config(bg="#E0E0E0", fg="#333", relief=tk.FLAT, font=("Arial", 11))
        self.submit_btn.config(text="Đăng Ký", bg="#4CAF50")
        self.status_label.config(text="")
        self.clear_form()

    def clear_form(self):
        """Clear form fields"""
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.username_entry.focus_set()

    def submit(self):
        """Submit login or register"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username:
            self.status_label.config(text="Vui lòng nhập tên đăng nhập!", fg="red")
            self.username_entry.focus_set()
            return
        
        if not password:
            self.status_label.config(text="Vui lòng nhập mật khẩu!", fg="red")
            self.password_entry.focus_set()
            return
        
        # Disable submit button
        self.submit_btn.config(state=tk.DISABLED, text="Đang xử lý...")
        self.status_label.config(text="Đang kết nối...", fg="#2196F3")
        
        # Connect and send login/register
        if self.is_registering:
            if self.client.register(username, password):
                # Registration request sent, wait for response
                pass
            else:
                self.status_label.config(text="Không thể kết nối đến server!", fg="red")
                self.submit_btn.config(state=tk.NORMAL, text="Đăng Ký")
        else:
            if self.client.connect(username, password):
                # Login request sent, wait for response
                pass
            else:
                self.status_label.config(text="Không thể kết nối đến server!", fg="red")
                self.submit_btn.config(state=tk.NORMAL, text="Đăng Nhập")

    def handle_login_response(self, success, message):
        """Handle login/register response from server"""
        self.submit_btn.config(state=tk.NORMAL)
        
        if success:
            self.status_label.config(text="", fg="green")
            self.build_chat_screen()
        else:
            self.status_label.config(text=message, fg="red")
            if self.is_registering:
                self.submit_btn.config(text="Đăng Ký")
            else:
                self.submit_btn.config(text="Đăng Nhập")

    def build_chat_screen(self):
        self.clear_screen()
        self.root.geometry("800x600")
        self.center_window()
        
        self.current_target = "Public" # Can be "Public", "User:Name", or "Group:ID"
        self.chat_histories = {"Public": []} # Store messages for each target locally if needed
        
        # Main PanedWindow
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#E0E0E0")
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar
        self.sidebar = tk.Frame(self.paned, bg="#FFFFFF", width=200)
        self.paned.add(self.sidebar)
        
        # Sidebar Header
        sb_header = tk.Frame(self.sidebar, bg="#2196F3", height=50)
        sb_header.pack(fill=tk.X)
        tk.Label(sb_header, text="Đang hoạt động", fg="white", bg="#2196F3", font=("Arial", 10, "bold")).pack(pady=15)
        
        # Public Chat Button
        self.public_btn = tk.Button(self.sidebar, text="🌐 Chat công khai", 
                                   command=lambda: self.select_target("Public"),
                                   relief=tk.FLAT, bg="#E3F2FD", anchor="w", padx=10, pady=10)
        self.public_btn.pack(fill=tk.X)
        
        # Online Users Section
        tk.Label(self.sidebar, text="NGƯỜI DÙNG", bg="#F5F5F5", font=("Arial", 8, "bold"), fg="#757575", pady=5, padx=10, anchor="w").pack(fill=tk.X)
        self.users_listbox = tk.Listbox(self.sidebar, relief=tk.FLAT, bg="white", borderwidth=0, highlightthickness=0)
        self.users_listbox.pack(fill=tk.BOTH, expand=True)
        self.users_listbox.bind('<<ListboxSelect>>', self.on_user_select)
        
        # Groups Section
        tk.Label(self.sidebar, text="NHÓM", bg="#F5F5F5", font=("Arial", 8, "bold"), fg="#757575", pady=5, padx=10, anchor="w").pack(fill=tk.X)
        self.groups_listbox = tk.Listbox(self.sidebar, relief=tk.FLAT, bg="white", borderwidth=0, highlightthickness=0)
        self.groups_listbox.pack(fill=tk.BOTH, expand=True)
        self.groups_listbox.bind('<<ListboxSelect>>', self.on_group_select)
        
        # Create Group Button
        tk.Button(self.sidebar, text="➕ Tạo nhóm mới", command=self.prompt_create_group,
                  relief=tk.FLAT, bg="#4CAF50", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=5, padx=10)

        # Right Chat Area
        self.chat_main = tk.Frame(self.paned, bg="#F5F5F5")
        self.paned.add(self.chat_main)
        
        # Chat Header
        self.chat_header = tk.Frame(self.chat_main, bg="#FFFFFF", height=50)
        self.chat_header.pack(fill=tk.X)
        self.chat_header.pack_propagate(False)
        
        self.target_label = tk.Label(self.chat_header, text="🌐 Chat công khai", font=("Arial", 12, "bold"), bg="white")
        self.target_label.pack(side=tk.LEFT, padx=15, pady=10)
        
        tk.Button(self.chat_header, text="Đăng Xuất", command=self.logout, 
                  bg="#F44336", fg="white", relief=tk.FLAT, font=("Arial", 9)).pack(side=tk.RIGHT, padx=15)

        # Scrolled Text
        self.chat_area = scrolledtext.ScrolledText(self.chat_main, state='disabled', font=("Arial", 10), wrap=tk.WORD, bg="#F5F5F5", relief=tk.FLAT)
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Input Area
        input_frame = tk.Frame(self.chat_main, bg="#FFFFFF")
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        self.msg_entry = tk.Entry(input_frame, font=("Arial", 11), relief=tk.SOLID, bd=1)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda event: self.send_message())
        
        send_btn = tk.Button(input_frame, text="Gửi", command=self.send_message, bg="#2196F3", fg="white", font=("Arial", 11, "bold"), relief=tk.FLAT, padx=20)
        send_btn.pack(side=tk.RIGHT)
        
        self.configure_chat_tags()
        self.msg_entry.focus_set()
        
        # Register callbacks
        self.client.on_users_list_received = self.update_users_list
        self.client.on_groups_list_received = self.update_groups_list
        self.client.on_server_response = self.handle_server_response

    def select_target(self, target):
        """Switches current chat target"""
        self.current_target = target
        display_name = target
        if target.startswith("User:"):
            display_name = f"👤 {target[5:]}"
            self.public_btn.config(bg="#FFFFFF")
        elif target.startswith("Group:"):
            # Find group name
            group_id = target[6:]
            display_name = f"👥 Nhóm {group_id}"
            self.public_btn.config(bg="#FFFFFF")
        else:
            display_name = "🌐 Chat công khai"
            self.public_btn.config(bg="#E3F2FD")
            
        self.target_label.config(text=display_name)
        # In a real app, we would clear chat area and load history for this target
        self.display_message(f"--- Bạn đang chat ở: {display_name} ---", "server_msg")

    def on_user_select(self, event):
        selection = self.users_listbox.curselection()
        if selection:
            username = self.users_listbox.get(selection[0])
            if username == self.client.username:
                return # Can't chat with self
            self.select_target(f"User:{username}")

    def on_group_select(self, event):
        selection = self.groups_listbox.curselection()
        if selection:
            group_str = self.groups_listbox.get(selection[0])
            # Assuming format "ID: Name"
            group_id = group_str.split(":")[0]
            self.select_target(f"Group:{group_id}")

    def update_users_list(self, users):
        self.root.after(0, self._update_users_ui, users)

    def _update_users_ui(self, users):
        self.users_listbox.delete(0, tk.END)
        for user in users:
            self.users_listbox.insert(tk.END, user)

    def update_groups_list(self, groups):
        self.root.after(0, self._update_groups_ui, groups)

    def _update_groups_ui(self, groups):
        self.groups_listbox.delete(0, tk.END)
        for g in groups:
            self.groups_listbox.insert(tk.END, f"{g['id']}: {g['name']}")

    def prompt_create_group(self):
        from tkinter import simpledialog
        group_name = simpledialog.askstring("Tạo nhóm", "Nhập tên nhóm mới:")
        if group_name:
            self.client.create_group(group_name)

    def handle_server_response(self, type, msg):
        self.root.after(0, lambda: messagebox.showinfo(type, msg))

    def send_message(self):
        msg = self.msg_entry.get().strip()
        if not msg: return
        
        if self.current_target == "Public":
            self.client.send_message(msg)
            self.display_message(f"You: {msg}", "user_msg")
        elif self.current_target.startswith("User:"):
            receiver = self.current_target[5:]
            self.client.send_private(receiver, msg)
            self.display_message(f"[To {receiver}] You: {msg}", "user_msg")
        elif self.current_target.startswith("Group:"):
            group_id = self.current_target[6:]
            self.client.send_group(group_id, msg)
            # We don't display our own group message here as it will be broadcasted back 
            # Or we can display it. Usually server broadcasts back to sender too if wanted.
            self.display_message(f"[To Group {group_id}] You: {msg}", "user_msg")
            
        self.msg_entry.delete(0, tk.END)

    def on_message(self, message, msg_type=None, extra=None):
        # Update GUI from background thread safely
        self.root.after(0, self.display_message, message, msg_type, extra)

    def display_message(self, message, tag=None, extra=None):
        if hasattr(self, 'chat_area'):
            self.chat_area.config(state='normal')
            
            if tag:
                self.chat_area.insert(tk.END, message + "\n", tag)
            elif message.startswith("You:"):
                self.chat_area.insert(tk.END, message + "\n", "user_msg")
            elif message.startswith("Server:") or message.startswith("---"):
                self.chat_area.insert(tk.END, message + "\n", "server_msg")
            else:
                self.chat_area.insert(tk.END, message + "\n")
            
            self.chat_area.yview(tk.END)
            self.chat_area.config(state='disabled')
    
    def configure_chat_tags(self):
        if hasattr(self, 'chat_area'):
            self.chat_area.tag_config("user_msg", foreground="#1976D2", font=("Arial", 10, "bold"))
            self.chat_area.tag_config("server_msg", foreground="#F57C00", font=("Arial", 10, "italic"))

    def start(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def logout(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn đăng xuất?"):
            self.client.disconnect()
            from src.client.client import ChatClient
            self.client = ChatClient()
            self.client.on_message_received = self.on_message
            self.client.on_login_response = self.handle_login_response
            self.root.geometry("450x550")
            self.center_window()
            self.build_login_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def on_close(self):
        self.client.disconnect()
        self.root.destroy()
