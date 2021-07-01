import json
import re
import requests
import unidecode

from geopy import distance
from operator import itemgetter


class BikeMiApi:
    def json_decoder(self, info_url):
        """Generate a list of stations, stored as dictionaries, manipulating the
        json files provided by BikeMi at https://bikemi.com/dati-aperti/"""
        resp = requests.get(info_url)
        raw = resp.json()
        # Pick the "stations" values inside the "data" key of the "raw" dict
        stations = raw["data"]["stations"]
        # Each station is a dictionary inside the list called "stations"
        return stations

    def get_stations_extra_info(self):
        """Get further info (bike availability) by scraping the website source"""
        raw = requests.get("https://bikemi.com/stazioni").text
        placeholder = '"stationMapPage","slug":null},'
        start = raw.find(placeholder) + len(placeholder)
        end = raw.find('"baseUrl":"https://bikemi.com"')
        station_extra_info_raw = raw[start:end].split("DockGroup:")
        # Each station is a string inside the list called "station_extra_info_list"
        station_extra_info_list = []
        station_list = []
        del station_extra_info_raw[0]  # Remove the first element, which is empty
        # Split the raw code into small chunks of data
        for station in station_extra_info_raw:
            station = station.split(",")
            data = [word for line in station for word in line.split(":")]

            # Create station_list containing only the relevant data
            # Each station with its data is a list
            if len(data) == 49:
                station_list.extend(
                    (
                        data[1],
                        data[2],
                        data[5],
                        data[6],
                        data[9],
                        data[10],
                        data[13],
                        data[14],
                        data[18],
                        data[19],
                        data[20],
                        data[21],
                        data[26],
                        data[28],
                        data[32],
                        data[34],
                        data[38],
                        data[40],
                    )
                )
            if len(data) == 50:  # For the stations with extra address info
                station_list.extend(
                    (
                        data[1],
                        data[2],
                        data[5],
                        data[6],
                        data[9],
                        data[10],
                        data[14],
                        data[15],
                        data[19],
                        data[20],
                        data[21],
                        data[22],
                        data[27],
                        data[29],
                        data[33],
                        data[35],
                        data[39],
                        data[41],
                    )
                )

            # Data cleanup
            titles = station_list[::2]  # Pick only the data placed in odd positions
            info = station_list[1::2]  # Pick only the data placed in even positions
            titles = [
                i.replace('"', "").replace("{", "").replace("id", "station_id")
                for i in titles
            ]
            info = [i.replace('"', "").replace("}", "").replace("]", "") for i in info]
            # Parse the data in a dictionary where "titles" are the keys
            # and "info" are the values
            station_dict = dict(zip(titles, info))
            # Add the newly created dictionary inside a list
            if bool(station_dict) == True:
                station_extra_info_list.append(station_dict)

        # Return a list containing all the stations, stored as dictionaries
        return station_extra_info_list

    def get_stations_full_info(self, get_stations_basic_info, stations_extra_info):
        """Merge basic info gathered from the Open Data (json)
        with the extra info scraped from the website"""
        get_stations_basic_info_sorted = sorted(
            get_stations_basic_info, key=itemgetter("station_id")
        )
        stations_extra_info_sorted = sorted(
            stations_extra_info, key=itemgetter("station_id")
        )
        stations_full_info = [
            a | b
            for (a, b) in zip(
                stations_extra_info_sorted, get_stations_basic_info_sorted
            )
        ]

        return stations_full_info

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
                "[^A-Za-z0-9]+", "", unidecode.unidecode(station["name"])
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
