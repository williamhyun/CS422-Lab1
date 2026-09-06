import subprocess
import re

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
        try:
            result = subprocess.run(
                ["ping", "-c", "10", ip],
                capture_output=True,
                text=True,
                timeout=20
            )

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