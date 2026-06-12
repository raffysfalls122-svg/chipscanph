import requests

url = "http://127.0.0.1:8000/api/chips/?role=admin&username=admin"
payload = {
    "code": "KMRX1000BM",
    "grade": "A1",
    "size": "16GB",
    "type": "eMMC",
    "status": "coded",
    "note": "Saved as non-code entry"
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload)
print("Status Code:", response.status_code)
print("Response:", response.json())
