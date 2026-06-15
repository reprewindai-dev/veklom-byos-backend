import requests
apps = requests.get('http://5.78.135.11:8000/api/v1/applications', headers={'Authorization': 'Bearer 35|bebXAUHPDJw509LsGDr0BVG8qI354iWdVZmohKt5469cc08b', 'Accept': 'application/json'}).json()
for a in apps:
    print(f"{a.get('name')} | {a.get('uuid')} | {a.get('fqdn')} | {a.get('status')}")
