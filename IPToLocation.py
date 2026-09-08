import requests
import time

from math import radians, sin, cos, sqrt, atan2

class IPDistances:

    def __init__(self, ip_list, api_key, local_ip):
        self.ip_list = []
        self.distances_list = []    #Parallel list to ip_list

        #Obtain local coordinates
        local_coords = self.getCoords(local_ip, api_key)

        if local_coords is None:
            raise Exception("Could not obtain coordinates for local IP")
        
        local_lat, local_lon = local_coords
        
        #Creates parallel list of valid IPs and distances between
        #local IP to another IP
        for ip in ip_list:
            remote_coords = self.getCoords(ip, api_key)

            if remote_coords is None:
                print(f"Removing {ip}: could not obtain location")
                continue

            remote_ip_lat, remote_ip_lon = remote_coords

            distance = self.calcDistance(
                local_lat,
                local_lon,
                remote_ip_lat,
                remote_ip_lon
            )

            self.ip_list.append(ip)
            self.distances_list.append(distance)

    #Given an IP and api key for the IPGeolocation API, this function
    #returns a tuple of estimated latitude and longitude coordinates
    #of the IP
    def getCoords(self, ip, api_key, retries=3):
        url = "https://api.ipgeolocation.io/v3/ipgeo"

        for attempt in range(retries):
            try:
                response = requests.get(
                    url,
                    params={
                        "apiKey": api_key,
                        "ip": ip
                    },
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()

                    return (
                        float(data["location"]["latitude"]),
                        float(data["location"]["longitude"])
                    )

                print(
                    f"Attempt {attempt + 1} failed for {ip}: "
                    f"status code {response.status_code}"
                )

            except requests.RequestException:
                print(
                    f"Attempt {attempt + 1} failed for {ip}: "
                    "request error"
                )

            # Wait 1 second before trying again
            time.sleep(0.5)

        # All attempts failed
        return None

    #Given 2 latitude and longitude coordinates, this function
    #returns the distance between them in Kilometers
    def calcDistance(self, lat1, lon1, lat2, lon2):
        R = 6371.0

        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            sin(dlat / 2) ** 2
            + cos(lat1)
            * cos(lat2)
            * sin(dlon / 2) ** 2
        )

        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c