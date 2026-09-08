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
                ["ping", "-c", "10", "-i", "0.5", ip],
                capture_output=True,
                text=True,
                timeout=10
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

#Returns 3 lists:
  #new_ping_ip_list: list PingIP objects where its IP was pingable
  #new_ip_distances: list of distances between local to remote IP that were pingable
  #new_ip_list: list of IPs that were pingable
def getPingIPDistanceLists(
    ip_distances: list[float],
    ip_list: list[str]
) -> tuple[list[PingIP], list[float], list[str]]:

    new_ping_ip_list = []
    new_ip_distances = []
    new_ip_list = []

    ping_num = 0
    for ip, distance in zip(ip_list, ip_distances):
        print(ping_num)
        ping_num += 1

        ping_ip = PingIP(ip)

        # If ping failed, don't add this IP or its distance
        if ping_ip.avg_rtt is None:
            print(f"Removing {ip}: could not ping")
            continue

        new_ping_ip_list.append(ping_ip)
        new_ip_list.append(ip)
        new_ip_distances.append(distance)

    return new_ping_ip_list, new_ip_distances, new_ip_list