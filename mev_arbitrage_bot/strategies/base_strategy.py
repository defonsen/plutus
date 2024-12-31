# strategies/base_strategy.py

class BaseArbitrageStrategy:
    def __init__(self, web3, account):
        self.web3 = web3
        self.account = account

    def find_arbitrage_opportunity(self, tokenA, tokenB, amount):
        """
        Returns a tuple: (profitable: bool, buy_on: str, sell_on: str, profit_estimate: float)
        Or (False, None, None, 0) if no profitable opportunity.
        """
        raise NotImplementedError("Must implement find_arbitrage_opportunity")
    
    def execute_arbitrage(self, tokenA, tokenB, amount, buy_on, sell_on):
        """
        Actually execute the arbitrage steps. 
        This might involve multiple transactions.
        """
        raise NotImplementedError("Must implement execute_arbitrage")
