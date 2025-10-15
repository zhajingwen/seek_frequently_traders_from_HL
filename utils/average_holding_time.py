import requests
from collections import defaultdict
from datetime import datetime, timedelta


class AverageHoldingTimeAnalyzer:
    """Hyperliquid交易数据分析器（支持合约和现货）"""
    
    def __init__(self, user_address):
        """
        初始化分析器
        
        Args:
            user_address: 用户地址
        """
        self.user_address = user_address
        self.api_url = "https://api.hyperliquid.xyz/info"
        self.fills = []
        
        # 分别存储合约和现货的数据
        self.perp_holding_times = defaultdict(list)
        self.perp_positions = defaultdict(list)
        self.spot_holding_times = defaultdict(list)
        self.spot_positions = defaultdict(list)
    
    def fetch_user_fills(self):
        """获取用户的成交记录"""
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }
        body = {
            "aggregateByTime": True,
            "type": "userFills",
            "user": self.user_address
        }
        
        response = requests.post(self.api_url, json=body, headers=headers)
        response.raise_for_status()
        self.fills = response.json()
        return self.fills
    
    def _is_spot_trade(self, fill):
        """
        判断是否为现货交易
        
        现货交易的特征：
        1. coin字段包含'/'（如 'BTC/USDC'）
        2. 或者通过其他字段判断（如crossed字段为'spot'）
        """
        coin = fill.get('coin', '')
        # 如果币种名称包含'/'，则为现货
        if '/' in coin:
            return True
        # 也可以通过其他字段判断
        if fill.get('crossed') == 'spot':
            return True
        return False
    
    def calculate_average_holding_time(self):
        """
        计算每个币种的平均持仓时间（分别计算合约和现货）
        
        逻辑：
        1. 追踪每个币种的持仓队列（FIFO）
        2. 开仓时记录开仓时间和数量
        3. 平仓时计算持仓时间
        """
        # 重置数据
        self.perp_positions = defaultdict(list)
        self.perp_holding_times = defaultdict(list)
        self.spot_positions = defaultdict(list)
        self.spot_holding_times = defaultdict(list)
        
        # 按时间排序（从早到晚）
        fills_sorted = sorted(self.fills, key=lambda x: x['time'])
        
        for fill in fills_sorted:
            coin = fill['coin']
            size = float(fill['sz'])
            time = fill['time']  # 毫秒时间戳
            direction = fill['dir']
            is_spot = self._is_spot_trade(fill)
            
            # 判断是开仓还是平仓
            # 对于现货，Buy相当于开仓，Sell相当于平仓
            if is_spot:
                is_opening = direction in ['Buy']
            else:
                is_opening = 'Open' in direction
            
            if is_opening:
                self._handle_opening(coin, size, time, float(fill['px']), is_spot)
            else:
                self._handle_closing(coin, size, time, is_spot)
        
        return (self.perp_holding_times, self.perp_positions, 
                self.spot_holding_times, self.spot_positions)
    
    def _handle_opening(self, coin, size, time, price, is_spot):
        """处理开仓"""
        position_data = {
            'time': time,
            'size': size,
            'price': price
        }
        
        if is_spot:
            self.spot_positions[coin].append(position_data)
        else:
            self.perp_positions[coin].append(position_data)
    
    def _handle_closing(self, coin, size, time, is_spot):
        """处理平仓（FIFO）"""
        positions = self.spot_positions if is_spot else self.perp_positions
        holding_times = self.spot_holding_times if is_spot else self.perp_holding_times
        
        remaining_size = size
        
        while remaining_size > 0 and positions[coin]:
            position = positions[coin][0]
            
            if position['size'] <= remaining_size:
                # 完全平掉这个仓位
                holding_time_ms = time - position['time']
                holding_time_hours = holding_time_ms / (1000 * 60 * 60)
                
                holding_times[coin].append({
                    'holding_time_hours': holding_time_hours,
                    'size': position['size'],
                    'open_time': position['time'],
                    'close_time': time
                })
                
                remaining_size -= position['size']
                positions[coin].pop(0)
            else:
                # 部分平仓
                holding_time_ms = time - position['time']
                holding_time_hours = holding_time_ms / (1000 * 60 * 60)
                
                holding_times[coin].append({
                    'holding_time_hours': holding_time_hours,
                    'size': remaining_size,
                    'open_time': position['time'],
                    'close_time': time
                })
                
                position['size'] -= remaining_size
                remaining_size = 0
    
    @staticmethod
    def format_time(hours):
        """格式化时间显示"""
        if hours < 1:
            return f"{hours * 60:.1f} 分钟"
        elif hours < 24:
            return f"{hours:.1f} 小时"
        else:
            days = hours / 24
            return f"{days:.1f} 天"
    
    def get_coin_statistics(self, coin, is_spot=False):
        """
        获取指定币种的统计数据
        
        Args:
            coin: 币种名称
            is_spot: 是否为现货
            
        Returns:
            dict: 包含各项统计指标的字典
        """
        holding_times = self.spot_holding_times if is_spot else self.perp_holding_times
        times = holding_times.get(coin, [])
        
        if not times:
            return None
        
        simple_avg = sum(t['holding_time_hours'] for t in times) / len(times)
        total_size = sum(t['size'] for t in times)
        weighted_avg = sum(t['holding_time_hours'] * t['size'] for t in times) / total_size
        min_time = min(t['holding_time_hours'] for t in times)
        max_time = max(t['holding_time_hours'] for t in times)
        
        return {
            'coin': coin,
            'close_count': len(times),
            'simple_avg': simple_avg,
            'weighted_avg': weighted_avg,
            'min_time': min_time,
            'max_time': max_time,
            'total_size': total_size
        }
    
    def get_overall_statistics(self, is_spot=None):
        """
        获取总体统计数据
        
        Args:
            is_spot: None=全部, True=仅现货, False=仅合约
        """
        if is_spot is None:
            # 合并现货和合约的数据
            holding_times_list = [self.perp_holding_times, self.spot_holding_times]
        elif is_spot:
            holding_times_list = [self.spot_holding_times]
        else:
            holding_times_list = [self.perp_holding_times]
        
        all_holding_times = []
        all_weighted_times = []
        
        for holding_times in holding_times_list:
            for coin, times in holding_times.items():
                all_holding_times.extend([t['holding_time_hours'] for t in times])
                all_weighted_times.extend([t['holding_time_hours'] * t['size'] for t in times])
        
        if not all_holding_times:
            return None
        
        total_size = sum(all_weighted_times) / sum(all_holding_times) if all_holding_times else 0
        # 重新计算总大小
        total_size = 0
        for holding_times in holding_times_list:
            for coin_times in holding_times.values():
                total_size += sum(t['size'] for t in coin_times)
        
        return {
            'total_close_count': len(all_holding_times),
            'overall_simple_avg': sum(all_holding_times) / len(all_holding_times),
            'overall_weighted_avg': sum(all_weighted_times) / total_size
        }
    
    def get_open_positions(self, is_spot=False):
        """
        获取未平仓位
        
        Args:
            is_spot: 是否为现货
        """
        positions = self.spot_positions if is_spot else self.perp_positions
        return {coin: pos for coin, pos in positions.items() if pos}
    
    def print_type_statistics(self, trade_type="合约"):
        """
        打印指定类型的统计信息
        
        Args:
            trade_type: "合约" 或 "现货"
        """
        is_spot = (trade_type == "现货")
        holding_times = self.spot_holding_times if is_spot else self.perp_holding_times
        
        print("\n" + "=" * 80)
        print(f"【{trade_type}】持仓时间统计报告")
        print("=" * 80)
        
        # 打印未平仓位
        open_positions = self.get_open_positions(is_spot)
        if open_positions:
            print("\n" + "=" * 80)
            print(f"【当前{trade_type}未平仓位】")
            print("-" * 80)
            for coin, pos_list in open_positions.items():
                total_open = sum(p['size'] for p in pos_list)
                print(f"  {coin}: {total_open:.4f} (共 {len(pos_list)} 个开仓记录)")

        # 已平仓
        if not holding_times:
            print(f"\n未找到已平仓的{trade_type}交易记录")
            return
        
        # 打印每个币种的统计
        for coin in holding_times.keys():
            stats = self.get_coin_statistics(coin, is_spot)
            
            if stats is None:
                continue
            
            print(f"\n【{coin}】")
            print("-" * 80)
            print(f"  平仓次数: {stats['close_count']}")
            print(f"  简单平均持仓时间: {self.format_time(stats['simple_avg'])}")
            print(f"  加权平均持仓时间: {self.format_time(stats['weighted_avg'])} (按仓位大小加权)")
            print(f"  最短持仓时间: {self.format_time(stats['min_time'])}")
            print(f"  最长持仓时间: {self.format_time(stats['max_time'])}")
            print(f"  总平仓量: {stats['total_size']:.4f}")
        
        # 打印总体统计
        overall = self.get_overall_statistics(is_spot)
        if overall:
            print("\n" + "=" * 80)
            print(f"【{trade_type}总体统计】")
            print("-" * 80)
            print(f"  总平仓次数: {overall['total_close_count']}")
            print(f"  总体简单平均持仓时间: {self.format_time(overall['overall_simple_avg'])}")
            print(f"  总体加权平均持仓时间: {self.format_time(overall['overall_weighted_avg'])}")
    
    def print_statistics(self):
        """打印完整的统计信息（合约+现货）"""
        print("=" * 80)
        print("Hyperliquid 交易分析报告")
        print("=" * 80)
        
        # 打印合约统计
        self.print_type_statistics("合约")
        
        # 打印现货统计
        self.print_type_statistics("现货")
        
        # 打印综合统计
        perp_overall = self.get_overall_statistics(is_spot=False)
        spot_overall = self.get_overall_statistics(is_spot=True)
        all_overall = self.get_overall_statistics(is_spot=None)
        
        if perp_overall or spot_overall:
            print("\n" + "=" * 80)
            print("【综合对比】")
            print("=" * 80)
            
            if perp_overall:
                print(f"\n合约交易:")
                print(f"  总平仓次数: {perp_overall['total_close_count']}")
                print(f"  简单平均持仓时间: {self.format_time(perp_overall['overall_simple_avg'])}")
                print(f"  加权平均持仓时间: {self.format_time(perp_overall['overall_weighted_avg'])}")
            
            if spot_overall:
                print(f"\n现货交易:")
                print(f"  总平仓次数: {spot_overall['total_close_count']}")
                print(f"  简单平均持仓时间: {self.format_time(spot_overall['overall_simple_avg'])}")
                print(f"  加权平均持仓时间: {self.format_time(spot_overall['overall_weighted_avg'])}")
            
            if all_overall and perp_overall and spot_overall:
                print(f"\n所有交易（合约+现货）:")
                print(f"  总平仓次数: {all_overall['total_close_count']}")
                print(f"  简单平均持仓时间: {self.format_time(all_overall['overall_simple_avg'])}")
                print(f"  加权平均持仓时间: {self.format_time(all_overall['overall_weighted_avg'])}")
 
    def analyze(self):
        """执行完整的分析流程"""
        print(f"正在获取用户 {self.user_address} 的交易记录...\n")
        
        try:
            # 获取数据
            fills = self.fetch_user_fills()
            
            if not fills:
                print("未找到交易记录")
                return
            
            print(f"成功获取 {len(fills)} 条交易记录\n")
            
            # 统计合约和现货交易数量
            perp_count = sum(1 for f in fills if not self._is_spot_trade(f))
            spot_count = sum(1 for f in fills if self._is_spot_trade(f))
            print(f"其中: 合约交易 {perp_count} 条, 现货交易 {spot_count} 条\n")
            
            # 计算持仓时间
            self.calculate_average_holding_time()
            
            # 获取总体统计数据
            overall = self.get_overall_statistics()
            overall_simple_avg = overall['overall_simple_avg']
            if overall_simple_avg > 1:
                print(f"总体简单平均持仓时间: {overall_simple_avg} 小时 {self.user_address}")
                return
            # 打印统计信息
            self.print_statistics()
            return self.user_address
            
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
        except Exception as e:
            print(f"发生错误: {e}")
            import traceback
            traceback.print_exc()


def main():
    # 用户地址
    # user_address = "0x5c9c9ab381c841530464ef9ee402568f84c3b676"
    user_address = "0xf709deb9ca069e53a31a408fde397a87d025a352"
    
    # 创建分析器并执行分析
    analyzer = AverageHoldingTimeAnalyzer(user_address)
    analyzer.analyze()


if __name__ == "__main__":
    main()