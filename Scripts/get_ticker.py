import requests
import json
import time
from datetime import datetime

class MultiCurrencyArbitrage:
    def __init__(self):
        # API エンドポイント
        self.coincheck_url = "https://coincheck.com/api/ticker"
        self.okx_url = "https://www.okx.com/api/v5/market/ticker"
        self.usdjpy_url = "https://api.exchangerate-api.com/v4/latest/USD"
        
        # Coincheck取扱銘柄とOKXでの対応ペア
        self.currency_pairs = {
            'BTC': {'coincheck': 'btc_jpy', 'okx': 'BTC-USDT'},
            'ETH': {'coincheck': 'eth_jpy', 'okx': 'ETH-USDT'},
            'XRP': {'coincheck': 'xrp_jpy', 'okx': 'XRP-USDT'},
            'LTC': {'coincheck': 'ltc_jpy', 'okx': 'LTC-USDT'},
            'BCH': {'coincheck': 'bch_jpy', 'okx': 'BCH-USDT'},
            'XLM': {'coincheck': 'xlm_jpy', 'okx': 'XLM-USDT'},
            'BAT': {'coincheck': 'bat_jpy', 'okx': 'BAT-USDT'},
            'QTUM': {'coincheck': 'qtum_jpy', 'okx': 'QTUM-USDT'},
            'IOST': {'coincheck': 'iost_jpy', 'okx': 'IOST-USDT'},
            'ENJ': {'coincheck': 'enj_jpy', 'okx': 'ENJ-USDT'},
            'SAND': {'coincheck': 'sand_jpy', 'okx': 'SAND-USDT'},
            'DOT': {'coincheck': 'dot_jpy', 'okx': 'DOT-USDT'},
            'CHZ': {'coincheck': 'chz_jpy', 'okx': 'CHZ-USDT'},
            'LINK': {'coincheck': 'link_jpy', 'okx': 'LINK-USDT'},
            'MKR': {'coincheck': 'mkr_jpy', 'okx': 'MKR-USDT'},
            'MATIC': {'coincheck': 'matic_jpy', 'okx': 'MATIC-USDT'},
            'APE': {'coincheck': 'ape_jpy', 'okx': 'APE-USDT'},
            'AXS': {'coincheck': 'axs_jpy', 'okx': 'AXS-USDT'},
            'IMX': {'coincheck': 'imx_jpy', 'okx': 'IMX-USDT'},
            'SHIB': {'coincheck': 'shib_jpy', 'okx': 'SHIB-USDT'},
            'AVAX': {'coincheck': 'avax_jpy', 'okx': 'AVAX-USDT'},
            'DOGE': {'coincheck': 'doge_jpy', 'okx': 'DOGE-USDT'},
            'MANA': {'coincheck': 'mana_jpy', 'okx': 'MANA-USDT'},
            'GRT': {'coincheck': 'grt_jpy', 'okx': 'GRT-USDT'},
            'WBTC': {'coincheck': 'wbtc_jpy', 'okx': 'WBTC-USDT'},
            'DAI': {'coincheck': 'dai_jpy', 'okx': 'DAI-USDT'},
        }
        
        # Coincheckのみ取扱（OKXにない銘柄）
        self.coincheck_only = ['ETC', 'LSK', 'XEM', 'MONA', 'XYM', 'FNCT', 'BRIL', 'BC', 'MASK', 'PEPE']
        
    def get_usdjpy_rate(self):
        """USD/JPY為替レートを取得"""
        try:
            response = requests.get(self.usdjpy_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data['rates']['JPY'])
        except Exception as e:
            print(f"為替レート取得エラー: {e}")
            return 150.0  # フォールバック
    
    def get_coincheck_price(self, pair, usdjpy_rate):
        """Coincheckから特定ペアの価格を取得"""
        try:
            url = f"https://coincheck.com/api/ticker?pair={pair}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # JPYからUSDTに換算
            bid_usdt = float(data['bid']) / usdjpy_rate
            ask_usdt = float(data['ask']) / usdjpy_rate
            last_usdt = float(data['last']) / usdjpy_rate
            
            return {
                'bid': round(bid_usdt, 6),
                'ask': round(ask_usdt, 6),
                'last': round(last_usdt, 6),
                'original': {
                    'bid_jpy': float(data['bid']),
                    'ask_jpy': float(data['ask']),
                    'last_jpy': float(data['last'])
                },
                'success': True
            }
        except Exception as e:
            print(f"Coincheck {pair} 価格取得エラー: {e}")
            return {'success': False}
    
    def get_okx_price(self, pair):
        """OKXから特定ペアの価格を取得"""
        try:
            params = {'instId': pair}
            response = requests.get(self.okx_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] == '0' and data['data']:
                ticker = data['data'][0]
                return {
                    'bid': round(float(ticker['bidPx']), 6),
                    'ask': round(float(ticker['askPx']), 6),
                    'last': round(float(ticker['last']), 6),
                    'success': True
                }
        except Exception as e:
            print(f"OKX {pair} 価格取得エラー: {e}")
            return {'success': False}
    
    def get_all_prices(self, selected_currencies=None):
        """選択された通貨の価格を両取引所から取得"""
        # 為替レート取得
        usdjpy_rate = self.get_usdjpy_rate()
        
        if selected_currencies is None:
            selected_currencies = list(self.currency_pairs.keys())[:5]  # デフォルトは主要5通貨
        
        results = {
            'usdjpy_rate': usdjpy_rate,
            'currencies': {},
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        for currency in selected_currencies:
            if currency not in self.currency_pairs:
                print(f"警告: {currency} は対応していません")
                continue
                
            pairs = self.currency_pairs[currency]
            
            # Coincheckから価格取得
            cc_data = self.get_coincheck_price(pairs['coincheck'], usdjpy_rate)
            
            # OKXから価格取得
            okx_data = self.get_okx_price(pairs['okx'])
            
            if cc_data['success'] and okx_data['success']:
                results['currencies'][currency] = {
                    'coincheck': cc_data,
                    'okx': okx_data
                }
        
        return results
    
    def calculate_arbitrage_opportunity(self, cc_data, okx_data):
        """アービトラージ機会を計算"""
        # Coincheck → OKX
        cc_ask = cc_data['ask']  # Coincheckで買う価格
        okx_bid = okx_data['bid']  # OKXで売る価格
        diff1 = okx_bid - cc_ask
        diff1_pct = (diff1 / cc_ask) * 100
        
        # OKX → Coincheck
        okx_ask = okx_data['ask']  # OKXで買う価格
        cc_bid = cc_data['bid']   # Coincheckで売る価格
        diff2 = cc_bid - okx_ask
        diff2_pct = (diff2 / okx_ask) * 100
        
        return {
            'cc_to_okx': {'diff': diff1, 'pct': diff1_pct},
            'okx_to_cc': {'diff': diff2, 'pct': diff2_pct}
        }
    
    def display_results(self, results, show_details=True):
        """結果を表示"""
        print("=" * 80)
        print(f"アービトラージ機会検索 - {results['timestamp']}")
        print(f"USD/JPY為替レート: {results['usdjpy_rate']:.2f}")
        print("=" * 80)
        
        opportunities = []
        
        for currency, data in results['currencies'].items():
            cc_data = data['coincheck']
            okx_data = data['okx']
            
            arb = self.calculate_arbitrage_opportunity(cc_data, okx_data)
            
            # 最大利益機会を特定
            if abs(arb['cc_to_okx']['pct']) > abs(arb['okx_to_cc']['pct']):
                max_opportunity = arb['cc_to_okx']
                direction = "Coincheck→OKX"
            else:
                max_opportunity = arb['okx_to_cc']
                direction = "OKX→Coincheck"
            
            opportunities.append({
                'currency': currency,
                'profit_pct': abs(max_opportunity['pct']),
                'direction': direction,
                'data': data,
                'arb': arb
            })
            
            if show_details:
                print(f"\n【{currency}】")
                print(f"  Coincheck: Bid ${cc_data['bid']:.6f} | Ask ${cc_data['ask']:.6f}")
                print(f"  OKX:       Bid ${okx_data['bid']:.6f} | Ask ${okx_data['ask']:.6f}")
                print(f"  CC→OKX: {arb['cc_to_okx']['pct']:+.3f}% (${arb['cc_to_okx']['diff']:+.6f})")
                print(f"  OKX→CC: {arb['okx_to_cc']['pct']:+.3f}% (${arb['okx_to_cc']['diff']:+.6f})")
                
                if abs(max_opportunity['pct']) > 0.5:  # 0.5%以上の機会
                    print(f"  🚀 機会: {direction} - {abs(max_opportunity['pct']):.3f}%")
        
        # 上位の機会をランキング表示
        opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
        
        print("\n" + "=" * 50)
        print("🎯 アービトラージ機会ランキング TOP5")
        print("=" * 50)
        
        for i, opp in enumerate(opportunities[:5], 1):
            if opp['profit_pct'] > 0.3:  # 0.3%以上の機会のみ表示
                print(f"{i}. {opp['currency']} - {opp['direction']}")
                print(f"   利益率: {opp['profit_pct']:.3f}%")
                print(f"   手数料控除後概算: {opp['profit_pct'] - 0.3:.3f}%")
                print()
    
    def get_available_currencies(self):
        """利用可能な通貨リストを返す"""
        return list(self.currency_pairs.keys())
    
    def monitor_specific_currencies(self, currencies, interval=5):
        """特定通貨の継続監視"""
        print(f"監視対象通貨: {', '.join(currencies)}")
        print("Ctrl+C で停止")
        
        try:
            while True:
                results = self.get_all_prices(currencies)
                self.display_results(results, show_details=False)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n監視を停止しました")

# 使用例
if __name__ == "__main__":
    arbitrage = MultiCurrencyArbitrage()
    
    print("🔍 利用可能な通貨:")
    currencies = arbitrage.get_available_currencies()
    for i, currency in enumerate(currencies, 1):
        print(f"{i:2d}. {currency}")
    
    print("\n" + "="*50)
    print("アービトラージ機会検索を開始します...")
    
    # 主要通貨での検索例
    major_currencies = ['BTC', 'ETH', 'XRP', 'LTC', 'ADA']
    results = arbitrage.get_all_prices(major_currencies)
    arbitrage.display_results(results)
    
    # 継続監視を開始（コメントアウトを外して使用）
    # arbitrage.monitor_specific_currencies(['BTC', 'ETH', 'XRP'], interval=10)