import matplotlib.pyplot as plt
import IPToLocation
import PingServers
import requests
import Latency_Breakdown

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

    ip_list = fetch_ips()
    ip_distances = IPToLocation.IPDistances(ip_list, api_key, local_ip)
    ip_pings = PingServers.getPingIPList(ip_list)

    #TODO: skip and remove servers from list that aren't pingable (inside PingServers.py)
    #      and also for servers we can't obtain coordinates for (inside IPToLocation.py)
    avg_rtts = [ping_obj.avg_rtt for ping_obj in ip_pings]

    plotDistancesVSRtt(ip_distances, avg_rtts)

    #print(len(ip_list))
    #print(ip_list)
    #print(len(ip_distances.distances_list))
    #print(ip_distances.distances_list)

    print("Moving onto Q2")

    #Q2:
    results = Latency_Breakdown.find_and_print_random(ip_list, n = 5)
    Latency_Breakdown.plot_stacked_bar_chart(results)
    Latency_Breakdown.plot_scatter_hop_vs_rtt(results)





