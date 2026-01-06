import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import threading
import os
from datetime import datetime

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
        self.client.on_file_received = self.on_file_received
        
        # File transfer tracking
        self.file_transfers = {}  # filename -> {'progress': progress_bar, 'status': label, 'frame': frame}

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
        self.root.geometry("600x700")
        self.center_window()
        
        # Header
        header_frame = tk.Frame(self.root, bg="#2196F3", height=50)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Left side - Username
        tk.Label(header_frame, text=f"Chat - {self.client.username}", 
                font=("Arial", 14, "bold"), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=15, pady=10)
        
        # Right side - Logout button
        logout_btn = tk.Button(header_frame, text="Đăng Xuất", command=self.logout,
                              font=("Arial", 10, "bold"), bg="#F44336", fg="white",
                              relief=tk.FLAT, padx=15, pady=5, cursor="hand2")
        logout_btn.pack(side=tk.RIGHT, padx=15, pady=8)
        
        # Chat History Area
        chat_frame = tk.Frame(self.root)
        chat_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.chat_area = scrolledtext.ScrolledText(chat_frame, state='disabled', 
                                                   font=("Arial", 10), wrap=tk.WORD,
                                                   bg="#F5F5F5", relief=tk.FLAT, bd=2)
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        # Input Area
        input_frame = tk.Frame(self.root, bg="#FFFFFF")
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        self.msg_entry = tk.Entry(input_frame, font=("Arial", 11), relief=tk.SOLID, bd=1)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda event: self.send_message())
        
        send_btn = tk.Button(input_frame, text="Gửi", command=self.send_message, 
                            bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
                            relief=tk.FLAT, padx=20, cursor="hand2")
        send_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # File button
        file_btn = tk.Button(input_frame, text="📎 File", command=self.send_file_dialog,
                            bg="#FF9800", fg="white", font=("Arial", 10, "bold"),
                            relief=tk.FLAT, padx=15, cursor="hand2")
        file_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Configure chat tags
        self.configure_chat_tags()
        
        # Focus on message entry
        self.msg_entry.focus_set()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def send_message(self):
        msg = self.msg_entry.get().strip()
        if msg:
            self.client.send_message(msg)
            self.display_message(f"You: {msg}")
            self.msg_entry.delete(0, tk.END)
    
    def send_file_dialog(self):
        """Mở dialog để chọn file và gửi"""
        filepath = filedialog.askopenfilename(
            title="Chọn file để gửi",
            filetypes=[("All files", "*.*")]
        )
        
        if filepath:
            try:
                filename = os.path.basename(filepath)
                filesize = os.path.getsize(filepath)
                size_mb = filesize / (1024 * 1024)
                
                if size_mb > 10:  # Cảnh báo nếu file > 10MB
                    if not messagebox.askyesno("Cảnh báo", 
                        f"File {filename} có kích thước {size_mb:.2f} MB.\nBạn có muốn tiếp tục?"):
                        return
                
                # Tạo progress bar trong chat
                self._create_file_transfer_ui(filename, filesize, is_sending=True)
                
                # Gửi file với progress callback
                def update_progress(sent, total):
                    progress = (sent / total) * 100
                    self.root.after(0, self._update_file_progress, filename, progress, sent, total)
                
                # Gửi file trong thread riêng để không block UI
                def send_file_thread():
                    success = self.client.send_file(filepath, progress_callback=update_progress)
                    self.root.after(0, self._file_send_complete, filename, success)
                
                threading.Thread(target=send_file_thread, daemon=True).start()
                
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi khi gửi file: {e}")
    
    def _create_file_transfer_ui(self, filename, filesize, is_sending=True):
        """Tạo UI cho file transfer (progress bar và status)"""
        if not hasattr(self, 'chat_area'):
            return
        
        self.chat_area.config(state='normal')
        
        # Tạo frame cho file transfer
        file_frame = tk.Frame(self.chat_area, bg="#E3F2FD", relief=tk.RAISED, bd=1)
        
        # File info
        info_label = tk.Label(file_frame, text=f"📎 {filename} ({self._format_size(filesize)})", 
                             font=("Arial", 9, "bold"), bg="#E3F2FD", anchor="w")
        info_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Progress bar
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(file_frame, variable=progress_var, maximum=100, length=300)
        progress_bar.pack(fill=tk.X, padx=5, pady=2)
        
        # Status label
        status_label = tk.Label(file_frame, text="Đang gửi...", font=("Arial", 8), 
                               bg="#E3F2FD", fg="#666")
        status_label.pack(fill=tk.X, padx=5, pady=2)
        
        # Lưu vào window để có thể cập nhật
        window = self.chat_area.window_create(tk.END, window=file_frame)
        self.chat_area.insert(tk.END, "\n")
        
        # Lưu reference
        if filename not in self.file_transfers:
            self.file_transfers[filename] = {}
        self.file_transfers[filename] = {
            'progress_var': progress_var,
            'progress_bar': progress_bar,
            'status_label': status_label,
            'frame': file_frame,
            'window': window,
            'is_sending': is_sending
        }
        
        self.chat_area.yview(tk.END)
        self.chat_area.config(state='disabled')
    
    def _update_file_progress(self, filename, progress, sent, total):
        """Cập nhật progress bar"""
        if filename in self.file_transfers:
            self.file_transfers[filename]['progress_var'].set(progress)
            status_text = f"Đang gửi... {self._format_size(sent)} / {self._format_size(total)} ({progress:.1f}%)"
            self.file_transfers[filename]['status_label'].config(text=status_text)
    
    def _file_send_complete(self, filename, success):
        """Cập nhật UI khi gửi file hoàn tất"""
        if filename in self.file_transfers:
            if success:
                self.file_transfers[filename]['progress_var'].set(100)
                self.file_transfers[filename]['status_label'].config(
                    text="✓ Đã gửi thành công", fg="#4CAF50"
                )
                # Đổi màu frame thành xanh lá
                self.file_transfers[filename]['frame'].config(bg="#E8F5E9")
            else:
                self.file_transfers[filename]['status_label'].config(
                    text="✗ Gửi thất bại", fg="#F44336"
                )
                self.file_transfers[filename]['frame'].config(bg="#FFEBEE")
    
    def _format_size(self, size_bytes):
        """Format file size"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
    
    def on_file_received(self, file_data):
        """Xử lý khi nhận được file info từ server"""
        sender = file_data.get('sender', 'Unknown')
        filename = file_data.get('filename', 'unknown')
        filesize = file_data.get('filesize', 0)
        message = file_data.get('message', f"{sender} đã gửi file: {filename}")
        
        # Hiển thị file info trong chat
        self.display_message(f"{message} ({self._format_size(filesize)})")
        
        # Tạo UI cho file đã nhận
        self._create_file_transfer_ui(filename, filesize, is_sending=False)
        
        # Đánh dấu là đã nhận
        if filename in self.file_transfers:
            self.file_transfers[filename]['progress_var'].set(100)
            self.file_transfers[filename]['status_label'].config(
                text="✓ Đã nhận", fg="#4CAF50"
            )
            self.file_transfers[filename]['frame'].config(bg="#E8F5E9")

    def on_message(self, message):
        # Update GUI from background thread safely
        self.root.after(0, self.display_message, message)

    def display_message(self, message):
        if hasattr(self, 'chat_area'):
            self.chat_area.config(state='normal')
            
            # Format message with colors
            if message.startswith("You:"):
                self.chat_area.insert(tk.END, message + "\n", "user_msg")
            elif message.startswith("Server:"):
                self.chat_area.insert(tk.END, message + "\n", "server_msg")
            else:
                self.chat_area.insert(tk.END, message + "\n")
            
            self.chat_area.yview(tk.END) # Auto scroll to bottom
            self.chat_area.config(state='disabled')
    
    def configure_chat_tags(self):
        """Configure text tags for chat messages"""
        if hasattr(self, 'chat_area'):
            self.chat_area.tag_config("user_msg", foreground="#1976D2", font=("Arial", 10, "bold"))
            self.chat_area.tag_config("server_msg", foreground="#F57C00", font=("Arial", 10, "italic"))

    def start(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def logout(self):
        """Logout and return to login screen"""
        # Ask for confirmation
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn đăng xuất?"):
            # Disconnect from server
            self.client.disconnect()
            
            # Recreate client for new connection
            from src.client.client import ChatClient
            self.client = ChatClient()
            self.client.on_message_received = self.on_message
            self.client.on_login_response = self.handle_login_response
            
            # Reset window size
            self.root.geometry("450x550")
            self.center_window()
            
            # Return to login screen
            self.build_login_screen()
    
    def on_close(self):
        """Handle window close event"""
        self.client.disconnect()
        self.root.destroy()
