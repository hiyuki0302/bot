#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bitget 急騰検出システム（pybotters版・簡素化）
1つ前の15分足と比較して、50%以上の価格上昇とボリューム急増を検出してDiscordに通知
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pybotters
import aiohttp


class BitgetPumpDetector:
    def __init__(self, discord_webhook_url: str, api_key: str = "", api_secret: str = "", passphrase: str = ""):
        self.discord_webhook = discord_webhook_url
        
        # Bitget API認証情報（パブリックAPIのみ使用する場合は空でOK）
        self.apis = {
            "bitget": [api_key, api_secret, passphrase]
        }
        
        # パフォーマンス設定
        self.max_concurrent = 100  # 同時リクエスト数
        self.timeout_seconds = 3   # タイムアウト時間
    
    async def get_all_usdt_symbols(self, session) -> List[str]:
        """全USDTペアのシンボル一覧を取得"""
        try:
            resp = await session.get(
                "https://api.bitget.com/api/v2/spot/public/symbols"
            )
            data = await resp.json()
            
            if data.get("code") == "00000":
                symbols = []
                for symbol_info in data.get("data", []):
                    symbol = symbol_info.get("symbol", "")
                    if symbol.endswith("USDT") and symbol != "USDT":
                        # ステータスがonlineのもののみ
                        if symbol_info.get("status") == "online":
                            symbols.append(symbol)
                return symbols
            else:
                print(f"API Error: {data.get('msg', 'Unknown error')}")
                return []
                
        except Exception as e:
            print(f"Error getting symbols: {e}")
            return []
    
    async def get_15m_candles_optimized(self, session, symbol: str) -> Optional[List[List]]:
        """最適化された15分足データ取得"""
        try:
            params = {
                "symbol": symbol,
                "granularity": "15m",
                "limit": 2
            }
            
            # タイムアウトを短縮してレスポンス向上
            timeout = aiohttp.ClientTimeout(total=5)
            resp = await session.get(
                "https://api.bitget.com/api/v2/spot/market/candles",
                params=params,
                timeout=timeout
            )
            data = await resp.json()
            
            if data.get("code") == "00000":
                return data.get("data", [])
            else:
                return None
                
        except asyncio.TimeoutError:
            print(f"Timeout for {symbol}")
            return None
        except Exception as e:
            # エラーログを簡素化
            return None
    
    async def process_all_symbols_concurrent(self, session, symbols: List[str], max_concurrent: int = 50) -> List[Dict]:
        """全シンボルを高速並列処理して急騰を検出"""
        pumps = []
        
        # セマフォでコンカレンシー制限
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(symbol):
            async with semaphore:
                return await self.analyze_single_symbol(session, symbol)
        
        print(f"Processing {len(symbols)} symbols with max {max_concurrent} concurrent requests...")
        start_time = time.time()
        
        # 全シンボルを一度に並列処理
        tasks = [analyze_with_semaphore(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を処理
        for symbol, result in zip(symbols, results):
            if isinstance(result, dict) and result:
                pumps.append(result)
            elif isinstance(result, Exception):
                print(f"Error processing {symbol}: {result}")
        
        elapsed = time.time() - start_time
        print(f"Completed {len(symbols)} symbols in {elapsed:.2f} seconds")
        
        return pumps
    
    async def analyze_single_symbol(self, session, symbol: str) -> Optional[Dict]:
        """単一シンボルの高速分析と急騰判定"""
        try:
            # 最新2本の15分足を取得
            candles = await self.get_15m_candles_optimized(session, symbol)
            if not candles or len(candles) < 2:
                return None
            
            # データ解析を高速化
            current_candle = candles[0]
            previous_candle = candles[1]
            
            current_close = float(current_candle[4])
            previous_close = float(previous_candle[4])
            current_volume = float(current_candle[6])
            previous_volume = float(previous_candle[6])
            
            # 早期リターンで無駄な計算を回避
            if previous_close <= 0 or previous_volume <= 0:
                return None
            
            price_change = (current_close - previous_close) / previous_close
            volume_change = (current_volume - previous_volume) / previous_volume
            
            # 急騰条件チェックを最初に
            if price_change >= 0.5 and volume_change >= 2.0:
                return {
                    "symbol": symbol,
                    "price_change": price_change,
                    "volume_change": volume_change,
                    "current_price": current_close,
                    "previous_price": previous_close,
                    "current_volume": current_volume,
                    "previous_volume": previous_volume,
                    "timestamp": int(current_candle[0])
                }
            
            return None
            
        except Exception:
            # エラーハンドリングを簡素化
            return None
    
    async def send_status_notification(self, session, total_symbols: int, processed_symbols: int, execution_time: float) -> None:
        """稼働状況をDiscordに通知"""
        embed = {
            "title": "📊 Bitget監視システム 稼働レポート",
            "color": 0x0099ff,  # 青色
            "fields": [
                {
                    "name": "🔍 監視対象",
                    "value": f"{total_symbols} USDTペア",
                    "inline": True
                },
                {
                    "name": "✅ 処理完了",
                    "value": f"{processed_symbols} 銘柄",
                    "inline": True
                },
                {
                    "name": "⏱️ 処理時間",
                    "value": f"{execution_time:.1f}秒",
                    "inline": True
                },
                {
                    "name": "📈 検出条件",
                    "value": "価格+50% & ボリューム+200%",
                    "inline": False
                },
                {
                    "name": "🟢 ステータス",
                    "value": "正常稼働中",
                    "inline": True
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "次回監視まで15分"
            }
        }
        
        payload = {
            "content": "ℹ️ **急騰銘柄なし** - システム正常稼働中",
            "embeds": [embed]
        }
        
        try:
            async with session.post("https://discord.com/api/webhooks/1369503632650928148/lNMN5RzSRDTIYo2X4nTbMBlv4Rzg_HYR4PQY7shMnTnAhZv-xkbdVAdbI59JAslVa8cl", json=payload) as resp:
                if resp.status == 204:
                    print("Status notification sent to Discord")
                else:
                    print(f"Status notification failed: {resp.status}")
        except Exception as e:
            print(f"Failed to send status notification: {e}")
    
    async def send_discord_notification(self, session, pumps: List[Dict]) -> None:
        """Discordに急騰通知送信"""
        if not pumps:
            return
        
        # 価格上昇率でソート（降順）
        pumps.sort(key=lambda x: x["price_change"], reverse=True)
        
        # Embed形式でリッチな通知を作成
        embeds = []
        
        # 最大10銘柄まで表示
        for pump in pumps[:10]:
            symbol = pump["symbol"]
            price_change_pct = pump["price_change"] * 100
            volume_change_pct = pump["volume_change"] * 100
            
            embed = {
                "title": f"🚀 {symbol} 急騰検出！",
                "color": 0x00ff00,  # 緑色
                "fields": [
                    {
                        "name": "📈 価格上昇率（15分）",
                        "value": f"+{price_change_pct:.1f}%",
                        "inline": True
                    },
                    {
                        "name": "📊 ボリューム増加率（15分）",
                        "value": f"+{volume_change_pct:.1f}%",
                        "inline": True
                    },
                    {
                        "name": "💰 現在価格",
                        "value": f"${pump['current_price']:.8f}",
                        "inline": True
                    },
                    {
                        "name": "📊 ボリューム比較",
                        "value": f"前: ${pump['previous_volume']:,.0f}\n今: ${pump['current_volume']:,.0f}",
                        "inline": True
                    },
                    {
                        "name": "📈 価格変動",
                        "value": f"${pump['previous_price']:.8f} → ${pump['current_price']:.8f}",
                        "inline": False
                    }
                ],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            embeds.append(embed)
        
        # Discord Webhook送信
        payload = {
            "content": f"🔥 **{len(pumps)}銘柄で急騰を検出！**（前15分足比較） 🔥",
            "embeds": embeds
        }
        
        try:
            async with session.post(self.discord_webhook, json=payload) as resp:
                if resp.status == 204:
                    print(f"Discord notification sent for {len(pumps)} pumps")
                else:
                    print(f"Discord notification failed: {resp.status}")
        except Exception as e:
            print(f"Failed to send Discord notification: {e}")
    
    async def run(self) -> None:
        """メイン実行処理"""
        print(f"[{datetime.now()}] Starting simplified 15m pump detection...")
        start_time = time.time()
        
        async with pybotters.Client(apis=self.apis) as client:
            # 全USDTペアのシンボル取得
            symbols = await self.get_all_usdt_symbols(client)
            if not symbols:
                print("Failed to get symbols")
                return
            
            print(f"Found {len(symbols)} USDT pairs")
            
            # 急騰検出（高速並列処理）
            pumps = await self.process_all_symbols_concurrent(client, symbols, max_concurrent=self.max_concurrent)
            
            execution_time = time.time() - start_time
            
            if pumps:
                print(f"🚀 Detected {len(pumps)} pumps (vs previous 15m candle)!")
                for pump in pumps:
                    print(f"  {pump['symbol']}: Price +{pump['price_change']*100:.1f}%, "
                          f"Volume +{pump['volume_change']*100:.1f}%")
                
                # 急騰通知送信
                await self.send_discord_notification(client, pumps)
            else:
                print("No significant pumps detected vs previous 15m candle")
                
                # 稼働状況通知送信（急騰なしの場合）
                processed_count = len([s for s in symbols if s])  # 処理された銘柄数
                await self.send_status_notification(client, len(symbols), processed_count, execution_time)
            
            print(f"[{datetime.now()}] Simplified pump detection completed\n")


async def main():
    # Discord Webhook URL を設定
    discord_webhook_url = "https://discord.com/api/webhooks/1398172478693707786/g8lptbshUeKILdHwAORGfR-lhV2SQoOfIPHTUhcik91r1npKFMe12alhuMUkpsOaBmyC"
    
    if not discord_webhook_url:
        print("Error: DISCORD_WEBHOOK_URL environment variable not set")
        print("Usage: export DISCORD_WEBHOOK_URL='your_webhook_url'")
        return
    
    # Bitget API認証情報（パブリックAPIのみなので空でOK）
    api_key = os.getenv("BITGET_API_KEY", "")
    api_secret = os.getenv("BITGET_API_SECRET", "")
    passphrase = os.getenv("BITGET_PASSPHRASE", "")
    
    # 検出器を初期化して実行
    detector = BitgetPumpDetector(discord_webhook_url, api_key, api_secret, passphrase)
    await detector.run()


if __name__ == "__main__":
    asyncio.run(main())