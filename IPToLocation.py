import requests

from math import radians, sin, cos, sqrt, atan2

class IPDistances:

    def __init__(self, ip_list, api_key, local_ip):
        self.ip_list = ip_list
        self.distances_list = []    #Parallel list to ip_list

        #Obtain local coordinates
        local_coords = self.getCoords(local_ip, api_key)

        #Could not find local coords
        if (local_coords == None):
            raise ValueError("Could not get coordinates for local IP")
            
        
        local_lat, local_lon = local_coords

        for ip in self.ip_list:
            coords = self.getCoords(ip, api_key)

            #check bad server response
            if (coords == None):                            #I'm not sure how you guys wanted to handle this so for now I'll just store a None
                self.distances_list.append(None)
                continue

            remote_ip_lat, remote_ip_lon = coords

            self.distances_list.append(self.calcDistance(local_lat, local_lon, remote_ip_lat, remote_ip_lon))

    #Given an IP and api key for the IPGeolocation API, this function
    #returns a tuple of estimated latitude and longitude coordinates
    #of the IP
    def getCoords(self, ip, api_key):
        url = "https://api.ipgeolocation.io/v3/ipgeo"

        response = requests.get(
            url,
            params={
                "apiKey": api_key,
                "ip": ip
            },
            timeout=5
        )

        if response.status_code != 200:
            return None

        data = response.json()

        return (
            float(data["location"]["latitude"]),
            float(data["location"]["longitude"])
        )

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