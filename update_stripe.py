import stripe
import os
import sys

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
account_id = sys.argv[1]

try:
    account = stripe.Account.retrieve(account_id)
    print("Currently due:", account.requirements.currently_due)
    
    # In test mode, bypassing usually just means providing a test token for the document
    # or just updating the business profile and TOS.
    # We will provide generic test data to bypass the KYC.
    res = stripe.Account.modify(
        account_id,
        tos_acceptance={"date": 1609459200, "ip": "8.8.8.8"},
        business_profile={"mcc": "5734", "url": "https://veklom.com"},
        company={
            "address": {"line1": "123 Test St", "city": "Test City", "state": "NY", "postal_code": "10001"},
            "name": "Test Company",
            "phone": "8888675309",
            "tax_id": "000000000",
        },
        # You can bypass document uploads by passing the test file token: file_identity_document_success
        individual={
            "first_name": "Test",
            "last_name": "User",
            "dob": {"day": 1, "month": 1, "year": 1990},
            "address": {"line1": "123 Test St", "city": "Test City", "state": "NY", "postal_code": "10001"},
            "email": "test@example.com",
            "phone": "8888675309",
            "verification": {
                "document": {"front": "file_identity_document_success"}
            }
        }
    )
    print("Success! Account updated.")
    
    account = stripe.Account.retrieve(account_id)
    print("Still due:", account.requirements.currently_due)
    
except Exception as e:
    print(f"Error: {e}")
