from blockfrost import BlockFrostApi, ApiError, ApiUrls
import json

api = BlockFrostApi(
    project_id='mainnetBfAqcyng5W9OWn6PFkiECjYaxX7GJ7Ty',  # or export environment variable BLOCKFROST_PROJECT_ID
    # optional: pass base_url or export BLOCKFROST_API_URL to use testnet, defaults to ApiUrls.mainnet.value
    base_url=ApiUrls.mainnet.value,
)
try:
    health = api.health()
    print(health)   # prints object:    HealthResponse(is_healthy=True)

except ApiError as e:
    print(e)

class CardanoDataFetcher:
    def __init__(self, project_id):
        self.api = BlockFrostApi(
            project_id=project_id,
            base_url=ApiUrls.mainnet.value
        )
    
    def get_transaction_details(self, tx_hash):
        """特定のトランザクションの詳細を取得"""
        try:
            # 基本トランザクション情報
            tx = self.api.transaction(tx_hash)
            
            # UTXO情報
            utxos = self.api.transaction_utxos(tx_hash)
            
            # メタデータ
            try:
                metadata = self.api.transaction_metadata(tx_hash)
            except ApiError:
                metadata = []
            
            return {
                'transaction': tx,
                'inputs': utxos.inputs,
                'outputs': utxos.outputs,
                'metadata': metadata,
                'block_time': tx.block_time
            }
        except ApiError as e:
            print(f"取引詳細取得エラー {tx_hash}: {e}")
            return None
    
    def get_address_transactions(self, address, count=100, page=1):
        """特定アドレスの取引履歴を取得"""
        try:
            transactions = self.api.address_transactions(
                address=address,
                count=count,
                page=page,
                order='desc'
            )
            return transactions
        except ApiError as e:
            print(f"アドレス取引履歴取得エラー {address}: {e}")
            return []

class DEXTransactionAnalyzer:
    def __init__(self, data_fetcher):
        self.fetcher = data_fetcher
        
        # 主要DEXコントラクトアドレス
        self.dex_contracts = {
            'minswap_order': 'addr1w9qzpelu9hn45pefc0xr4ac4kdxeswq7pndul2vuj59u8tqaxdznu',
            'minswap_pool': 'addr1wxn9efv2f6w82hagxqtn62ju4m293tqvw0uhmdl64ch8uwc5rd65d',
            'sundaeswap': 'addr1w9xu5tge2s0l8zz5gy6m4fnp6vqlw3qsklcyfqpqhv67hgqv3rlv4',
            'wingRiders': 'addr1w8qmxkacjdffxah0l3qg8hq2pmvs58q8lcy42zy9kda2ylc6dy5r4'
        }
        
    def is_dex_transaction(self, tx_details):
        """DEX取引かどうかを判定"""
        if not tx_details:
            return False
            
        # コントラクトアドレスをチェック
        for input_utxo in tx_details['inputs']:
            if input_utxo.address in self.dex_contracts.values():
                return True
                
        for output_utxo in tx_details['outputs']:
            if output_utxo.address in self.dex_contracts.values():
                return True
                
        # メタデータからDEX取引を識別
        for metadata in tx_details['metadata']:
            if self._check_dex_metadata(metadata):
                return True
                
        return False
    
    def _check_dex_metadata(self, metadata):
        """メタデータからDEX関連情報を確認"""
        dex_labels = ['674', '1967']  # 一般的なDEXメタデータラベル
        
        if str(metadata.label) in dex_labels:
            return True
            
        # JSON文字列にDEX関連キーワードが含まれているかチェック
        metadata_str = json.dumps(metadata.json_metadata).lower()
        dex_keywords = ['swap', 'minswap', 'sundaeswap', 'dex', 'pool']
        
        return any(keyword in metadata_str for keyword in dex_keywords)
    
    def parse_swap_data(self, tx_details):
        """スワップデータを解析"""
        swap_data = {
            'tx_hash': tx_details['transaction'].hash,
            'timestamp': tx_details['block_time'],
            'fee': int(tx_details['transaction'].fees),
            'token_in': None,
            'token_out': None,
            'amount_in': 0,
            'amount_out': 0,
            'dex_name': self._identify_dex(tx_details)
        }
        
        # 入力と出力を解析してスワップ詳細を特定
        user_inputs = []
        user_outputs = []
        
        for input_utxo in tx_details['inputs']:
            if input_utxo.address not in self.dex_contracts.values():
                user_inputs.extend(input_utxo.amount)
                
        for output_utxo in tx_details['outputs']:
            if output_utxo.address not in self.dex_contracts.values():
                user_outputs.extend(output_utxo.amount)
        
        # トークンの変化を計算
        swap_data.update(self._calculate_token_changes(user_inputs, user_outputs))
        
        return swap_data
    
    def _identify_dex(self, tx_details):
        """使用されたDEXを特定"""
        for name, address in self.dex_contracts.items():
            for input_utxo in tx_details['inputs']:
                if input_utxo.address == address:
                    return name.split('_')[0]  # 'minswap_order' -> 'minswap'
            for output_utxo in tx_details['outputs']:
                if output_utxo.address == address:
                    return name.split('_')[0]
        return 'unknown'
    
    def _calculate_token_changes(self, inputs, outputs):
        """入力と出力の差分から実際のスワップを計算"""
        input_tokens = {}
        output_tokens = {}
        
        # 入力トークンの集計
        for amount in inputs:
            unit = amount.unit
            quantity = int(amount.quantity)
            input_tokens[unit] = input_tokens.get(unit, 0) + quantity
            
        # 出力トークンの集計
        for amount in outputs:
            unit = amount.unit
            quantity = int(amount.quantity)
            output_tokens[unit] = output_tokens.get(unit, 0) + quantity
        
        # 変化を計算
        changes = {}
        all_units = set(input_tokens.keys()) | set(output_tokens.keys())
        
        for unit in all_units:
            input_qty = input_tokens.get(unit, 0)
            output_qty = output_tokens.get(unit, 0)
            changes[unit] = output_qty - input_qty
        
        # 送信トークン（減少）と受信トークン（増加）を特定
        token_in = None
        token_out = None
        amount_in = 0
        amount_out = 0
        
        for unit, change in changes.items():
            if change < 0:  # 減少 = 送信
                token_in = unit
                amount_in = abs(change)
            elif change > 0:  # 増加 = 受信
                token_out = unit
                amount_out = change
        
        return {
            'token_in': token_in,
            'token_out': token_out,
            'amount_in': amount_in,
            'amount_out': amount_out
        }

import pandas as pd
from datetime import datetime, timedelta
import time

class DEXDataCollector:
    def __init__(self, project_id):
        self.fetcher = CardanoDataFetcher(project_id)
        self.analyzer = DEXTransactionAnalyzer(self.fetcher)
        self.collected_data = []
    
    def collect_dex_transactions_from_address(self, address, pages=10):
        """特定アドレスからDEX取引を収集"""
        dex_transactions = []
        
        for page in range(1, pages + 1):
            print(f"ページ {page} を処理中...")
            
            transactions = self.fetcher.get_address_transactions(
                address, count=100, page=page
            )
            
            if not transactions:
                break
                
            for tx in transactions:
                # レート制限対策
                time.sleep(0.1)
                
                tx_details = self.fetcher.get_transaction_details(tx.tx_hash)
                
                if self.analyzer.is_dex_transaction(tx_details):
                    swap_data = self.analyzer.parse_swap_data(tx_details)
                    dex_transactions.append(swap_data)
                    print(f"DEX取引発見: {tx.tx_hash}")
        
        return dex_transactions
    
    def collect_recent_dex_data(self, contract_addresses, hours_back=24):
        """最近のDEX取引データを収集"""
        all_transactions = []
        
        for name, address in contract_addresses.items():
            print(f"{name} の取引を収集中...")
            
            transactions = self.collect_dex_transactions_from_address(
                address, pages=5
            )
            
            # 指定時間以内の取引のみフィルタ
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            recent_transactions = [
                tx for tx in transactions 
                if datetime.fromtimestamp(tx['timestamp']) > cutoff_time
            ]
            
            all_transactions.extend(recent_transactions)
            
            # レート制限対策
            time.sleep(1)
        
        return all_transactions
    
    def save_to_csv(self, transactions, filename=None):
        """取引データをCSVに保存"""
        if not filename:
            filename = f"cardano_dex_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        df = pd.DataFrame(transactions)
        df.to_csv(filename, index=False)
        print(f"データを {filename} に保存しました")
        
        return df
    
    def get_volume_statistics(self, transactions):
        """取引量統計を取得"""
        df = pd.DataFrame(transactions)
        
        if df.empty:
            return {}
        
        stats = {
            'total_transactions': len(df),
            'unique_dexes': df['dex_name'].nunique(),
            'total_ada_volume': df[df['token_in'] == 'lovelace']['amount_in'].sum() / 1_000_000,
            'average_fee': df['fee'].mean() / 1_000_000,
            'transactions_by_dex': df['dex_name'].value_counts().to_dict()
        }
        
        return stats

def main():
    # API接続
    PROJECT_ID = "mainnetBfAqcyng5W9OWn6PFkiECjYaxX7GJ7Ty"
    collector = DEXDataCollector(PROJECT_ID)
    
    # DEXコントラクトアドレス
    dex_contracts = collector.analyzer.dex_contracts
    
    # 最近24時間のDEX取引を収集
    print("DEX取引データ収集開始...")
    transactions = collector.collect_recent_dex_data(dex_contracts, hours_back=24)
    
    print(f"収集された取引数: {len(transactions)}")
    
    # 統計情報を表示
    stats = collector.get_volume_statistics(transactions)
    print("\n=== 取引統計 ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # CSVに保存
    df = collector.save_to_csv(transactions)
    
    # データの表示
    print("\n=== 最近の取引サンプル ===")
    print(df.head())

if __name__ == "__main__":
    main()