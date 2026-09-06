import matplotlib.pyplot as plt
import IPToLocation
import requests

from fetch_servers import fetch_ips

#def createScatterPlot():


if __name__ == "__main__":
    api_key = "48c460778462485c897c94cd724fb652"
    local_ip = requests.get("https://api.ipify.org").text

    ip_list = fetch_ips()

    distances = IPToLocation.IPDistances(ip_list, api_key, local_ip)

    print(len(ip_list))
    print(ip_list)

    print(len(distances.distances_list))
    print(distances.distances_list)
