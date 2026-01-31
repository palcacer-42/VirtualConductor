from pythonosc import dispatcher
from pythonosc import osc_server

def print_handler(address, *args):
    print(f"Received {address}: {args}")

if __name__ == "__main__":
    ip = "127.0.0.1"
    port = 8000
    
    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/hand/*", print_handler)  # Map wildcard for all hand messages

    server = osc_server.ThreadingOSCUDPServer((ip, port), dispatcher)
    print(f"Serving on {server.server_address}")
    
    # Run until interrupted
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped.")
