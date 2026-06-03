import urllib.request
import json

url = "https://veklom.com/api/v1/connectors/fax/inbound"
payload = {
    "sender_number": "+15550192",
    "receiver_number": "+18005550100",
    "document_url": "https://storage.veklom.com/faxes/patient_clinical_intake_form.pdf"
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    response = urllib.request.urlopen(req)
    print("SUCCESS STATUS:", response.getcode())
    print("RESPONSE BODY:")
    print(json.dumps(json.loads(response.read().decode("utf-8")), indent=2))
except Exception as e:
    print("ERROR:")
    print(e)
