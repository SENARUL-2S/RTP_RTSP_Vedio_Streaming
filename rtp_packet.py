"""
RTP Packet Implementation for Video Streaming
Handles RTP packet creation, parsing, and management
"""

import struct
import time

class RTPPacket:
    HEADER_SIZE = 12
    
    def __init__(self, version=2, padding=0, extension=0, cc=0, marker=0, 
                 pt=26, seq_num=0, timestamp=0, ssrc=0, payload=b''):
        """
        Initialize RTP packet with header fields
        
        Args:
            version (int): RTP version (default: 2)
            padding (int): Padding bit (0 or 1)
            extension (int): Extension bit (0 or 1)  
            cc (int): CSRC count (0-15)
            marker (int): Marker bit (0 or 1)
            pt (int): Payload type (default: 26 for MJPEG)
            seq_num (int): Sequence number
            timestamp (int): Timestamp
            ssrc (int): Synchronization source identifier
            payload (bytes): Payload data
        """
        self.version = version
        self.padding = padding
        self.extension = extension
        self.cc = cc
        self.marker = marker
        self.pt = pt
        self.seq_num = seq_num
        self.timestamp = timestamp
        self.ssrc = ssrc
        self.payload = payload
    
    def encode(self):
        """
        Encode RTP packet to bytes
        
        Returns:
            bytes: Encoded RTP packet
        """
        # First byte: V(2) + P(1) + X(1) + CC(4)
        byte1 = (self.version << 6) | (self.padding << 5) | (self.extension << 4) | self.cc
        
        # Second byte: M(1) + PT(7)
        byte2 = (self.marker << 7) | self.pt
        
        # Pack RTP header (12 bytes)
        header = struct.pack('!BBHII', 
                           byte1,           # V|P|X|CC
                           byte2,           # M|PT
                           self.seq_num,    # Sequence number
                           self.timestamp,  # Timestamp
                           self.ssrc)       # SSRC
        
        return header + self.payload
    
    def decode(self, packet_data):
        """
        Decode RTP packet from bytes (instance method)
        
        Args:
            packet_data (bytes): Raw packet data
        """
        if len(packet_data) < self.HEADER_SIZE:
            raise ValueError("Packet too short for RTP header")
        
        # Unpack header
        byte1, byte2, seq_num, timestamp, ssrc = struct.unpack('!BBHII', 
                                                               packet_data[:self.HEADER_SIZE])
        
        # Extract header fields
        self.version = (byte1 >> 6) & 0x3
        self.padding = (byte1 >> 5) & 0x1
        self.extension = (byte1 >> 4) & 0x1
        self.cc = byte1 & 0xF
        
        self.marker = (byte2 >> 7) & 0x1
        self.pt = byte2 & 0x7F
        
        # Set packet fields
        self.seq_num = seq_num
        self.timestamp = timestamp
        self.ssrc = ssrc
        
        # Extract payload
        self.payload = packet_data[self.HEADER_SIZE:]

    @classmethod
    def decode_packet(cls, packet_data):
        """
        Decode RTP packet from bytes (class method)
        
        Args:
            packet_data (bytes): Raw packet data
            
        Returns:
            RTPPacket: Decoded RTP packet object
        """
        if len(packet_data) < cls.HEADER_SIZE:
            raise ValueError("Packet too short for RTP header")
        
        # Unpack header
        byte1, byte2, seq_num, timestamp, ssrc = struct.unpack('!BBHII', 
                                                               packet_data[:cls.HEADER_SIZE])
        
        # Extract header fields
        version = (byte1 >> 6) & 0x3
        padding = (byte1 >> 5) & 0x1
        extension = (byte1 >> 4) & 0x1
        cc = byte1 & 0xF
        
        marker = (byte2 >> 7) & 0x1
        pt = byte2 & 0x7F
        
        # Extract payload
        payload = packet_data[cls.HEADER_SIZE:]
        
        return cls(version, padding, extension, cc, marker, pt, 
                  seq_num, timestamp, ssrc, payload)
    
    def __str__(self):
        """String representation of RTP packet"""
        return (f"RTP Packet: V={self.version}, PT={self.pt}, "
                f"Seq={self.seq_num}, TS={self.timestamp}, "
                f"SSRC={self.ssrc}, Payload={len(self.payload)} bytes")

class RTPVideoStream:
    """RTP Video Stream Manager"""
    
    def __init__(self, ssrc=None):
        self.ssrc = ssrc or int(time.time())
        self.seq_num = 0
        self.timestamp_base = int(time.time() * 90000)  # 90kHz clock
        
    def create_packet(self, frame_data, is_last_fragment=False):
        """
        Create RTP packet for video frame
        
        Args:
            frame_data (bytes): Video frame data
            is_last_fragment (bool): Whether this is the last fragment of frame
            
        Returns:
            RTPPacket: RTP packet with video data
        """
        # Calculate timestamp (90kHz for video)
        timestamp = self.timestamp_base + int(time.time() * 90000)
        
        # Create RTP packet
        packet = RTPPacket(
            pt=26,  # MJPEG payload type
            seq_num=self.seq_num,
            timestamp=timestamp,
            ssrc=self.ssrc,
            marker=1 if is_last_fragment else 0,
            payload=frame_data
        )
        
        # Increment sequence number
        self.seq_num = (self.seq_num + 1) % 65536
        
        return packet
    
    def get_stats(self):
        """Get streaming statistics"""
        return {
            'packets_sent': self.seq_num,
            'ssrc': self.ssrc,
            'current_timestamp': self.timestamp_base + int(time.time() * 90000)
        }

# Example usage
if __name__ == "__main__":
    # Create RTP stream
    stream = RTPVideoStream()
    
    # Sample frame data
    frame_data = b'\xFF\xD8\xFF\xE0' + b'\x00' * 1000 + b'\xFF\xD9'  # JPEG frame
    
    # Create RTP packet
    packet = stream.create_packet(frame_data, is_last_fragment=True)
    
    # Encode packet
    encoded = packet.encode()
    print(f"Encoded packet size: {len(encoded)} bytes")
    
    # Decode packet
    decoded = RTPPacket.decode(encoded)
    print(f"Decoded: {decoded}")
    
    # Verify payload
    print(f"Payload match: {decoded.payload == frame_data}")