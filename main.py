import matplotlib.pyplot as plt
import IPToLocation
import PingServers
import requests

from fetch_servers import fetch_ips

def plotDistancesVSRtt(distances_list: list[float], rtt_list: list[float], rtt_type: str):
    plt.figure()
    plt.scatter(distances_list, rtt_list)
    plt.xlabel("Distance (km)")

    #Change ylabel and title based on rtt data type
    if rtt_type == "avg":
        plt.ylabel("Average RTT (ms)")
        plt.title("Distance vs Average RTT")
        plt.savefig("distance_vs_avg_rtt.pdf")
    elif rtt_type == "min":
        plt.ylabel("Minimum RTT (ms)")
        plt.title("Distance vs Minimum RTT")
        plt.savefig("distance_vs_min_rtt.pdf")
    else:
        plt.ylabel("Maximum RTT (ms)")
        plt.title("Distance vs Maximum RTT")
        plt.savefig("distance_vs_max_rtt.pdf")


if __name__ == "__main__":
    api_key = "bd8527edb8f2412c947e3d498ee8839a"
    local_ip = requests.get("https://api.ipify.org").text

    #Parses IPs and retrieves from https://iperf3serverlist.net/
    ip_list = fetch_ips()

    #Contains list of IPs where coordinates were obtainable and
    #a parallel list of distances from our local IP to another IP
    ip_distances_obj = IPToLocation.IPDistances(ip_list, api_key, local_ip)

    pingIP_list, ip_distances_list, ip_list = PingServers.getPingIPDistanceLists(
      ip_distances_obj.distances_list,
      ip_distances_obj.ip_list
    )
    
    avg_rtts = [ping_obj.avg_rtt for ping_obj in pingIP_list]
    min_rtts = [ping_obj.min_rtt for ping_obj in pingIP_list]
    max_rtts = [ping_obj.max_rtt for ping_obj in pingIP_list]

    plotDistancesVSRtt(ip_distances_list, avg_rtts, "avg")
    plotDistancesVSRtt(ip_distances_list, min_rtts, "min")
    plotDistancesVSRtt(ip_distances_list, max_rtts, "max")
