import datetime
import os
from dotenv import load_dotenv
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from pymongo import MongoClient
from math import radians, cos, sin, asin, sqrt
from sklearn.cluster import OPTICS
from labellines import labelLines
import random

load_dotenv()

CONNECTION_STRING = os.getenv('CONNECTION_STRING')
client = MongoClient(host=CONNECTION_STRING)
loadDb = client.LoadDetail
metadataDb = client.metadata
today = datetime.datetime.now()

CHICAGO = [102, 106, 274, 267, 130, 126, 278, 125, 127, 129, 105, 122, 268, 124, 123, 284, 285]
CONTINENTAL_US = [ 'AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FM', 'FL', 'GA', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY' ]

def pull_location_data():

    response = loadDb['v4loadDetail'].find({
        "PickupDate": {
            "$gte": datetime.datetime(2024,4,1),
            "$lte": datetime.datetime(2024,5,1)
        },
        "LoadStatus": {
            "$in": ['Delivered', 'Dispatched', 'Planned']
        },
        "OriginData.OriginLatitude": {
            "$exists": True
        },
        "OriginData.OriginLongitude": {
            "$exists": True
        },
        "DestinationData.DestinationLatitude": {
            "$exists": True
        },
        "DestinationData.DestinationLongitude": {
            "$exists": True
        },
        "EquipmentType": {
            "$eq": "Van"
        },
        "CustomerTerminalCode": {
            "$in": CHICAGO
        },
        "LoadSize": {
            "$eq": "FTL"
        },
        "RateData.GrossRevenue": {
            "$gte": 250
        },
        "RateData.GrossTransCost": {
            "$gte": 250
        }
    },
    {
        "_id": 0,
        "load_id": "$LoadID",
        "customer": "$Customer",
        "equipment": "$EquipmentType",
        "carrier": "$Carrier",
        "customer_rate": "$RateData.GrossRevenue",
        "truck_rate": "$RateData.GrossTransCost",
        "mileage": "$RateData.Miles",
        "pickup_date": "$PickupDate",
        "origin_city": "$OriginData.OriginCity",
        "origin_state": "$OriginData.OriginState",
        "origin_latitude": "$OriginData.OriginLatitude",
        "origin_longitude": "$OriginData.OriginLongitude",
        "destination_city": "$DestinationData.DestinationCity",
        "destination_state": "$DestinationData.DestinationState",
        "destination_latitude": "$DestinationData.DestinationLatitude",
        "destination_longitude": "$DestinationData.DestinationLongitude"
    })

    loads = []
    for load in response:
        loads.append(load)

    #LOAD TO RIDE TRANSPORTATION LLC
    #CIRCLE LOGISTICS, INC.
    #Zoom Trucking Inc
    #YU EXPRESS
    #1628939 ONTARIO LTD
    #Ampro Innovations Llc
    #Samra Trucking Llc
    #NORTH EAST LOGISTICS LLC
    #City Freight Llc
    #Infiniti Freight Logistics
    #Deta Logistics Llc
    #Bolt Express LLC
    #Rvn Logistics Inc
    #GP TRANSCO
    #Double Diamond Transport Inc
    #Nice Guys Llc
    #N-TRANS INC **
    #Erives Enterprises Inc
    #BLUE RHINO LOGISTICS LLC
    #Green Line Logistics, Inc.
    #DC TRANSPORT INC

    loads = pd.DataFrame.from_dict(loads)
    #loads.to_csv('carrier_data.csv')

    return loads

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees) 

    Thanks Michael Dunn on stackoverflow.
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.

    return c * r

def flow_distance(array1, array2):
    """ Credit Tao and Thill (2016) for the original flow distance metric which uses euclidean distance. Euclidean is fine
    When dealing with short intra-city travel, but on this scale we really need the haversine distance, so that change has
    been made.
    Arrays should be ordered 
    origin lat
    origin long
    destination lat
    destination long
    """

    distance_between_origins = haversine(array1[1], array1[0], array2[1], array2[0])
    distance_between_destinations = haversine(array1[3], array1[2], array2[3], array2[2])
    array1_distance = haversine(array1[1], array1[0], array1[3], array1[2])
    array2_distance = haversine(array2[1], array2[0], array2[3], array2[2])

    if array1_distance == 0:
        array1_distance = 1

    if array2_distance == 0:
        array2_distance = 1

    distance_squared = ( (distance_between_origins **  2) + (distance_between_destinations ** 2) ) / ( ( array1_distance * array2_distance ) ** 0.5)
    distance = sqrt(distance_squared)

    return distance

def reverse_geocode(lat, long):

    response = metadataDb['unique-zips'].find_one({
        "geoJSON": {
            "$near": {
                "type": "Point",
                "coordinates": [long, lat]
            }
        }
    },
    {
        "_id": 0,
        "city": "$City",
        "state": "$State_Province"
    })

    return response

def find_cluster_metadata(data):

    cluster_labels = pd.unique(data['cluster'])
    
    cluster_metadata = []
    for cluster in cluster_labels:

        cluster_data = data[data['cluster']==cluster]

        cluster_origin_centroid_latitude = cluster_data['origin_latitude'].sum()/len(cluster_data)
        cluster_origin_centroid_longitude = cluster_data['origin_longitude'].sum()/len(cluster_data)
        origin = reverse_geocode(cluster_origin_centroid_latitude, cluster_origin_centroid_longitude)
        origin_city = origin['city']
        origin_state = origin['state']
        cluster_destination_centroid_latitude = cluster_data['destination_latitude'].sum()/len(cluster_data)
        cluster_destination_centroid_longitude = cluster_data['destination_longitude'].sum()/len(cluster_data)
        destination = reverse_geocode(cluster_destination_centroid_latitude, cluster_destination_centroid_longitude)
        destination_city = destination['city']
        destination_state = destination['state']

        avg_mileage = cluster_data['mileage'].mean()
        avg_customer_rate = cluster_data['customer_rate'].mean()
        avg_customer_rpm = cluster_data['customer_rate'].sum() / cluster_data['mileage'].sum()
        avg_truck_rate = cluster_data['truck_rate'].mean()
        avg_truck_rpm = cluster_data['truck_rate'].sum() / cluster_data['mileage'].sum()

        num_carriers = len(pd.unique(cluster_data['carrier']))

        cluster_object = {
            "cluster": cluster,
            "lanes_in_cluster": len(cluster_data),
            "num_carriers": num_carriers,
            "avg_mileage": avg_mileage,
            "avg_customer_rate": avg_customer_rate,
            "avg_customer_rpm": avg_customer_rpm,
            "avg_truck_rate": avg_truck_rate,
            "avg_truck_rpm": avg_truck_rpm,
            "origin_city": origin_city,
            "origin_state": origin_state,
            "destination_city": destination_city,
            "destination_state": destination_state,
            "cluster_origin_centroid_latitude": cluster_origin_centroid_latitude,
            "cluster_origin_centroid_longitude": cluster_origin_centroid_longitude,
            "cluster_destination_centroid_latitude": cluster_destination_centroid_latitude,
            "cluster_destination_centroid_longitude": cluster_destination_centroid_longitude
        }

        cluster_metadata.append(cluster_object)

    cluster_metadata = pd.DataFrame.from_dict(cluster_metadata)

    return cluster_metadata

def make_color_list(n):

    colors = []

    for i in range(n):

        color = "%06x" % random.randint(0, 0xFFFFFF)
        color = "#" + color

        colors.append(color)

    return colors

def plot_clusters(data):

    us_map = gpd.read_file("./files/shapefile/tl_2023_us_state.shp")
    us_map = us_map[us_map['STUSPS'].isin(CONTINENTAL_US)]
    fig, ax = plt.subplots(figsize=(10,10))
    us_map.plot(ax=ax)

    outlier_data = data[data['cluster'] < 0]
    data = data[data['cluster'] >= 0]

    cluster_metadata = find_cluster_metadata(data)
    colors = make_color_list(len(cluster_metadata))

    cluster_metadata['color'] = ""
    cluster_metadata['color'] = cluster_metadata['cluster'].apply(lambda d: colors[d])

    data['color'] = ""
    data['color'] = data['cluster'].apply(lambda d: colors[d])

    top_volume_clusters = cluster_metadata.sort_values(by="lanes_in_cluster")['cluster'][-25:].to_list()
    #print(top_volume_clusters)

    """ Creating the shapes for the cluster centroid lines """
    geo_cluster_metadata = gpd.GeoDataFrame(cluster_metadata[cluster_metadata['cluster'].isin(top_volume_clusters)])
    geo_cluster_metadata['origin_point'] = gpd.points_from_xy(geo_cluster_metadata['cluster_origin_centroid_longitude'], geo_cluster_metadata['cluster_origin_centroid_latitude'], crs="EPSG:4326")
    geo_cluster_metadata['destination_point'] = gpd.points_from_xy(geo_cluster_metadata['cluster_destination_centroid_longitude'], geo_cluster_metadata['cluster_destination_centroid_latitude'], crs="EPSG:4326")
    geo_cluster_metadata['line'] = geo_cluster_metadata.apply(lambda row: LineString([row['origin_point'], row['destination_point']]), axis=1)
    geo_cluster_metadata = geo_cluster_metadata.set_geometry(geo_cluster_metadata['line'])
    
    """ Creating the shapes for the actual lanes that are within clusters """
    geo_data = gpd.GeoDataFrame(data[data['cluster'].isin(top_volume_clusters)])
    geo_data['origin_point'] = gpd.points_from_xy(geo_data['origin_longitude'], geo_data['origin_latitude'], crs="EPSG:4326")
    geo_data['destination_point'] = gpd.points_from_xy(geo_data['destination_longitude'], geo_data['destination_latitude'], crs="EPSG:4326")
    geo_data['line'] = geo_data.apply(lambda row: LineString([row['origin_point'], row['destination_point']]), axis=1)

    """ Creating the shapes for the lanes that werent found to be in any cluster """
    geo_outlier_data = gpd.GeoDataFrame(outlier_data)
    geo_outlier_data['origin_point'] = gpd.points_from_xy(geo_outlier_data['origin_longitude'], geo_outlier_data['origin_latitude'], crs="EPSG:4326")
    geo_outlier_data['destination_point'] = gpd.points_from_xy(geo_outlier_data['destination_longitude'], geo_outlier_data['destination_latitude'], crs="EPSG:4326")
    geo_outlier_data['line'] = geo_outlier_data.apply(lambda row: LineString([row['origin_point'], row['destination_point']]), axis=1)

    origin_geo_data = geo_data.set_geometry(geo_data['origin_point'])
    destination_geo_data = geo_data.set_geometry(geo_data['destination_point'])
    line_geo_data = geo_data.set_geometry(geo_data['line'])

    origin_geo_outlier_data = geo_outlier_data.set_geometry(geo_outlier_data['origin_point'])
    destination_geo_outlier_data = geo_outlier_data.set_geometry(geo_outlier_data['destination_point'])
    #origin_outlier_g = origin_geo_outlier_data.plot(ax=ax, color="gray", alpha=0.25, marker="o", markersize=2)
    #destination_outlier_g = destination_geo_outlier_data.plot(ax=ax, color="gray", alpha=0.25, marker="x", markersize=2)
    line_geo_outlier_data = geo_outlier_data.apply(lambda row: LineString([row['origin_point'], row['destination_point']]), axis=1)

    #line_outlier_g = line_geo_outlier_data.plot(ax=ax, color="gray", linewidth=1, alpha=0.5)
    line_actual_g = line_geo_data.plot(ax=ax, color=line_geo_data['color'], linewidth=1, alpha=0.20)
    cluster_g = geo_cluster_metadata.plot(ax=ax, color=geo_cluster_metadata['color'], linewidth=3, alpha=.9, label=str(geo_cluster_metadata['cluster']))
    labelLines(cluster_g.get_lines(), zorder=2.5)
    origin_g = origin_geo_data.plot(ax=ax, color=origin_geo_data['color'], alpha=0.5, marker="o")
    destination_g = destination_geo_data.plot(ax=ax, color=destination_geo_data['color'], alpha=0.5, marker=">") 

    print(geo_cluster_metadata.sort_values(by="lanes_in_cluster",ascending=False)[['cluster','lanes_in_cluster', 'num_carriers', 'avg_mileage','origin_city', 'origin_state', 'destination_city', 'destination_state', "avg_customer_rpm", "avg_truck_rpm"]])
    geo_cluster_metadata.sort_values(by="lanes_in_cluster",ascending=False)[['cluster','lanes_in_cluster', 'num_carriers', 'avg_mileage','origin_city', 'origin_state', 'destination_city', 'destination_state', "avg_customer_rpm", "avg_truck_rpm"]].to_csv("van_lanes.csv")
    geo_data.to_csv("loads_per_cluster.csv")
    #print(geo_data)

    plt.show()


def __main__():

    data = pull_location_data()

    X = data[['origin_latitude', 'origin_longitude', 'destination_latitude', 'destination_longitude']].to_numpy()
    print(data.head())
    print(str(len(data)) + " lanes pulled")
    print("Started at " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    clustering = OPTICS(min_samples=10,
                        max_eps = 3.75, 
                        metric=flow_distance, 
                        cluster_method="dbscan",
                        n_jobs=-1).fit(X)

    print("Finished at " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print(str(len(pd.unique(clustering.labels_))-1) + " clusters found.")

    data['cluster'] = clustering.labels_
    #print(data.sort_values(by='cluster'))

    #print(data['cluster'].value_counts())

    plot_clusters(data)

    return

__main__()