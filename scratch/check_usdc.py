
from web3 import Web3
from eth_account import Account
import json

pk = "cc347eb918f18772b2a6bc5e403ae75db8688a194077dd02209974f6cf8c274f"
acct = Account.from_key(pk)
w3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))

usdc_address = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
usdc_abi = json.loads('[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]')

contract = w3.eth.contract(address=usdc_address, abi=usdc_abi)
bal = contract.functions.balanceOf(acct.address).call()
print(f"USDC Balance for {acct.address}: {bal / 10**6} USDC")

