import socket

# Ports you listed
ports_to_check = [30053, 9119, 6001, 3100, 8001, 5432, 9167, 3000, 8453, 5302, 9090, 5335, 8083]

# Known services mapping (you can expand if needed)
common_services = {
    30053: "Custom (possible game or app server)",
    9119: "Custom / proprietary service",
    6001: "X11:1 / custom TCP app",
    3100: "Grafana / custom HTTP service",
    8001: "Alt HTTP / Node.js",
    5432: "PostgreSQL Database",
    9167: "Prometheus metrics",
    3000: "Node.js / Grafana / Dev server",
    8453: "Custom HTTPS",
    5302: "Custom",
    9090: "Prometheus / custom web service",
    5335: "Custom",
    8083: "Alt HTTP / management interface"
}

# Change this to your target host
target_host = "127.0.0.1"

def check_port(host, port):
    """Check if a port is open and return service name if found."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)  # timeout in seconds
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            service = common_services.get(port, "Unknown Service")
            return True, service
        else:
            return False, None
    except socket.error:
        return False, None
    finally:
        sock.close()

print(f"Scanning {target_host}...\n")
for port in ports_to_check:
    is_open, service = check_port(target_host, port)
    if is_open:
        print(f"Port {port} is OPEN — Service: {service}")
    else:
        print(f"Port {port} is CLOSED")
