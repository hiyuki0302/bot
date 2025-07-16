import pybotters
import json
import asyncio
import sys
import pandas as pd

class kline:
    def __init__(self, symbol:str, client:pybotters.Client):
        # Parameter
        self.symbol = symbol

        # API
        self.client: pybotters.Client = client
        self.base_url = "https://api.bybit.com"

    async def get_kline(self):
        endpoint = "/v5/market/kline"
        url = f"{self.base_url}{endpoint}"
        params = {
            'category': "linear",
            'symbol': self.symbol,
            'interval' : "15", #15分足
            'limit' : "500" # 500本
        }
        result = await self.client.fetch("GET", url=url, params=params)
        text = result.text
        data = json.loads(text)
        return data

async def run_task(symbol, client:pybotters.Client):
    bot = kline(symbol, client)
    await bot.get_kline()

async def main():
    symbols = ['BTCUSDT']
    async with pybotters.Client() as client:
        await asyncio.gather(*(run_task(symbol, client) for symbol in symbols))

if __name__ == '__main__':
    asyncio.run(main())
