import requests
app = requests.get('http://5.78.135.11:8000/api/v1/applications/qg8ks04044so8cwooko4swww', headers={'Authorization': 'Bearer 35|bebXAUHPDJw509LsGDr0BVG8qI354iWdVZmohKt5469cc08b', 'Accept': 'application/json'}).json()
print("FQDN:", app.get('fqdn'))
print("Status:", app.get('status'))
print("Ports:", app.get('ports_exposes'))
