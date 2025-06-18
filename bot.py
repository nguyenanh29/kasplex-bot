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
    print(f"{Fore.CYAN}           EDITED BY NGUYEN  {Style.RESET_ALL}")
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

