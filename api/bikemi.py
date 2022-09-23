import json
import re
import requests
import unidecode

from geopy import distance
from operator import itemgetter


class BikeMiApi:
    def json_decoder(self, info_url):
        """Generate a list of stations, stored as dictionaries, by using the
        json files provided by BikeMi at https://bikemi.com/dati-aperti/"""
        resp = requests.get(info_url)
        raw = resp.json()
        # Pick the "stations" values inside the "data" key of the "raw" dict
        stations = raw["data"]["stations"]
        for element in stations:
            del element["name"]
        # Each station is a dictionary inside the list called "stations"
        return json.dumps(stations, indent=4)

    def get_station_extra_info_json(self):
        """Get further info (bike availability) by scraping the bikemi.com source"""
        raw = requests.get("https://bikemi.com/stazioni").text
        placeholder = '"stationMapPage","slug":null},'
        start = raw.find(placeholder) + len(placeholder)
        end = raw.find('},"baseUrl":"https://bikemi.com"')
        station_extra_info_raw = "{" + (raw[start:end])
        # Each station is a string inside the list called "station_list"
        station_list = []
        jsontxt = json.loads(station_extra_info_raw)
        for element in jsontxt:
            station_info = {
                "station_id": jsontxt[element]["id"],
                "name": jsontxt[element]["name"],
                "title": jsontxt[element]["title"],
                "bike": jsontxt[element]["availabilityInfo"][
                    "availableVehicleCategories"
                ][0]["count"],
                "ebike": jsontxt[element]["availabilityInfo"][
                    "availableVehicleCategories"
                ][1]["count"],
                "ebike_with_childseat": jsontxt[element]["availabilityInfo"][
                    "availableVehicleCategories"
                ][2]["count"],
                "availableDocks": jsontxt[element]["availabilityInfo"][
                    "availableDocks"
                ],
                "availableVirtualDocks": jsontxt[element]["availabilityInfo"][
                    "availableVirtualDocks"
                ],
                "availablePhysicalDocks": jsontxt[element]["availabilityInfo"][
                    "availablePhysicalDocks"
                ],
            }
            station_list.append(station_info)

        # Return a list containing all the stations, stored as dictionaries
        return json.dumps(station_list, indent=4)

    def get_station_full_info_json(self, url):
        """Merge basic info from the Open Data with the extra info
        scraped from the website.
        Note: both input files have to be in json format"""
        get_stations_basic_info = self.json_decoder(url)
        stations_extra_info = self.get_station_extra_info_json()
        get_stations_basic_info_sorted = sorted(
            json.loads(get_stations_basic_info), key=itemgetter("station_id")
        )
        stations_extra_info_sorted = sorted(
            json.loads(stations_extra_info), key=itemgetter("station_id")
        )
        stations_full_info = [
            a | b
            for (a, b) in zip(
                stations_extra_info_sorted, get_stations_basic_info_sorted
            )
        ]

        return json.dumps(stations_full_info, indent=4)

    def find_station(self, stations, user_input):
        """Search and yield stations by typing their names or their unique IDs,
        it's meant to be used with
        https://gbfs.urbansharing.com/bikemi.com/station_information.json"""
        # Remove accents, all the spaces and special chars from the input
        user_input_edit = re.sub("[^A-Za-z0-9]+", "", unidecode.unidecode(user_input))
        found_station_list = []

        for station in stations:
            # Temporarily treat the station names like user_input
            station_edit = re.sub(
                "[^A-Za-z0-9]+", "", unidecode.unidecode(station["title"])
            )
            # Check if user_input and stations match
            if user_input_edit != ("") and (
                re.search(user_input_edit, station_edit, re.IGNORECASE)
                or re.search(user_input, station["station_id"], re.IGNORECASE)
            ):
                found_station_list.append(station)
            else:
                found_station_list.append(0)

        if not any(found_station_list):
            yield None
        if any(found_station_list):
            for element in found_station_list:
                if element != 0:
                    yield element

    def sort(self, stations, key):
        """Sort all the stations by chosen key"""
        return sorted(stations, key=itemgetter(key))

    def get_nearest_station(self, stations_full_info, lat, lon):
        """Get the nearest station given latitude and longitude"""
        distances = []
        for station in stations_full_info:
            coord_input = (lat, lon)
            coord_stations = (station["lat"], station["lon"])
            distances.append(distance.distance(coord_input, coord_stations).kilometers)

        smallest = min(distances)  # Get smallest distance
        # Get index of the specified element in the list
        # Note: index of the smallest distance = index of
        # said station in "stations_full_info" list
        index = distances.index(smallest)
        return stations_full_info[index]
