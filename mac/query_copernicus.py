import urllib.request
import json

url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name%20eq%20'SENTINEL-1'%20and%20OData.CSC.Intersects(area=geography'SRID=4326;POLYGON((81.1782861%2018.6668167,%2081.2088583%2018.6668167,%2081.2088583%2018.6973278,%2081.1782861%2018.6973278,%2081.1782861%2018.6668167))')%20and%20contains(Name,'GRD')&$top=1&$orderby=ContentDate/Start%20desc"

req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    if data.get("value"):
        print(json.dumps(data["value"][0], indent=2))
    else:
        print("No results found.")
