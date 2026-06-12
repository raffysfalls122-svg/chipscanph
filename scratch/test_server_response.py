import urllib.request
import json

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/api/prices/") as response:
        html = response.read()
        print("Response Code:", response.getcode())
        print("Data:", json.loads(html.decode('utf-8')))
except Exception as e:
    print("Error connecting to server:", e)
