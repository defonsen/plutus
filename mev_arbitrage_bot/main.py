# main.py

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

from utils.logger import logger
from strategies.uniswap_sushi_strategy import UniswapSushiStrategy
from flashbots_service import send_flashbots_bundle

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="MEV Arbitrage Bot (Testnet)",
    description="A demonstration MEV bot for testnet with Uniswap-Sushi arbitrage & Flashbots integration.",
    version="1.0.0",
)

# Retrieve environment variables
WEB3_PROVIDER_URL = os.getenv("WEB3_PROVIDER_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Validate environment variables
if not WEB3_PROVIDER_URL or not PRIVATE_KEY:
    logger.error("Missing environment variables WEB3_PROVIDER_URL or PRIVATE_KEY")
    raise Exception("Missing environment variables WEB3_PROVIDER_URL or PRIVATE_KEY")

# Connect to testnet
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
if not w3.is_connected():

    logger.error("Failed to connect to the testnet. Check your URL/Internet.")
    raise Exception("Web3 connection failed")

# Prepare account from private key
account = Account.from_key(PRIVATE_KEY)
WALLET_ADDRESS = account.address
logger.info(f"Bot wallet address: {WALLET_ADDRESS}")

# Instantiate strategy
uniswap_sushi_strategy = UniswapSushiStrategy(w3, account)

# Define Pydantic model for swap request
class SwapRequest(BaseModel):
    tokenA: str
    tokenB: str
    amount: float  # in terms of tokenA's quantity

# Define root endpoint
@app.get("/")
def root():
    return {"message": "MEV Arbitrage Bot (Testnet) is online!"}

# Define arbitrage endpoint
@app.post("/arbitrage")
def execute_arbitrage(req: SwapRequest):
    """
    Endpoint that the frontend will call when user wants to attempt an arbitrage swap.
    """
    tokenA = req.tokenA.upper()
    tokenB = req.tokenB.upper()
    amount = req.amount

    if tokenA == tokenB:
        raise HTTPException(status_code=400, detail="TokenA and TokenB cannot be the same.")

    logger.info(f"Received request: {tokenA} -> {tokenB}, amount={amount}")

    # 1) Find arbitrage opportunity
    try:
        (profitable, buy_on, sell_on, profit_estimate) = uniswap_sushi_strategy.find_arbitrage_opportunity(tokenA, tokenB, amount)
    except Exception as e:
        logger.error(f"Error finding arbitrage opportunity: {e}")
        raise HTTPException(status_code=500, detail="Error finding arbitrage opportunity.")

    if not profitable:
        return {
            "message": "No profitable arbitrage found.",
            "profit_estimate": 0.0
        }

    logger.info(f"Arbitrage found! Buy on {buy_on}, sell on {sell_on}, estimated profit ~ {profit_estimate}")

    # 2) Craft transactions
    try:
        tx_dicts = uniswap_sushi_strategy.execute_arbitrage(tokenA, tokenB, amount, buy_on, sell_on)
    except Exception as e:
        logger.error(f"Error executing arbitrage strategy: {e}")
        raise HTTPException(status_code=500, detail="Error executing arbitrage strategy.")

    # 3) Sign transactions
    signed_txs = []
    try:
        current_nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
        for tx in tx_dicts:
            # Set nonce and chain ID
            tx["nonce"] = current_nonce
            tx["chainId"] = w3.eth.chain_id
            # Sign transaction
            signed = account.sign_transaction(tx)
            signed_txs.append(signed.rawTransaction.hex())
            current_nonce += 1
    except Exception as e:
        logger.error(f"Error signing transactions: {e}")
        raise HTTPException(status_code=500, detail="Error signing transactions.")

    # 4) Send as Flashbots bundle
    try:
        block_number = w3.eth.block_number
        logger.info(f"Submitting bundle to Flashbots for block {block_number + 1} ...")
        fb_response = send_flashbots_bundle(w3, signed_txs, block_number + 1, WALLET_ADDRESS)
    except Exception as e:
        logger.error(f"Error sending Flashbots bundle: {e}")
        fb_response = None

    if fb_response is None:
        # Fallback to normal broadcast
        try:
            tx_hashes = []
            for raw_tx in signed_txs:
                tx_hash = w3.eth.send_raw_transaction(raw_tx)
                tx_hashes.append(tx_hash.hex())
            return {
                "message": "Arbitrage executed via normal broadcast (no valid Flashbots response on testnet).",
                "tx_hashes": tx_hashes,
                "profit_estimate": profit_estimate
            }
        except Exception as e:
            logger.error(f"Error broadcasting transactions: {e}")
            raise HTTPException(status_code=500, detail="Error broadcasting transactions.")

    return {
        "message": "Arbitrage bundle submitted to Flashbots",
        "flashbots_response": fb_response,
        "profit_estimate": profit_estimate
    }
