import subprocess
import re
import platform

class PingIP:
    def __init__(self, ip: str):
        self.ip = ip
        result = self.ping_server(self.ip)

        if result is not None:
            self.min_rtt, self.avg_rtt, self.max_rtt = result
        else:
            self.min_rtt = None
            self.avg_rtt = None
            self.max_rtt = None

    # Given an IP, this function returns a tuple of the minimum,
    # average, and maximum round-trip time for 10 pings.
    def ping_server(self, ip: str):


        is_windows = platform.system().lower() == "windows"
        
        # Use '-n' for Windows and '-c' for Unix/Mac
        if is_windows:
            command = ["ping", "-n", "10", ip]
        else:
            command = ["ping", "-c", "10", ip]



        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=20
            )

            if is_windows:

                # Windows format example:
                # Minimum = 12ms, Maximum = 20ms, Average = 15ms
                match = re.search(
                    r"Minimum\s*=\s*([\d.]+)ms.*?Maximum\s*=\s*([\d.]+)ms.*?Average\s*=\s*([\d.]+)ms",
                    result.stdout,
                    re.IGNORECASE
                )
                if match:
                    min_rtt = float(match.group(1))
                    max_rtt = float(match.group(2))
                    avg_rtt = float(match.group(3))
                    return min_rtt, avg_rtt, max_rtt
                print(f"Could not get RTT for {ip}")
                return None

            else:
                # Output example:
                # round-trip min/avg/max/stddev = 12.3/15.2/20.1/2.4 ms

                match = re.search(
                    r"min/avg/max/stddev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)",
                    result.stdout
                )

                if match:
                    min_rtt = float(match.group(1))
                    avg_rtt = float(match.group(2))
                    max_rtt = float(match.group(3))

                    return min_rtt, avg_rtt, max_rtt

                print(f"Could not get RTT for {ip}")
                return None

        except subprocess.TimeoutExpired:
            print(f"{ip} timed out")
            return None


def getPingIPList(ip_list: list[str]) -> list[PingIP]:
    ping_ip_list = [PingIP(ip) for ip in ip_list]
    return ping_ip_list