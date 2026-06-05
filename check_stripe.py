import stripe
import os
import sys

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
account_id = "acct_1TefVaHAFRy91lPH"

try:
    account = stripe.Account.retrieve(account_id)
    print(f"Charges Enabled: {account.charges_enabled}")
    print(f"Details Submitted: {account.details_submitted}")
    print(f"Payouts Enabled: {account.payouts_enabled}")
    print(f"Due: {account.requirements.currently_due}")
except Exception as e:
    print(f"Error: {e}")
