"""
RTSP Client with GUI
Connects to RTSP server and displays video stream
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import socket
import threading
import time
from PIL import Image, ImageTk
import io
from rtp_packet import RTPPacket

class RTSPClient:
    """RTSP Client with GUI Interface"""
    
    RTSP_VER = "RTSP/1.0"
    
    def __init__(self):
        # Connection settings
        self.server_addr = "127.0.0.1"
        self.server_port = 8554
        self.rtp_port = self.get_available_port()
        self.filename = ""
        
        # RTSP connection
        self.rtsp_socket = None
        self.rtp_socket = None
        self.seq_num = 0
        self.session_id = None
        self.request_sent = -1
        self.teardown_acked = 0
        
        # Video playback
        self.current_frame = None
        self.frame_count = 0
        self.playing = False
        
        # Threading
        self.rtp_thread = None
        self.rtp_running = False
        
        # Setup GUI
        self.setup_gui()
        
        # Connect to server on startup
        self.connect_to_server()
    
    def get_available_port(self, start_port=25000):
        """Find an available RTP port"""
        import socket
        for port in range(start_port, start_port + 100):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_socket.bind(('', port))
                test_socket.close()
                return port
            except socket.error:
                continue
        return start_port  # Fallback
    
    def setup_gui(self):
        """Setup GUI interface"""
        self.root = tk.Tk()
        self.root.title("🎬 Nirob's RTSP Video Player - Enhanced UI")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)
        self.root.configure(bg='#0d1117')  # GitHub dark theme
        
        # Set window icon (if available)
        try:
            self.root.iconbitmap(default='🎬')
        except:
            pass
        
        # Enhanced style configuration with modern theme
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern button styles with glassmorphism effect
        style.configure('TButton', 
                       font=('Segoe UI', 10, 'bold'),
                       foreground='white',
                       background='#21262d',
                       borderwidth=2,
                       relief='flat',
                       padding=(10, 5))
        style.map('TButton',
                 background=[('active', '#585b70'),
                           ('pressed', '#45475a')])
                           
        # Setup button - Modern blue theme
        style.configure('Setup.TButton',
                       background='#0969da',
                       foreground='white',
                       borderwidth=2,
                       relief='flat')
        style.map('Setup.TButton',
                 background=[('active', '#1f6feb'),
                           ('pressed', '#0550ae')])
                           
        # Play button - Green theme
        style.configure('Play.TButton',
                       background='#16a34a',
                       foreground='white')
        style.map('Play.TButton',
                 background=[('active', '#22c55e'),
                           ('pressed', '#15803d')])
                           
        # Pause button - Orange theme
        style.configure('Pause.TButton',
                       background='#ea580c',
                       foreground='white')
        style.map('Pause.TButton',
                 background=[('active', '#f97316'),
                           ('pressed', '#c2410c')])
                           
        # Stop button - Red theme
        style.configure('Stop.TButton',
                       background='#dc2626',
                       foreground='white')
        style.map('Stop.TButton',
                 background=[('active', '#ef4444'),
                           ('pressed', '#b91c1c')])
                           
        # Connect button - Purple theme
        style.configure('Connect.TButton',
                       background='#7c3aed',
                       foreground='white')
        style.map('Connect.TButton',
                 background=[('active', '#8b5cf6'),
                           ('pressed', '#6d28d9')])
        
        # Label styles
        style.configure('TLabel', 
                       font=('Arial', 9), 
                       background='#1e1e2e', 
                       foreground='#cdd6f4')
                       
        # LabelFrame styles
        style.configure('TLabelframe', 
                       background='#1e1e2e',
                       foreground='#f38ba8',
                       borderwidth=2)
        style.configure('TLabelframe.Label',
                       background='#1e1e2e',
                       foreground='#f38ba8',
                       font=('Arial', 9, 'bold'))
                       
        # Entry styles
        style.configure('TEntry',
                       font=('Arial', 9),
                       foreground='#cdd6f4',
                       fieldbackground='#313244',
                       borderwidth=1,
                       insertcolor='#f38ba8')
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connection frame
        self.setup_connection_frame(main_frame)
        
        # Video display frame
        self.setup_video_frame(main_frame)
        
        # Control buttons frame
        self.setup_control_frame(main_frame)
        
        # Status frame
        self.setup_status_frame(main_frame)
    
    def setup_connection_frame(self, parent):
        """Setup connection controls"""
        conn_frame = ttk.LabelFrame(parent, text="🔗 Connection Settings", padding=5)
        conn_frame.pack(fill=tk.X, pady=(0, 5))
        conn_frame.configure(style='TLabelframe')
        
        # Server settings
        ttk.Label(conn_frame, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=(0, 2))
        self.server_entry = ttk.Entry(conn_frame, width=10)
        self.server_entry.insert(0, self.server_addr)
        self.server_entry.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(0, 2))
        self.port_entry = ttk.Entry(conn_frame, width=6)
        self.port_entry.insert(0, str(self.server_port))
        self.port_entry.grid(row=0, column=3, padx=(0, 5))
        
        ttk.Label(conn_frame, text="Video:").grid(row=0, column=4, sticky=tk.W, padx=(0, 2))
        self.video_entry = ttk.Entry(conn_frame, width=12)
        self.video_entry.insert(0, "nirob.mjpeg")
        self.video_entry.grid(row=0, column=5, padx=(0, 5))
        
        # Connect button with purple theme
        self.connect_btn = ttk.Button(conn_frame, text="🔗 Connect", 
                                    command=self.connect_to_server, style='Connect.TButton')
        self.connect_btn.grid(row=0, column=6)
    
    def setup_video_frame(self, parent):
        """Setup video display area"""
        video_frame = ttk.LabelFrame(parent, text="📺 Video Display", padding=5)
        video_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        video_frame.configure(style='TLabelframe')
        
        # Enhanced video canvas with modern styling
        self.video_canvas = tk.Canvas(video_frame, bg='#0d1117', width=500, height=300,
                                    highlightthickness=3, 
                                    highlightcolor='#58a6ff',
                                    relief='solid',
                                    bd=2)
        self.video_canvas.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # Enhanced welcome message with nirob branding
        self.video_canvas.create_text(250, 150, 
                                    text="🎬 Nirob's Video Player\n📺 Ready for MP4 Streaming\n✨ Enhanced RTSP/RTP Lab\n\n🔵 SETUP → ▶️ PLAY", 
                                    fill='#58a6ff', 
                                    font=('Segoe UI', 14, 'bold'), 
                                    justify=tk.CENTER)
    
    def setup_control_frame(self, parent):
        """Setup playback controls"""
        control_frame = ttk.LabelFrame(parent, text="🎮 Playback Controls", padding=5)
        control_frame.pack(fill=tk.X, pady=(0, 5))
        control_frame.configure(style='TLabelframe')
        
        # Modern control buttons with enhanced styling
        self.setup_btn = ttk.Button(control_frame, text="🔧 SETUP VIDEO", 
                                  command=self.setup_video, state=tk.DISABLED, 
                                  width=12, style='Setup.TButton')
        self.setup_btn.pack(side=tk.LEFT, padx=(5, 5))
        
        self.play_btn = ttk.Button(control_frame, text="▶️ PLAY NIROB.MP4", 
                                 command=self.play_video, state=tk.DISABLED, 
                                 width=15, style='Play.TButton')
        self.play_btn.pack(side=tk.LEFT, padx=(5, 5))
        
        self.pause_btn = ttk.Button(control_frame, text="⏸️ PAUSE", 
                                  command=self.pause_video, state=tk.DISABLED, 
                                  width=10, style='Pause.TButton')
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        self.stop_btn = ttk.Button(control_frame, text="⏹️ STOP", 
                                 command=self.stop_video, state=tk.DISABLED, 
                                 width=10, style='Stop.TButton')
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # Colorful frame counter
        self.frame_label = ttk.Label(control_frame, text="📊 Frame: 0",
                                   font=('Arial', 9, 'bold'))
        self.frame_label.pack(side=tk.RIGHT)
    
    def setup_status_frame(self, parent):
        """Setup status display"""
        status_frame = ttk.LabelFrame(parent, text="📊 Status Log", padding=3)
        status_frame.pack(fill=tk.X)
        status_frame.configure(style='TLabelframe')
        
        # Modern terminal-like status area
        self.status_text = tk.Text(status_frame, height=5, 
                                  bg='#161b22', fg='#7ee787', 
                                  font=('Cascadia Code', 9), wrap=tk.WORD,
                                  insertbackground='#58a6ff',
                                  selectbackground='#264f78',
                                  selectforeground='#ffffff',
                                  relief='flat', bd=3,
                                  highlightthickness=1,
                                  highlightcolor='#30363d')
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Scrollbar for status
        scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_message("🚀 Nirob's Enhanced RTSP Client Initialized")
        self.log_message("🎬 Ready for nirob.mp4 streaming with MP4 support")
        self.log_message("✨ Enhanced UI with modern design loaded")
    
    def log_message(self, message):
        """Add message to status log with colors"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Insert timestamp in cyan
        self.status_text.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        
        # Color-code different message types
        if message.startswith('✅') or 'OK' in message or 'Connected' in message:
            self.status_text.insert(tk.END, f"{message}\n", 'success')
        elif message.startswith('❌') or 'Error' in message or 'failed' in message:
            self.status_text.insert(tk.END, f"{message}\n", 'error')
        elif message.startswith('📤') or 'request' in message.lower():
            self.status_text.insert(tk.END, f"{message}\n", 'request')
        elif message.startswith('📨') or 'response' in message.lower():
            self.status_text.insert(tk.END, f"{message}\n", 'response')
        else:
            self.status_text.insert(tk.END, f"{message}\n", 'info')
        
        # Configure text tags for colors
        self.status_text.tag_configure('timestamp', foreground='#89b4fa')
        self.status_text.tag_configure('success', foreground='#a6e3a1')
        self.status_text.tag_configure('error', foreground='#f38ba8')
        self.status_text.tag_configure('request', foreground='#fab387')
        self.status_text.tag_configure('response', foreground='#cba6f7')
        self.status_text.tag_configure('info', foreground='#cdd6f4')
        
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def connect_to_server(self):
        """Connect to RTSP server"""
        try:
            # Get connection parameters
            self.server_addr = self.server_entry.get()
            self.server_port = int(self.port_entry.get())
            self.filename = self.video_entry.get()
            
            # Create RTSP socket
            self.rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.rtsp_socket.connect((self.server_addr, self.server_port))
            
            self.log_message(f"✅ Connected to RTSP server: {self.server_addr}:{self.server_port}")
            self.log_message(f"🎯 Ready to stream {self.filename} with enhanced quality")
            
            # Enable controls with color feedback
            self.setup_btn.config(state=tk.NORMAL)
            self.connect_btn.config(text="✅ Connected", state=tk.DISABLED)
            
        except Exception as e:
            self.log_message(f"❌ Connection failed: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect to server:\n{e}")
    
    def send_rtsp_request(self, request_code):
        """Send RTSP request to server"""
        if request_code == "SETUP" and self.rtsp_socket:
            threading.Thread(target=self.recv_rtsp_reply, daemon=True).start()
            
            self.seq_num += 1
            request = (f"SETUP rtsp://{self.server_addr}:{self.server_port}/{self.filename} {self.RTSP_VER}\r\n"
                      f"CSeq: {self.seq_num}\r\n"
                      f"Transport: RTP/UDP;client_port={self.rtp_port}\r\n\r\n")
            
            self.rtsp_socket.send(request.encode())
            self.request_sent = "SETUP"
            self.log_message(f"📤 RTSP SETUP request sent")
            
        elif request_code == "PLAY" and self.rtsp_socket:
            self.seq_num += 1
            request = (f"PLAY rtsp://{self.server_addr}:{self.server_port}/{self.filename} {self.RTSP_VER}\r\n"
                      f"CSeq: {self.seq_num}\r\n"
                      f"Session: {self.session_id}\r\n\r\n")
            
            self.rtsp_socket.send(request.encode())
            self.request_sent = "PLAY"
            self.log_message(f"📤 RTSP PLAY request sent")
            
        elif request_code == "PAUSE" and self.rtsp_socket:
            self.seq_num += 1
            request = (f"PAUSE rtsp://{self.server_addr}:{self.server_port}/{self.filename} {self.RTSP_VER}\r\n"
                      f"CSeq: {self.seq_num}\r\n"
                      f"Session: {self.session_id}\r\n\r\n")
            
            self.rtsp_socket.send(request.encode())
            self.request_sent = "PAUSE"
            self.log_message(f"📤 RTSP PAUSE request sent")
            
        elif request_code == "TEARDOWN" and self.rtsp_socket:
            self.seq_num += 1
            request = (f"TEARDOWN rtsp://{self.server_addr}:{self.server_port}/{self.filename} {self.RTSP_VER}\r\n"
                      f"CSeq: {self.seq_num}\r\n"
                      f"Session: {self.session_id}\r\n\r\n")
            
            self.rtsp_socket.send(request.encode())
            self.request_sent = "TEARDOWN"
            self.log_message(f"📤 RTSP TEARDOWN request sent")
    
    def recv_rtsp_reply(self):
        """Receive RTSP reply from server"""
        try:
            while self.rtsp_socket:
                try:
                    self.rtsp_socket.settimeout(5.0)  # 5 second timeout
                    reply = self.rtsp_socket.recv(1024).decode()
                    if reply:
                        self.parse_rtsp_reply(reply)
                    else:
                        break
                except socket.timeout:
                    self.log_message("⚠️ RTSP reply timeout")
                    break
                except socket.error as e:
                    if "[WinError 10048]" in str(e):
                        self.log_message("❌ Port conflict - retrying with new port")
                        self.rtp_port = self.get_available_port(self.rtp_port + 1)
                    else:
                        self.log_message(f"❌ RTSP socket error: {e}")
                    break
                    
        except Exception as e:
            self.log_message(f"❌ RTSP reply error: {e}")
    
    def parse_rtsp_reply(self, reply):
        """Parse RTSP reply"""
        lines = reply.split('\n')
        seq_num = self.seq_num
        session_id = self.session_id
        
        # Extract response code
        if lines[0].split()[1] == '200':
            # Extract session ID for SETUP response
            if self.request_sent == "SETUP":
                for line in lines:
                    if line.startswith('Session:'):
                        self.session_id = line.split(' ')[1]
                        break
                
                # Create RTP socket with port retry
                max_retries = 10
                for retry in range(max_retries):
                    try:
                        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        self.rtp_socket.settimeout(0.5)
                        self.rtp_socket.bind(('', self.rtp_port))
                        break  # Success
                    except socket.error as e:
                        if self.rtp_socket:
                            self.rtp_socket.close()
                        self.rtp_port = self.get_available_port(self.rtp_port + 1)
                        if retry == max_retries - 1:
                            self.log_message(f"❌ Could not bind RTP socket: {e}")
                            return
                
                self.log_message(f"📨 RTSP SETUP OK - Session: {self.session_id}")
                
                # Enable play button
                self.play_btn.config(state=tk.NORMAL)
                self.setup_btn.config(state=tk.DISABLED)
                
            elif self.request_sent == "PLAY":
                self.log_message(f"📨 RTSP PLAY OK - Starting video stream")
                self.playing = True
                
                # Clear canvas before starting
                self.video_canvas.delete("all")
                self.video_canvas.create_text(200, 120, 
                                            text="🎬 Starting Video Stream...\nReceiving frames...", 
                                            fill='#a6e3a1', font=('Arial', 12, 'bold'), 
                                            justify=tk.CENTER)
                
                # Start RTP receiving thread
                self.rtp_running = True
                self.rtp_thread = threading.Thread(target=self.listen_rtp, daemon=True)
                self.rtp_thread.start()
                
                # Update buttons
                self.play_btn.config(state=tk.DISABLED)
                self.pause_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.NORMAL)
                
            elif self.request_sent == "PAUSE":
                self.log_message(f"📨 RTSP PAUSE OK")
                self.playing = False
                self.rtp_running = False
                
                # Update buttons
                self.play_btn.config(state=tk.NORMAL)
                self.pause_btn.config(state=tk.DISABLED)
                
            elif self.request_sent == "TEARDOWN":
                self.log_message(f"📨 RTSP TEARDOWN OK")
                self.teardown_acked = 1
                
        else:
            self.log_message(f"❌ RTSP Error: {lines[0]}")
    
    def listen_rtp(self):
        """Listen for RTP packets"""
        self.log_message(f"🎥 RTP listening on port {self.rtp_port}")
        
        while self.rtp_running:
            try:
                data, addr = self.rtp_socket.recvfrom(65536)
                if data and len(data) > 12:  # Valid RTP packet size
                    try:
                        # Parse RTP packet
                        rtp_packet = RTPPacket()
                        rtp_packet.decode(data)
                        
                        # Validate payload
                        if rtp_packet.payload and len(rtp_packet.payload) > 0:
                            # Display frame
                            self.display_frame(rtp_packet.payload)
                            self.frame_count += 1
                            
                            # Update frame counter
                            self.frame_label.config(text=f"📊 Frame: {self.frame_count}")
                            
                            # Log success every 30 frames
                            if self.frame_count % 30 == 0:
                                self.log_message(f"✅ Received {self.frame_count} frames")
                        else:
                            self.log_message("⚠️ Empty RTP payload")
                            
                    except Exception as decode_error:
                        self.log_message(f"❌ RTP decode error: {decode_error}")
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.rtp_running:
                    self.log_message(f"❌ RTP receive error: {e}")
                break
        
        self.log_message(f"⏹️ RTP listening stopped")
    
    def display_frame(self, frame_data):
        """Display video frame on canvas"""
        try:
            # Validate frame data
            if not frame_data or len(frame_data) < 100:
                self.log_message("⚠️ Invalid frame data")
                return
            
            # Check if it's valid JPEG
            if not frame_data.startswith(b'\xff\xd8'):
                self.log_message("⚠️ Not a valid JPEG frame")
                return
            
            # Convert JPEG data to PIL Image
            image = Image.open(io.BytesIO(frame_data))
            
            # Resize to fit canvas
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # Maintain aspect ratio
                img_width, img_height = image.size
                aspect_ratio = img_width / img_height
                
                if canvas_width / canvas_height > aspect_ratio:
                    new_height = canvas_height
                    new_width = int(canvas_height * aspect_ratio)
                else:
                    new_width = canvas_width
                    new_height = int(canvas_width / aspect_ratio)
                
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # Display on canvas
                self.video_canvas.delete("all")
                self.video_canvas.create_image(canvas_width//2, canvas_height//2, image=photo)
                self.video_canvas.image = photo  # Keep reference
                
                # Success indicator (only for first few frames)
                if self.frame_count < 5:
                    self.log_message(f"✅ Frame {self.frame_count} displayed ({new_width}x{new_height})")
                
        except Exception as e:
            self.log_message(f"❌ Frame display error: {e}")
            # Show error on canvas
            self.video_canvas.delete("all")
            self.video_canvas.create_text(200, 120, 
                                        text=f"❌ Display Error\n{str(e)[:50]}", 
                                        fill='#f38ba8', font=('Arial', 10, 'bold'), 
                                        justify=tk.CENTER)
    
    # Button event handlers
    def setup_video(self):
        """Setup video stream"""
        self.send_rtsp_request("SETUP")
    
    def play_video(self):
        """Play video stream"""
        self.send_rtsp_request("PLAY")
    
    def pause_video(self):
        """Pause video stream"""
        self.send_rtsp_request("PAUSE")
    
    def stop_video(self):
        """Stop video stream"""
        self.playing = False
        self.rtp_running = False
        self.send_rtsp_request("TEARDOWN")
        
        # Reset UI with colorful message
        self.video_canvas.delete("all")
        self.video_canvas.create_text(200, 120, text="📺 Video Stopped\n🔄 Ready for new stream", 
                                    fill='#fab387', font=('Arial', 12, 'bold'), justify=tk.CENTER)
        
        self.frame_count = 0
        self.frame_label.config(text="Frame: 0")
        
        # Reset buttons
        self.setup_btn.config(state=tk.NORMAL)
        self.play_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        
        # Close sockets properly
        if self.rtp_socket:
            try:
                self.rtp_socket.close()
                self.rtp_socket = None
            except:
                pass
        
        self.log_message(f"⏹️ Video stream stopped")
    
    def run(self):
        """Run the client GUI"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
    
    def on_closing(self):
        """Handle window closing"""
        self.playing = False
        self.rtp_running = False
        
        # Cleanup sockets
        try:
            if self.rtsp_socket:
                self.rtsp_socket.close()
                self.rtsp_socket = None
        except:
            pass
            
        try:
            if self.rtp_socket:
                self.rtp_socket.close()
                self.rtp_socket = None
        except:
            pass
        
        self.root.destroy()

# Main execution
if __name__ == "__main__":
    try:
        client = RTSPClient()
        client.run()
    except ImportError as e:
        print("❌ Missing required packages:")
        print("Install with: pip install Pillow")
        print(f"Error: {e}")
    except Exception as e:
        print(f"❌ Client error: {e}")