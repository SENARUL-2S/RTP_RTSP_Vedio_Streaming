from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
import threading
import base64
import json
import time
import socket
import os
from real_video_stream import global_video_streamer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nirob_rtsp_web_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global server instance
rtsp_server_thread = None
server_running = False

@app.route('/')
def index():
    return render_template('enhanced_player.html')

@app.route('/start_server')
def start_server():
    global rtsp_server_thread, server_running
    try:
        if not server_running:
            # Start RTSP server in background
            import subprocess
            subprocess.Popen(['python', 'rtsp_server.py'])
            server_running = True
            time.sleep(2)  # Wait for server to start
            
        return jsonify({
            "status": "success", 
            "message": "🎬 RTSP Server + Real Video Streaming Ready!",
            "server_url": "rtsp://localhost:8554"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"❌ Error: {str(e)}"})

@app.route('/api/videos')
def get_videos():
    # Get real video list from video streamer
    try:
        video_list = global_video_streamer.get_video_list()
        return jsonify({"videos": video_list})
    except Exception as e:
        # Fallback video list
        return jsonify({
            "videos": [
                {
                    "name": "nirob.mp4",
                    "title": "📹 Nirob Video (MP4)",
                    "frame_count": 0,
                    "fps": 25,
                    "format": "MP4"
                }
            ]
        })

@app.route('/api/server_status')
def server_status():
    try:
        # Check if RTSP server is running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8554))
        sock.close()
        
        if result == 0:
            return jsonify({
                "status": "running",
                "message": "✅ RTSP Server + Real Video Streaming Online",
                "port": 8554,
                "video_count": len(global_video_streamer.videos)
            })
        else:
            return jsonify({
                "status": "stopped", 
                "message": "❌ RTSP Server is offline",
                "port": 8554,
                "video_count": len(global_video_streamer.videos)
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"🔍 Status check failed: {str(e)}"
        })

@socketio.on('connect')
def on_connect():
    emit('status_update', {'message': '🔗 Connected to Enhanced Video Web Server'})
    # Send video info on connect
    video_info = {
        'available_videos': len(global_video_streamer.videos),
        'loaded_videos': list(global_video_streamer.videos.keys())
    }
    emit('video_info', video_info)

@socketio.on('rtsp_command')
def handle_rtsp_command(data):
    command = data.get('command')
    video = data.get('video', 'nirob.mp4')
    
    if command == 'SETUP':
        emit('status_update', {'message': f'📋 Setting up real {video}...'})
        if video in global_video_streamer.videos:
            emit('setup_complete', {'video': video})
            emit('status_update', {'message': f'✅ {video} ready for streaming!'})
        else:
            emit('status_update', {'message': f'❌ Video {video} not found!'})
        
    elif command == 'PLAY':
        if global_video_streamer.start_stream(video):
            emit('status_update', {'message': f'▶️ Playing real {video} video...'})
            emit('video_start', {'video': video})
            # Start real frame streaming
            start_frame_streaming(video)
        else:
            emit('status_update', {'message': f'❌ Failed to start {video}'})
        
    elif command == 'PAUSE':
        emit('status_update', {'message': '⏸️ Video paused'})
        emit('video_pause', {})
        
    elif command == 'TEARDOWN':
        global_video_streamer.stop_stream(video)
        emit('status_update', {'message': '⏹️ Video stopped'})
        emit('video_stop', {})

def start_frame_streaming(video_name):
    """Stream real video frames in real-time"""
    def stream_frames():
        frame_count = 0
        start_time = time.time()
        
        print(f'🎬 Starting frame streaming for {video_name}...')
        
        while video_name in global_video_streamer.active_streams:
            frame_data = global_video_streamer.get_next_frame(video_name)
            if frame_data:
                # Emit real video frame
                socketio.emit('video_frame', {
                    'frame_data': frame_data['frame_data'],
                    'frame_number': frame_data['frame_number'],
                    'video': video_name,
                    'timestamp': frame_data['timestamp']
                })
                frame_count += 1
                
                # Control frame rate (25 FPS = 40ms)
                time.sleep(0.04)
                    
            else:
                break
        
        # Video streaming finished
        socketio.emit('video_complete', {
            'video': video_name, 
            'total_frames': frame_count,
            'duration': time.time() - start_time
        })
        print(f'🏁 {video_name} streaming completed! {frame_count} frames')
    
    # Start streaming in background thread
    threading.Thread(target=stream_frames, daemon=True).start()

@app.route('/api/video_info/<video_name>')
def get_video_info(video_name):
    """Get detailed video information"""
    if video_name in global_video_streamer.videos:
        info = global_video_streamer.videos[video_name].get_info()
        return jsonify(info)
    else:
        return jsonify({"error": "Video not found"}), 404

if __name__ == '__main__':
    print("🎬 Starting Enhanced Nirob's Real Video Web Server...")
    print("📱 Features: Real MP4 streaming, Frame-by-frame delivery")
    print("🌐 Access at: http://localhost:5001")
    print(f"📹 Loaded videos: {list(global_video_streamer.videos.keys())}")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)