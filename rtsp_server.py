"""
RTSP Server Implementation
Handles RTSP protocol commands and RTP video streaming
"""

import socket
import threading
import time
import os
from rtp_packet import RTPVideoStream
try:
    from enhanced_video_stream import EnhancedVideoStream as VideoStream
    print("🎬 Enhanced video support enabled (MP4 + MJPEG)")
except ImportError:
    from video_stream import VideoStream
    print("📺 Basic video support (MJPEG only)")

class RTSPServer:
    """RTSP Streaming Server"""
    
    RTSP_VER = "RTSP/1.0"
    
    # RTSP Response Codes
    OK = 200
    FILE_NOT_FOUND = 404
    CON_ERR = 500
    
    def __init__(self, port=8554):
        self.port = port
        self.server_socket = None
        self.clients = {}  # client_addr: ClientSession
        self.running = False
        
    def start(self):
        """Start RTSP server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"🎬 RTSP Server started on port {self.port}")
            print("Available videos:")
            
            # Check videos folder
            if os.path.exists('videos'):
                for video in os.listdir('videos'):
                    if video.lower().endswith(('.mjpeg', '.mp4', '.avi', '.mov')):
                        video_type = "MP4" if video.lower().endswith(('.mp4', '.avi', '.mov')) else "MJPEG"
                        print(f"  - rtsp://localhost:{self.port}/{video} [{video_type}]")
            
            # Check root directory for MP4 files
            for file in os.listdir('.'):
                if file.lower().endswith(('.mp4', '.avi', '.mov')):
                    print(f"  - rtsp://localhost:{self.port}/{file} [MP4]")
            
            while self.running:
                try:
                    client_socket, client_addr = self.server_socket.accept()
                    print(f"📱 Client connected: {client_addr}")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error:
                    if self.running:
                        print("❌ Server socket error")
                        
        except Exception as e:
            print(f"❌ Server start error: {e}")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, client_addr):
        """Handle individual client connection"""
        session = ClientSession(client_socket, client_addr)
        self.clients[client_addr] = session
        
        try:
            while self.running:
                # Receive RTSP request
                request = client_socket.recv(1024).decode('utf-8')
                if not request:
                    break
                
                print(f"📨 RTSP Request from {client_addr}:")
                print(request.strip())
                
                # Parse and handle request
                response = self.parse_rtsp_request(request, session)
                
                # Send response
                client_socket.send(response.encode('utf-8'))
                print(f"📤 RTSP Response to {client_addr}:")
                print(response.strip())
                
        except Exception as e:
            print(f"❌ Client handling error: {e}")
        finally:
            session.cleanup()
            if client_addr in self.clients:
                del self.clients[client_addr]
            client_socket.close()
            print(f"🔌 Client {client_addr} disconnected")
    
    def parse_rtsp_request(self, request, session):
        """Parse RTSP request and generate response"""
        lines = request.strip().split('\n')
        if not lines:
            return self.generate_response(self.CON_ERR, session.seq_num)
        
        # Parse request line
        request_line = lines[0].split()
        if len(request_line) < 3:
            return self.generate_response(self.CON_ERR, session.seq_num)
        
        method = request_line[0]
        url = request_line[1]
        
        # Extract CSeq
        cseq = 0
        for line in lines[1:]:
            if line.startswith('CSeq:'):
                cseq = int(line.split(':')[1].strip())
                break
        
        session.seq_num = cseq
        
        # Handle different RTSP methods
        if method == "SETUP":
            return self.handle_setup(url, lines, session)
        elif method == "PLAY":
            return self.handle_play(session)
        elif method == "PAUSE":
            return self.handle_pause(session)
        elif method == "TEARDOWN":
            return self.handle_teardown(session)
        else:
            return self.generate_response(self.CON_ERR, cseq)
    
    def handle_setup(self, url, lines, session):
        """Handle RTSP SETUP request"""
        try:
            # Extract filename from URL
            filename = url.split('/')[-1]
            video_path = os.path.join('videos', filename)
            
            # Check for MP4 file in root directory
            if not os.path.exists(video_path):
                # Check if it's an MP4 file in the root directory
                root_path = filename
                if os.path.exists(root_path) and filename.lower().endswith('.mp4'):
                    video_path = root_path
                    print(f"📁 Found MP4 file in root: {video_path}")
                else:
                    return self.generate_response(self.FILE_NOT_FOUND, session.seq_num)
            
            # Extract client RTP port
            client_rtp_port = 25000  # Default
            for line in lines:
                if 'client_port=' in line:
                    port_info = line.split('client_port=')[1].split('-')[0]
                    client_rtp_port = int(port_info)
                    break
            
            # Setup video stream
            session.video_stream = VideoStream(video_path)
            session.rtp_stream = RTPVideoStream()
            session.client_rtp_port = client_rtp_port
            session.server_rtp_port = 25000
            
            # Generate session ID
            session.session_id = int(time.time())
            
            # Create RTP socket
            session.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            response = (f"{self.RTSP_VER} {self.OK} OK\r\n"
                       f"CSeq: {session.seq_num}\r\n"
                       f"Transport: RTP/UDP;client_port={client_rtp_port}-{client_rtp_port+1};"
                       f"server_port={session.server_rtp_port}-{session.server_rtp_port+1}\r\n"
                       f"Session: {session.session_id}\r\n\r\n")
            
            session.state = "READY"
            return response
            
        except Exception as e:
            print(f"❌ SETUP error: {e}")
            return self.generate_response(self.CON_ERR, session.seq_num)
    
    def handle_play(self, session):
        """Handle RTSP PLAY request"""
        if session.state != "READY" and session.state != "PLAYING":
            return self.generate_response(self.CON_ERR, session.seq_num)
        
        session.state = "PLAYING"
        
        # Start RTP streaming thread
        if not session.streaming_thread or not session.streaming_thread.is_alive():
            session.streaming_thread = threading.Thread(
                target=self.stream_video, 
                args=(session,),
                daemon=True
            )
            session.streaming_thread.start()
        
        response = (f"{self.RTSP_VER} {self.OK} OK\r\n"
                   f"CSeq: {session.seq_num}\r\n"
                   f"Session: {session.session_id}\r\n\r\n")
        
        return response
    
    def handle_pause(self, session):
        """Handle RTSP PAUSE request"""
        session.state = "READY"
        
        response = (f"{self.RTSP_VER} {self.OK} OK\r\n"
                   f"CSeq: {session.seq_num}\r\n"
                   f"Session: {session.session_id}\r\n\r\n")
        
        return response
    
    def handle_teardown(self, session):
        """Handle RTSP TEARDOWN request"""
        session.state = "INIT"
        session.cleanup()
        
        response = (f"{self.RTSP_VER} {self.OK} OK\r\n"
                   f"CSeq: {session.seq_num}\r\n"
                   f"Session: {session.session_id}\r\n\r\n")
        
        return response
    
    def stream_video(self, session):
        """Stream video via RTP"""
        print(f"🎥 Starting video stream to {session.addr} on RTP port {session.client_rtp_port}")
        
        frame_count = 0
        try:
            while session.state == "PLAYING":
                # Get next frame
                frame_data = session.video_stream.get_next_frame()
                if frame_data is None:
                    # End of video, loop back
                    session.video_stream.reset()
                    print(f"🔄 Video loop - sent {frame_count} frames")
                    continue
                
                # Validate frame data
                if not frame_data or len(frame_data) < 100:
                    print(f"⚠️ Invalid frame data at frame {frame_count}")
                    continue
                
                # Create RTP packet
                rtp_packet = session.rtp_stream.create_packet(frame_data, True)
                encoded_packet = rtp_packet.encode()
                
                # Send RTP packet
                try:
                    bytes_sent = session.rtp_socket.sendto(
                        encoded_packet,
                        (session.addr[0], session.client_rtp_port)
                    )
                    frame_count += 1
                    
                    # Log progress every 30 frames
                    if frame_count % 30 == 0:
                        print(f"📤 Sent {frame_count} frames ({bytes_sent} bytes/frame)")
                        
                except Exception as send_error:
                    print(f"❌ Send error at frame {frame_count}: {send_error}")
                    break
                
                # Control frame rate (30 FPS = ~33ms per frame)
                time.sleep(0.033)
                
        except Exception as e:
            print(f"❌ Streaming error: {e}")
        
        print(f"⏹️ Video stream stopped for {session.addr} - Total frames sent: {frame_count}")
    
    def generate_response(self, code, cseq):
        """Generate RTSP response"""
        status_text = {
            self.OK: "OK",
            self.FILE_NOT_FOUND: "Not Found", 
            self.CON_ERR: "Internal Server Error"
        }
        
        return (f"{self.RTSP_VER} {code} {status_text[code]}\r\n"
                f"CSeq: {cseq}\r\n\r\n")
    
    def stop(self):
        """Stop RTSP server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # Cleanup all client sessions
        for session in self.clients.values():
            session.cleanup()
        
        print("⏹️ RTSP Server stopped")

class ClientSession:
    """Client session management"""
    
    def __init__(self, socket, addr):
        self.socket = socket
        self.addr = addr
        self.seq_num = 0
        self.session_id = None
        self.state = "INIT"
        self.video_stream = None
        self.rtp_stream = None
        self.rtp_socket = None
        self.client_rtp_port = None
        self.server_rtp_port = None
        self.streaming_thread = None
    
    def cleanup(self):
        """Clean up session resources"""
        self.state = "INIT"
        if self.rtp_socket:
            self.rtp_socket.close()
        if self.video_stream:
            self.video_stream.close()

# Main server execution
if __name__ == "__main__":
    import sys
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8554
    
    server = RTSPServer(port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Server interrupted by user")
    finally:
        server.stop()