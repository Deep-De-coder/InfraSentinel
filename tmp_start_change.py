import requests

infra_key = "9c1gDr6FXV4ypGQLBe0A3afJt5qTvHon"
url = "http://127.0.0.1:8080/v1/changes/start"
payload = {"change_id": "CHG-001", "scenario": "CHG-001_A"}

r = requests.post(url, json=payload, headers={"X-INFRA-KEY": infra_key})
print("status:", r.status_code)
print(r.text)
r.raise_for_status()
