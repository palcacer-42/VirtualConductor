from pythonosc import udp_client

class OscController:
    """
    Handles OSC communication for the Holistic Tracker.
    Broadcasts data to a target IP and Port (default: 127.0.0.1:8000).
    """
    def __init__(self, ip="127.0.0.1", port=8000):
        self.ip = ip
        self.port = port
        self.client = udp_client.SimpleUDPClient(ip, port)
        print(f"OSC Controller started. Targeting {self.ip}:{self.port}")

    def send_value(self, address, value):
        """
        Send a single value to an OSC address.
        e.g., send_value("/hand/left/y", 0.5)
        """
        self.client.send_message(address, value)
        
    def send_vector(self, address, x, y, z=0):
        """
        Send a vector (x, y, z) to an OSC address.
        """
        self.client.send_message(address, [x, y, z])
