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

# Initialize colorama
init(autoreset=True)

# Constants
KASPLEX_TESTNET_RPC_URL = "https://rpc.kasplextest.xyz"
CHAIN_ID = 167012
EXPLORER_URL = "https://frontend.kasplextest.xyz/tx/0x"
WKAS_CONTRACT = "0xf40178040278E16c8813dB20a84119A605812FB3"
AMOUNT_KAS = 0.00001  # Fixed amount for swaps
TX_DELAY = 5  # 5 seconds delay between transactions
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}

# Configuration
CONFIG = {
    "MAX_CONCURRENCY": 5,
    "MAX_RETRIES": 3,
    "MINIMUM_BALANCE": 0.001,
    "MIN_GAS_PRICE": Web3.to_wei(1, 'gwei'),  # Minimum gas price to reduce costs
}

# Contract ABI
contract_abi = [
    {"constant": False, "inputs": [], "name": "deposit", "outputs": [], "payable": True, "stateMutability": "payable", "type": "function"},
    {"constant": False, "inputs": [{"name": "wad", "type": "uint256"}], "name": "withdraw", "outputs": [], "payable": False, "stateMutability": "nonpayable", "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
]

# Utility functions
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  KASPLEX TESTNET WRAPPER v1.0 — BY KAZUHA  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}           LETS FUCK THIS TESTNET  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")

def is_valid_private_key(key: str) -> bool:
    key = key.strip()
    if not key.startswith('0x'):
        key = '0x' + key
    try:
        bytes.fromhex(key.replace('0x', ''))
        return len(key) == 66
    except ValueError:
        return False

def load_private_keys(file_path: str = "pky.txt") -> List[str]:
    try:
        if not os.path.exists(file_path):
            print(f"{Fore.RED}Error: pky.txt not found. Creating template...{Style.RESET_ALL}")
            with open(file_path, 'w') as f:
                f.write("# Add private keys here, one per line\n# Example: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef\n")
            sys.exit(1)
        
        valid_keys = []
        with open(file_path, 'r') as f:
            for i, line in enumerate(f, 1):
                key = line.strip()
                if key and not key.startswith('#'):
                    if is_valid_private_key(key):
                        if not key.startswith('0x'):
                            key = '0x' + key
                        valid_keys.append(key)
                    else:
                        print(f"{Fore.YELLOW}Warning: Line {i} invalid key: {key}{Style.RESET_ALL}")
        
        if not valid_keys:
            print(f"{Fore.RED}Error: No valid private keys found{Style.RESET_ALL}")
            sys.exit(1)
        
        print(f"{Fore.GREEN}Loaded {len(valid_keys)} wallets{Style.RESET_ALL}")
        return valid_keys
    except Exception as e:
        print(f"{Fore.RED}Error reading pvkey.txt: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def connect_web3():
    try:
        w3 = Web3(Web3.HTTPProvider(KASPLEX_TESTNET_RPC_URL, request_kwargs={'timeout': 10}))
        if not w3.is_connected():
            print(f"{Fore.RED}Error: Failed to connect to RPC{Style.RESET_ALL}")
            sys.exit(1)
        print(f"{Fore.GREEN}Connected to Kasplex Testnet | Chain ID: {w3.eth.chain_id}{Style.RESET_ALL}")
        return w3
    except Exception as e:
        print(f"{Fore.RED}Error: Web3 connection failed: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

async def wait_for_receipt(w3: Web3, tx_hash: str, max_wait_time: int = 60):
    start_time = asyncio.get_event_loop().time()
    with tqdm(total=max_wait_time, desc="Waiting for TX", bar_format="{l_bar}{bar}| {n:.1f}/{total:.1f}s") as pbar:
        while True:
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    pbar.n = max_wait_time
                    pbar.refresh()
                    return receipt
            except Exception:
                pass
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            pbar.n = min(elapsed_time, max_wait_time)
            pbar.refresh()
            if elapsed_time > max_wait_time:
                return None
            
            await asyncio.sleep(1)

def check_balance(w3: Web3, address: str, contract=None) -> float:
    try:
        if contract is None:
            balance = w3.eth.get_balance(address)
            return float(w3.from_wei(balance, 'ether'))
        else:
            balance = contract.functions.balanceOf(address).call()
            decimals = contract.functions.decimals().call()
            return balance / (10 ** decimals)
    except Exception as e:
        print(f"{Fore.RED}Error: Balance check failed: {str(e)}{Style.RESET_ALL}")
        return -1

async def wrap_kas(w3: Web3, private_key: str, amount_wei: int) -> bool:
    account = Account.from_key(private_key)
    sender_address = account.address
    contract = w3.eth.contract(address=Web3.to_checksum_address(WKAS_CONTRACT), abi=contract_abi)
    
    for attempt in range(CONFIG['MAX_RETRIES']):
        try:
            print(f"{Fore.CYAN}Checking balance...{Style.RESET_ALL}")
            kas_balance = check_balance(w3, sender_address, None)
            wkas_balance = check_balance(w3, sender_address, contract)
            print(f"{Fore.YELLOW}Balance: {kas_balance:.6f} KAS | {wkas_balance:.6f} WKAS{Style.RESET_ALL}")
            if kas_balance < CONFIG['MINIMUM_BALANCE'] or kas_balance < AMOUNT_KAS:
                print(f"{Fore.RED}Error: Insufficient KAS: {kas_balance:.6f} < {max(CONFIG['MINIMUM_BALANCE'], AMOUNT_KAS):.6f}{Style.RESET_ALL}")
                return False

            print(f"{Fore.CYAN}Preparing transaction...{Style.RESET_ALL}")
            nonce = w3.eth.get_transaction_count(sender_address, 'pending')
            network_gas_price = w3.eth.gas_price
            gas_price = max(CONFIG['MIN_GAS_PRICE'], int(network_gas_price * 0.9))  # Reduced gas price
            tx_params = {
                'from': sender_address,
                'to': Web3.to_checksum_address(WKAS_CONTRACT),
                'value': amount_wei,
                'data': '0xd0e30db0',
                'nonce': nonce,
                'chainId': CHAIN_ID,
                'gasPrice': gas_price
            }

            try:
                estimated_gas = w3.eth.estimate_gas(tx_params)
                tx_params['gas'] = int(estimated_gas * 1.05)  # Reduced multiplier
            except Exception as e:
                tx_params['gas'] = 25000  # Lower default gas
                print(f"{Fore.YELLOW}Warning: Gas estimation failed: {str(e)}. Using default: 25000{Style.RESET_ALL}")

            print(f"{Fore.CYAN}Sending transaction...{Style.RESET_ALL}")
            signed_tx = w3.eth.account.sign_transaction(tx_params, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_link = f"{EXPLORER_URL}{tx_hash.hex()}"

            receipt = await wait_for_receipt(w3, tx_hash)
            if receipt is None:
                print(f"{Fore.RED}Error: TX timed out after 60s: {tx_link}{Style.RESET_ALL}")
                return False
            elif receipt.status == 1:
                total_cost = w3.from_wei(receipt['gasUsed'] * tx_params['gasPrice'], 'ether')
                print(f"{Fore.GREEN}Wrapped {AMOUNT_KAS} KAS to WKAS | TX: {tx_link}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Block: {receipt['blockNumber']} | Gas Used: {receipt['gasUsed']} | Cost: {total_cost:.12f} KAS{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}Error: TX failed: {tx_link}{Style.RESET_ALL}")
                return False
        except Exception as e:
            if attempt < CONFIG['MAX_RETRIES'] - 1:
                print(f"{Fore.RED}Error: Attempt {attempt + 1} failed: {str(e)}{Style.RESET_ALL}")
                await asyncio.sleep(2)
                continue
            print(f"{Fore.RED}Error: Failed after {CONFIG['MAX_RETRIES']} attempts: {str(e)}{Style.RESET_ALL}")
            return False
    return False

async def unwrap_wkas(w3: Web3, private_key: str, amount_wei: int) -> bool:
    account = Account.from_key(private_key)
    sender_address = account.address
    contract = w3.eth.contract(address=Web3.to_checksum_address(WKAS_CONTRACT), abi=contract_abi)
    
    for attempt in range(CONFIG['MAX_RETRIES']):
        try:
            print(f"{Fore.CYAN}Checking balance...{Style.RESET_ALL}")
            kas_balance = check_balance(w3, sender_address, None)
            wkas_balance = check_balance(w3, sender_address, contract)
            print(f"{Fore.YELLOW}Balance: {kas_balance:.6f} KAS | {wkas_balance:.6f} WKAS{Style.RESET_ALL}")
            if kas_balance < CONFIG['MINIMUM_BALANCE']:
                print(f"{Fore.RED}Error: Insufficient KAS: {kas_balance:.6f} < {CONFIG['MINIMUM_BALANCE']:.6f}{Style.RESET_ALL}")
                return False
            if wkas_balance < AMOUNT_KAS:
                print(f"{Fore.RED}Error: Insufficient WKAS: {wkas_balance:.6f} < {AMOUNT_KAS:.6f}{Style.RESET_ALL}")
                return False

            print(f"{Fore.CYAN}Preparing transaction...{Style.RESET_ALL}")
            nonce = w3.eth.get_transaction_count(sender_address, 'pending')
            network_gas_price = w3.eth.gas_price
            gas_price = max(CONFIG['MIN_GAS_PRICE'], int(network_gas_price * 0.9))
            amount_hex = format(amount_wei, '064x')
            tx_data = f"0x2e1a7d4d{amount_hex}"
            tx_params = {
                'from': sender_address,
                'to': Web3.to_checksum_address(WKAS_CONTRACT),
                'data': tx_data,
                'nonce': nonce,
                'chainId': CHAIN_ID,
                'gasPrice': gas_price
            }

            try:
                estimated_gas = w3.eth.estimate_gas(tx_params)
                tx_params['gas'] = int(estimated_gas * 1.05)
            except Exception as e:
                tx_params['gas'] = 25000
                print(f"{Fore.YELLOW}Warning: Gas estimation failed: {str(e)}. Using default: 25000{Style.RESET_ALL}")

            print(f"{Fore.CYAN}Sending transaction...{Style.RESET_ALL}")
            signed_tx = w3.eth.account.sign_transaction(tx_params, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_link = f"{EXPLORER_URL}{tx_hash.hex()}"

            receipt = await wait_for_receipt(w3, tx_hash)
            if receipt is None:
                print(f"{Fore.RED}Error: TX timed out after 60s: {tx_link}{Style.RESET_ALL}")
                return False
            elif receipt.status == 1:
                total_cost = w3.from_wei(receipt['gasUsed'] * tx_params['gasPrice'], 'ether')
                print(f"{Fore.GREEN}Unwrapped {AMOUNT_KAS} WKAS to KAS | TX: {tx_link}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Block: {receipt['blockNumber']} | Gas Used: {receipt['gasUsed']} | Cost: {total_cost:.12f} KAS{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}Error: TX failed: {tx_link}{Style.RESET_ALL}")
                return False
        except Exception as e:
            if attempt < CONFIG['MAX_RETRIES'] - 1:
                print(f"{Fore.RED}Error: Attempt {attempt + 1} failed: {str(e)}{Style.RESET_ALL}")
                await asyncio.sleep(2)
                continue
            print(f"{Fore.RED}Error: Failed after {CONFIG['MAX_RETRIES']} attempts: {str(e)}{Style.RESET_ALL}")
            return False
    return False

async def process_wallet(index: int, private_key: str, w3: Web3, cycles: int, action: str) -> int:
    wallet_index = index + 1
    total_wallets = CONFIG.get('TOTAL_WALLETS', 1)
    amount_wei = int(AMOUNT_KAS * 10 ** 18)
    
    print_header()
    print(f"{Fore.MAGENTA}Processing Wallet {wallet_index}/{total_wallets} | Address: {Account.from_key(private_key).address}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")

    successful_txs = 0
    total_txs = cycles if action in ['1', '2'] else cycles * 2
    
    try:
        for cycle in range(1, cycles + 1):
            print(f"{Fore.CYAN}Cycle {cycle}/{cycles}{Style.RESET_ALL}")
            
            if action == '1':
                print(f"{Fore.CYAN}Action: Wrap {AMOUNT_KAS} KAS to WKAS{Style.RESET_ALL}")
                if await wrap_kas(w3, private_key, amount_wei):
                    successful_txs += 1
            elif action == '2':
                print(f"{Fore.CYAN}Action: Unwrap {AMOUNT_KAS} WKAS to KAS{Style.RESET_ALL}")
                if await unwrap_wkas(w3, private_key, amount_wei):
                    successful_txs += 1
            elif action == '3':
                print(f"{Fore.CYAN}Action: Wrap {AMOUNT_KAS} KAS to WKAS{Style.RESET_ALL}")
                if await wrap_kas(w3, private_key, amount_wei):
                    successful_txs += 1
                print(f"{Fore.YELLOW}Pausing {TX_DELAY}s...{Style.RESET_ALL}")
                for _ in tqdm(range(TX_DELAY), desc="Delay", bar_format="{l_bar}{bar}| {n:d}/{total:d}s"):
                    await asyncio.sleep(1)
                print(f"{Fore.CYAN}Action: Unwrap {AMOUNT_KAS} WKAS to KAS{Style.RESET_ALL}")
                if await unwrap_wkas(w3, private_key, amount_wei):
                    successful_txs += 1
            
            if cycle < cycles:
                print(f"{Fore.YELLOW}Pausing {TX_DELAY}s...{Style.RESET_ALL}")
                for _ in tqdm(range(TX_DELAY), desc="Delay", bar_format="{l_bar}{bar}| {n:d}/{total:d}s"):
                    await asyncio.sleep(1)
        
        print(f"{Fore.GREEN if successful_txs > 0 else Fore.RED}Wallet {wallet_index} Completed: {successful_txs}/{total_txs} TXs Successful{Style.RESET_ALL}")
        return successful_txs
    except Exception as e:
        print(f"{Fore.RED}Error: Wallet {wallet_index} failed: {str(e)}{Style.RESET_ALL}")
        return 0

async def main_menu():
    private_keys = load_private_keys()
    random.shuffle(private_keys)
    w3 = connect_web3()
    CONFIG['TOTAL_WALLETS'] = len(private_keys)
    CONFIG['MAX_CONCURRENCY'] = min(CONFIG['MAX_CONCURRENCY'], len(private_keys))

    while True:
        print_header()
        print(f"{Fore.YELLOW}Main Menu{Style.RESET_ALL}")
        print(f"{Fore.CYAN}1. Wrap KAS to WKAS ({AMOUNT_KAS} KAS){Style.RESET_ALL}")
        print(f"{Fore.CYAN}2. Unwrap WKAS to KAS ({AMOUNT_KAS} WKAS){Style.RESET_ALL}")
        print(f"{Fore.CYAN}3. Wrap & Unwrap ({AMOUNT_KAS} KAS/WKAS){Style.RESET_ALL}")
        print(f"{Fore.CYAN}4. Exit{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}")
        
        choice = input(f"{Fore.GREEN}Select option (1-4): {Style.RESET_ALL}").strip()
        if choice not in ['1', '2', '3', '4']:
            print(f"{Fore.RED}Error: Invalid option! Choose 1-4.{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")
            continue
        
        if choice == '4':
            print(f"{Fore.GREEN}Exiting...{Style.RESET_ALL}")
            break

        while True:
            print_header()
            print(f"{Fore.YELLOW}Enter number of cycles (default 1):{Style.RESET_ALL}")
            try:
                cycles = input(f"{Fore.GREEN}Select: {Style.RESET_ALL}").strip()
                cycles = int(cycles) if cycles else 1
                if cycles > 0:
                    break
                print(f"{Fore.RED}Error: Number must be > 0{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Error: Enter a valid number{Style.RESET_ALL}")
            input(f"{Fore.YELLOW}Press Enter to continue...{Style.RESET_ALL}")

        total_txs = len(private_keys) * cycles if choice in ['1', '2'] else len(private_keys) * cycles * 2
        successful_txs = 0

        async def limited_task(index, private_key):
            nonlocal successful_txs
            async with semaphore:
                result = await process_wallet(index, private_key, w3, cycles, choice)
                successful_txs += result
                if index < len(private_keys) - 1:
                    print(f"{Fore.YELLOW}Pausing {TX_DELAY}s...{Style.RESET_ALL}")
                    for _ in tqdm(range(TX_DELAY), desc="Delay", bar_format="{l_bar}{bar}| {n:d}/{total:d}s"):
                        await asyncio.sleep(1)

        semaphore = asyncio.Semaphore(CONFIG['MAX_CONCURRENCY'])
        tasks = [limited_task(i, private_key) for i, private_key in enumerate(private_keys)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print_header()
        print(f"{Fore.GREEN}Summary: {successful_txs}/{total_txs} Transactions Successful{Style.RESET_ALL}")
        input(f"{Fore.YELLOW}Press Enter to return to menu...{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main_menu())
