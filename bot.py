# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import random
import time
from web3 import Web3
from eth_account import Account
from colorama import init, Fore, Style
from typing import List
from tqdm import tqdm

# Global proxy flag
USE_PROXIES = None

# Terminal setup
init(autoreset=True)

# Constants
KASPLEX_TESTNET_RPC_URL = "https://rpc.kasplextest.xyz"
CHAIN_ID = 167012
EXPLORER_URL = "https://frontend.kasplextest.xyz/tx/0x"
WKAS_CONTRACT = "0xf40178040278E16c8813dB20a84119A605812FB3"
AMOUNT_KAS = 0.00001
TX_DELAY = 5
INTERVAL_HOURS = 24

CONFIG = {
    "MAX_CONCURRENCY": 5,
    "MAX_RETRIES": 3,
    "MINIMUM_BALANCE": 0.001,
    "MIN_GAS_PRICE": Web3.to_wei(1, 'gwei')
}

contract_abi = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
    {"constant": False, "inputs": [{"name": "wad", "type": "uint256"}], "name": "withdraw", "outputs": [], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
]

def load_proxy_list(path="proxies.txt"):
    proxies = []
    if not os.path.exists(path):
        print(f"{Fore.YELLOW}No proxies.txt found. Running without proxies.{Style.RESET_ALL}")
        return proxies
    with open(path, 'r') as f:
        for line in f:
            proxy = line.strip()
            if proxy and not proxy.startswith('#'):
                proxies.append(proxy)
    return proxies

def is_valid_private_key(key):
    key = key.strip()
    if not key.startswith("0x"):
        key = "0x" + key
    try:
        bytes.fromhex(key[2:])
        return len(key) == 66
    except:
        return False

def load_private_keys(path="pky.txt"):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write("# Add private keys here\n")
        sys.exit("Created pky.txt. Add private keys and re-run.")
    keys = []
    with open(path, 'r') as f:
        for line in f:
            k = line.strip()
            if k and not k.startswith('#') and is_valid_private_key(k):
                if not k.startswith('0x'):
                    k = '0x' + k
                keys.append(k)
    return keys

def connect_web3(proxy_url=None):
    try:
        request_kwargs = {'timeout': 10}
        if proxy_url:
            request_kwargs['proxies'] = {
                'http': proxy_url,
                'https': proxy_url
            }
            import requests
            test_url = "https://rpc.kasplextest.xyz"
            try:
                resp = requests.post(test_url, json={}, proxies=request_kwargs['proxies'], timeout=10)
                if resp.status_code != 200:
                    print(f"{Fore.YELLOW}Warning: Proxy responded with status {resp.status_code}. Continuing anyway...{Style.RESET_ALL}")
            except Exception as test_error:
                print(f"{Fore.YELLOW}Warning: Proxy test failed: {test_error}. Continuing anyway...{Style.RESET_ALL}")
        w3 = Web3(Web3.HTTPProvider(KASPLEX_TESTNET_RPC_URL, request_kwargs=request_kwargs))
        if not w3.is_connected():
            raise Exception("Web3 connection failed")
        return w3
    except Exception as e:
        print(f"{Fore.RED}Web3 connection error: {e}{Style.RESET_ALL}")
        return None

async def ask_use_proxies():
    global USE_PROXIES
    while True:
        choice = input(f"{Fore.CYAN}Do you want to use proxies? (y/n): {Style.RESET_ALL}").strip().lower()
        if choice in ['y', 'yes']:
            USE_PROXIES = True
            break
        elif choice in ['n', 'no']:
            USE_PROXIES = False
            break
        else:
            print(f"{Fore.RED}Please enter 'y' or 'n'.{Style.RESET_ALL}")

def print_menu():
    print(f"{Fore.CYAN}Select mode:{Style.RESET_ALL}")
    print("1. Wrap KAS to WKAS")
    print("2. Unwrap WKAS to KAS")
    print("3. Wrap then Unwrap")
    print("4. Auto run every 24hr")
    print("5. Exit")

def print_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Fore.CYAN}{'═'*60}\n  KASPLEX WRAPPER — BY KAZUHA - EDITED BY NGUYEN\n{'═'*60}{Style.RESET_ALL}")

# --- wrap_kas, unwrap_wkas, process_wallet, run_action_cycle ---

async def wrap_kas(w3, private_key, amount_wei):
    from_address = Account.from_key(private_key).address
    contract = w3.eth.contract(address=Web3.to_checksum_address(WKAS_CONTRACT), abi=contract_abi)
    try:
        balance = w3.eth.get_balance(from_address)
        if balance < amount_wei:
            print(f"{Fore.RED}Insufficient KAS balance ({w3.from_wei(balance, 'ether')} KAS){Style.RESET_ALL}")
            return False
        nonce = w3.eth.get_transaction_count(from_address)
        gas_price = max(CONFIG['MIN_GAS_PRICE'], w3.eth.gas_price)
        tx = {
            'from': from_address,
            'to': Web3.to_checksum_address(WKAS_CONTRACT),
            'value': amount_wei,
            'data': '0xd0e30db0',
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': CHAIN_ID,
        }
        try:
            tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.05)
        except:
            tx['gas'] = 30000
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(getattr(signed_tx, 'rawTransaction', signed_tx.raw_transaction))
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"{Fore.GREEN}Wrap successful | TX: {tx_hash.hex()} | Block: {receipt.blockNumber} | Gas: {receipt.gasUsed}{Style.RESET_ALL}")
        return receipt.status == 1
    except Exception as e:
        print(f"{Fore.RED}Wrap Error: {e}{Style.RESET_ALL}")
        return False

async def unwrap_wkas(w3, private_key, amount_wei):
    from_address = Account.from_key(private_key).address
    contract = w3.eth.contract(address=Web3.to_checksum_address(WKAS_CONTRACT), abi=contract_abi)
    try:
        balance = contract.functions.balanceOf(from_address).call()
        if balance < amount_wei:
            print(f"{Fore.RED}Insufficient WKAS balance ({balance / 1e18:.6f}){Style.RESET_ALL}")
            return False
        nonce = w3.eth.get_transaction_count(from_address)
        gas_price = max(CONFIG['MIN_GAS_PRICE'], w3.eth.gas_price)
        amount_hex = format(amount_wei, '064x')
        tx_data = f"0x2e1a7d4d{amount_hex}"
        tx = {
            'from': from_address,
            'to': Web3.to_checksum_address(WKAS_CONTRACT),
            'data': tx_data,
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': CHAIN_ID,
        }
        try:
            tx['gas'] = int(w3.eth.estimate_gas(tx) * 1.05)
        except:
            tx['gas'] = 30000
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(getattr(signed_tx, 'rawTransaction', signed_tx.raw_transaction))
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"{Fore.GREEN}Unwrap successful | TX: {tx_hash.hex()} | Block: {receipt.blockNumber} | Gas: {receipt.gasUsed}{Style.RESET_ALL}")
        return receipt.status == 1
    except Exception as e:
        print(f"{Fore.RED}Unwrap Error: {e}{Style.RESET_ALL}")
        return False

async def process_wallet(index, private_key, proxy, action):
    address = Account.from_key(private_key).address
    print(f"{Fore.MAGENTA}Processing Wallet {index + 1} | Address: {address}{Style.RESET_ALL}")
    if proxy:
        print(f"{Fore.CYAN}Using proxy: {proxy}{Style.RESET_ALL}")
    w3 = connect_web3(proxy)
    if not w3:
        return 0
    amount_wei = int(AMOUNT_KAS * 1e18)
    kas_balance = w3.eth.get_balance(address)
    contract = w3.eth.contract(address=Web3.to_checksum_address(WKAS_CONTRACT), abi=contract_abi)
    wkas_balance = contract.functions.balanceOf(address).call()
    print(f"{Fore.YELLOW}Balance: {w3.from_wei(kas_balance, 'ether'):.6f} KAS | {wkas_balance / 1e18:.6f} WKAS{Style.RESET_ALL}")
    if kas_balance < Web3.to_wei(CONFIG['MINIMUM_BALANCE'], 'ether') and wkas_balance < amount_wei:
        print(f"{Fore.RED}Skipping wallet {index + 1}: Insufficient KAS and WKAS{Style.RESET_ALL}")
        return 0
    if action == '1':
        return await wrap_kas(w3, private_key, amount_wei)
    elif action == '2':
        return await unwrap_wkas(w3, private_key, amount_wei)
    elif action == '3':
        await wrap_kas(w3, private_key, amount_wei)
        await asyncio.sleep(TX_DELAY)
        return await unwrap_wkas(w3, private_key, amount_wei)
    return 0

async def run_action_cycle(action):
    private_keys = load_private_keys()
    proxies = load_proxy_list() if USE_PROXIES else []
    success_count = 0
    skipped_wallets = 0
    async def run_wallet(i, key):
        nonlocal success_count, skipped_wallets
        proxy = random.choice(proxies) if proxies else None
        result = await process_wallet(i, key, proxy, action)
        if result:
            success_count += 1
        else:
            skipped_wallets += 1
    tasks = [run_wallet(i, key) for i, key in enumerate(private_keys)]
    await asyncio.gather(*tasks)
    print(f"{Fore.GREEN}✓ Cycle completed | Success: {success_count} | Skipped: {skipped_wallets} | Total: {len(private_keys)}{Style.RESET_ALL}")

async def main():
    await ask_use_proxies()
    while True:
        print_header()
        print_menu()
        choice = input(f"{Fore.GREEN}Enter your choice: {Style.RESET_ALL}").strip()
        if choice not in ['1', '2', '3', '4', '5']:
            print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
            await asyncio.sleep(2)
            continue
        if choice == '5':
            print("Exiting...")
            break
        elif choice == '4':
            while True:
                print(f"{Fore.CYAN}Running all features (1 → 3)...{Style.RESET_ALL}")
                await run_action_cycle('1')
                await asyncio.sleep(TX_DELAY)
                await run_action_cycle('2')
                await asyncio.sleep(TX_DELAY)
                await run_action_cycle('3')
                print(f"{Fore.CYAN}Waiting {INTERVAL_HOURS} hours for next auto cycle...{Style.RESET_ALL}")
                await asyncio.sleep(INTERVAL_HOURS * 3600)
        else:
            await run_action_cycle(choice)
            input(f"{Fore.YELLOW}Press Enter to return to menu...{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())
