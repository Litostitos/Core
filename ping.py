import requests

print(requests.get("http://localhost:5000/store/debug/list").text)