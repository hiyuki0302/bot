import requests
import json
import time
from datetime import datetime

class KrakenCoincheckArbitrage:
    def __init__(self):
        # API エンドポイント
        self.coincheck_url = "https://coincheck.com/api/ticker"
        self.kraken_url = "https://api.kraken.com/0/public/Ticker"
        self.usdjpy_url = "https://api.exchangerate-api.com/v4/latest/USD"
        
        # CoincheckとKrakenの対応通貨ペア
        self.currency_pairs = {
            'BTC': {'coincheck': 'btc_jpy', 'kraken': 'XBTUSD'},
            'ETH': {'coincheck': 'eth_jpy', 'kraken': 'ETHUSD'},
            'XRP': {'coincheck': 'xrp_jpy', 'kraken': 'XRPUSD'},
            'BCH': {'coincheck': 'bch_jpy', 'kraken': 'BCHUSD'},
            'XLM': {'coincheck': 'xlm_jpy', 'kraken': 'XLMUSD'},
            'BAT': {'coincheck': 'bat_jpy', 'kraken': 'BATUSD'},
            'QTUM': {'coincheck': 'qtum_jpy', 'kraken': 'QTUMUSD'},
            'DOT': {'coincheck': 'dot_jpy', 'kraken': 'DOTUSD'},
            'LINK': {'coincheck': 'link_jpy', 'kraken': 'LINKUSD'},
            'MATIC': {'coincheck': 'matic_jpy', 'kraken': 'MATICUSD'},
            'AVAX': {'coincheck': 'avax_jpy', 'kraken': 'AVAXUSD'},
            'DOGE': {'coincheck': 'doge_jpy', 'kraken': 'DOGEUSD'},
            'MANA': {'coincheck': 'mana_jpy', 'kraken': 'MANAUSD'},
            'GRT': {'coincheck': 'grt_jpy', 'kraken': 'GRTUSD'},
            'MKR': {'coincheck': 'mkr_jpy', 'kraken': 'MKRUSD'},
            'SHIB': {'coincheck': 'shib_jpy', 'kraken': 'SHIBUSD'},
            'ADA': {'coincheck': 'ada_jpy', 'kraken': 'ADAUSD'},  # もしCoincheckにADAがあれば
            'SOL': {'coincheck': 'sol_jpy', 'kraken': 'SOLUSD'},  # もしCoincheckにSOLがあれば
        }
        
        # Krakenの通貨ペア名の特殊処理
        self.kraken_pair_mapping = {
            'XBTUSD': 'BTC',
            'ETHUSD': 'ETH',
            'XRPUSD': 'XRP',
            'BCHUSD': 'BCH',
            'XLMUSD': 'XLM',
            'BATUSD': 'BAT',
            'QTUMUSD': 'QTUM',
            'DOTUSD': 'DOT',
            'LINKUSD': 'LINK',
            'MATICUSD': 'MATIC',
            'AVAXUSD': 'AVAX',
            'DOGEUSD': 'DOGE',
            'MANAUSD': 'MANA',
            'GRTUSD': 'GRT',
            'MKRUSD': 'MKR',
            'SHIBUSD': 'SHIB',
            'ADAUSD': 'ADA',
            'SOLUSD': 'SOL',
        }
        
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
        """Coincheckから特定ペアの価格を取得（USD換算）"""
        try:
            url = f"https://coincheck.com/api/ticker?pair={pair}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # JPYからUSDに換算
            bid_usd = float(data['bid']) / usdjpy_rate
            ask_usd = float(data['ask']) / usdjpy_rate
            last_usd = float(data['last']) / usdjpy_rate
            
            return {
                'bid': round(bid_usd, 6),
                'ask': round(ask_usd, 6),
                'last': round(last_usd, 6),
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
    
    def get_kraken_price(self, pair):
        """Krakenから特定ペアの価格を取得"""
        try:
            params = {'pair': pair}
            response = requests.get(self.kraken_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data and data['error']:
                print(f"Kraken APIエラー: {data['error']}")
                return {'success': False}
            
            if 'result' in data and data['result']:
                # Krakenのレスポンス形式は複雑なので注意深く処理
                result_data = data['result']
                
                # ペア名を取得（Krakenは実際のペア名が変わることがある）
                pair_key = list(result_data.keys())[0]
                ticker = result_data[pair_key]
                
                # Krakenの価格データ
                # bid = [価格, 全量, 全量の単位]
                # ask = [価格, 全量, 全量の単位]
                bid_price = float(ticker['b'][0])
                ask_price = float(ticker['a'][0])
                last_price = float(ticker['c'][0])
                
                return {
                    'bid': round(bid_price, 6),
                    'ask': round(ask_price, 6),
                    'last': round(last_price, 6),
                    'success': True
                }
        except Exception as e:
            print(f"Kraken {pair} 価格取得エラー: {e}")
            return {'success': False}
    
    def get_all_prices(self, selected_currencies=None):
        """選択された通貨の価格を両取引所から取得"""
        # 為替レート取得
        usdjpy_rate = self.get_usdjpy_rate()
        
        if selected_currencies is None:
            selected_currencies = ['BTC', 'ETH', 'XRP', 'LTC', 'BCH']  # デフォルトは主要5通貨
        
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
            
            # Krakenから価格取得
            kraken_data = self.get_kraken_price(pairs['kraken'])
            
            if cc_data['success'] and kraken_data['success']:
                results['currencies'][currency] = {
                    'coincheck': cc_data,
                    'kraken': kraken_data
                }
            elif cc_data['success']:
                print(f"⚠️  {currency}: Krakenでデータ取得失敗")
            elif kraken_data['success']:
                print(f"⚠️  {currency}: Coincheckでデータ取得失敗")
            else:
                print(f"❌ {currency}: 両取引所でデータ取得失敗")
        
        return results
    
    def calculate_arbitrage_opportunity(self, cc_data, kraken_data):
        """アービトラージ機会を計算"""
        # Coincheck → Kraken
        cc_ask = cc_data['ask']      # Coincheckで買う価格
        kraken_bid = kraken_data['bid']  # Krakenで売る価格
        diff1 = kraken_bid - cc_ask
        diff1_pct = (diff1 / cc_ask) * 100
        
        # Kraken → Coincheck
        kraken_ask = kraken_data['ask']  # Krakenで買う価格
        cc_bid = cc_data['bid']          # Coincheckで売る価格
        diff2 = cc_bid - kraken_ask
        diff2_pct = (diff2 / kraken_ask) * 100
        
        return {
            'cc_to_kraken': {'diff': diff1, 'pct': diff1_pct},
            'kraken_to_cc': {'diff': diff2, 'pct': diff2_pct}
        }
    
    def display_results(self, results, show_details=True, min_profit=0.3):
        """結果を表示"""
        print("=" * 85)
        print(f"Kraken vs Coincheck アービトラージ機会検索 - {results['timestamp']}")
        print(f"USD/JPY為替レート: {results['usdjpy_rate']:.2f}")
        print("=" * 85)
        
        if not results['currencies']:
            print("❌ データが取得できませんでした")
            return
        
        opportunities = []
        
        for currency, data in results['currencies'].items():
            cc_data = data['coincheck']
            kraken_data = data['kraken']
            
            arb = self.calculate_arbitrage_opportunity(cc_data, kraken_data)
            
            # 最大利益機会を特定
            if abs(arb['cc_to_kraken']['pct']) > abs(arb['kraken_to_cc']['pct']):
                max_opportunity = arb['cc_to_kraken']
                direction = "Coincheck→Kraken"
            else:
                max_opportunity = arb['kraken_to_cc']
                direction = "Kraken→Coincheck"
            
            opportunities.append({
                'currency': currency,
                'profit_pct': abs(max_opportunity['pct']),
                'direction': direction,
                'data': data,
                'arb': arb
            })
            
            if show_details:
                print(f"\n【{currency}】")
                print(f"  Coincheck: Bid ${cc_data['bid']:>9.6f} | Ask ${cc_data['ask']:>9.6f}")
                print(f"  Kraken:    Bid ${kraken_data['bid']:>9.6f} | Ask ${kraken_data['ask']:>9.6f}")
                print(f"  CC→Kraken: {arb['cc_to_kraken']['pct']:+7.3f}% (${arb['cc_to_kraken']['diff']:+9.6f})")
                print(f"  Kraken→CC: {arb['kraken_to_cc']['pct']:+7.3f}% (${arb['kraken_to_cc']['diff']:+9.6f})")
                
                if abs(max_opportunity['pct']) > 0.5:
                    print(f"  🚀 機会: {direction} - {abs(max_opportunity['pct']):.3f}%")
        
        # 上位の機会をランキング表示
        opportunities.sort(key=lambda x: x['profit_pct'], reverse=True)
        
        print("\n" + "=" * 60)
        print("🎯 アービトラージ機会ランキング")
        print("=" * 60)
        
        profitable_opportunities = [opp for opp in opportunities if opp['profit_pct'] > min_profit]
        
        if profitable_opportunities:
            for i, opp in enumerate(profitable_opportunities[:5], 1):
                print(f"{i}. {opp['currency']} - {opp['direction']}")
                print(f"   💰 理論利益率: {opp['profit_pct']:.3f}%")
                
                # Krakenの手数料を考慮（メイカー0.16%, テイカー0.26%）
                # Coincheckの手数料も考慮（スプレッド約0.1-0.3%）
                estimated_fees = 0.5  # 往復約0.5%の手数料
                net_profit = opp['profit_pct'] - estimated_fees
                
                if net_profit > 0:
                    print(f"   📈 手数料控除後: {net_profit:.3f}%")
                else:
                    print(f"   📉 手数料控除後: {net_profit:.3f}% (赤字)")
                print()
        else:
            print(f"現在、{min_profit}%以上の利益機会はありません")
            if opportunities:
                best = opportunities[0]
                print(f"最良の機会: {best['currency']} - {best['profit_pct']:.3f}%")
    
    def get_available_currencies(self):
        """利用可能な通貨リストを返す"""
        return list(self.currency_pairs.keys())
    
    def monitor_specific_currencies(self, currencies, interval=10, min_profit=0.5):
        """特定通貨の継続監視"""
        print(f"🔍 監視対象通貨: {', '.join(currencies)}")
        print(f"📊 最小利益率: {min_profit}%")
        print(f"⏱️  更新間隔: {interval}秒")
        print("Ctrl+C で停止")
        print("\n")
        
        try:
            while True:
                results = self.get_all_prices(currencies)
                self.display_results(results, show_details=False, min_profit=min_profit)
                print(f"\n次回更新: {interval}秒後...")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n🛑 監視を停止しました")
    
    def get_detailed_analysis(self, currency):
        """特定通貨の詳細分析"""
        if currency not in self.currency_pairs:
            print(f"❌ {currency} は対応していません")
            return
        
        print(f"\n📊 {currency} 詳細分析")
        print("=" * 50)
        
        results = self.get_all_prices([currency])
        
        if currency in results['currencies']:
            data = results['currencies'][currency]
            cc_data = data['coincheck']
            kraken_data = data['kraken']
            
            print(f"Coincheck ({currency}/JPY):")
            print(f"  Bid: ¥{cc_data['original']['bid_jpy']:,.2f}")
            print(f"  Ask: ¥{cc_data['original']['ask_jpy']:,.2f}")
            print(f"  スプレッド: ¥{cc_data['original']['ask_jpy'] - cc_data['original']['bid_jpy']:,.2f}")
            
            print(f"\nKraken ({currency}/USD):")
            print(f"  Bid: ${kraken_data['bid']:,.6f}")
            print(f"  Ask: ${kraken_data['ask']:,.6f}")
            print(f"  スプレッド: ${kraken_data['ask'] - kraken_data['bid']:,.6f}")
            
            arb = self.calculate_arbitrage_opportunity(cc_data, kraken_data)
            
            print(f"\nアービトラージ機会:")
            print(f"  Coincheck→Kraken: {arb['cc_to_kraken']['pct']:+.3f}%")
            print(f"  Kraken→Coincheck: {arb['kraken_to_cc']['pct']:+.3f}%")

# 使用例
if __name__ == "__main__":
    arbitrage = KrakenCoincheckArbitrage()
    
    print("🌊 Kraken vs Coincheck アービトラージシステム")
    print("=" * 50)
    
    print("📋 利用可能な通貨:")
    currencies = arbitrage.get_available_currencies()
    for i, currency in enumerate(currencies, 1):
        print(f"{i:2d}. {currency}")
    
    print("\n" + "="*60)
    
    # 主要通貨での検索例
    print("🔍 主要通貨でのアービトラージ機会検索...")
    major_currencies = ['BTC', 'ETH', 'XRP', 'LTC', 'BCH']
    results = arbitrage.get_all_prices(major_currencies)
    arbitrage.display_results(results)
    
    # 特定通貨の詳細分析例
    # arbitrage.get_detailed_analysis('BTC')
    
    # 継続監視の例（コメントアウトを外して使用）
    # print("\n" + "="*60)
    # arbitrage.monitor_specific_currencies(['BTC', 'ETH', 'XRP'], interval=15, min_profit=0.5)