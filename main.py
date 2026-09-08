import matplotlib.pyplot as plt
import IPToLocation
import PingServers
import requests

from fetch_servers import fetch_ips

def plotDistancesVSRtt(distances_list: list[float], rtt_list: list[float]):
    plt.scatter(distances_list, rtt_list)

    plt.xlabel("Distance (km)")
    plt.ylabel("Average RTT (ms)")
    plt.title("Distance vs Average RTT")

    plt.savefig("distance_vs_rtt.pdf")
    plt.show()


if __name__ == "__main__":
    api_key = "48c460778462485c897c94cd724fb652"
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

    plotDistancesVSRtt(ip_distances_list, avg_rtts)
