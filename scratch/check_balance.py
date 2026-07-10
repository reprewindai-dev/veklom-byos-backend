
from web3 import Web3
from eth_account import Account

pk = "cc347eb918f18772b2a6bc5e403ae75db8688a194077dd02209974f6cf8c274f"
acct = Account.from_key(pk)
print(f"Private Key derives to: {acct.address}")

w3_sepolia = Web3(Web3.HTTPProvider("https://sepolia.base.org"))
w3_mainnet = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

print(f"Balance on Sepolia: {w3_sepolia.from_wei(w3_sepolia.eth.get_balance(acct.address), 'ether')} ETH")
print(f"Balance on Mainnet: {w3_mainnet.from_wei(w3_mainnet.eth.get_balance(acct.address), 'ether')} ETH")

f970 = "0x3a74772e925b54F7dAD7FD95c9Ba30825033f970"
print(f"\nF970 Sepolia Balance: {w3_sepolia.from_wei(w3_sepolia.eth.get_balance(f970), 'ether')} ETH")
print(f"F970 Mainnet Balance: {w3_mainnet.from_wei(w3_mainnet.eth.get_balance(f970), 'ether')} ETH")

