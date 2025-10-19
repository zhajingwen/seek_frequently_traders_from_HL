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
        
        # 平仓记录（用于时间筛选）
        self.all_closes = []  # 所有平仓记录，包含时间戳
    
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
        if '/' in coin:
            return True
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
        self.all_closes = []
        
        # 按时间排序（从早到晚）
        fills_sorted = sorted(self.fills, key=lambda x: x['time'])
        
        for fill in fills_sorted:
            coin = fill['coin']
            size = float(fill['sz'])
            time = fill['time']  # 毫秒时间戳
            direction = fill['dir']
            is_spot = self._is_spot_trade(fill)
            
            # 判断是开仓还是平仓
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
                
                close_record = {
                    'holding_time_hours': holding_time_hours,
                    'size': position['size'],
                    'open_time': position['time'],
                    'close_time': time,
                    'coin': coin,
                    'is_spot': is_spot
                }
                
                holding_times[coin].append(close_record)
                self.all_closes.append(close_record)  # 记录所有平仓
                
                remaining_size -= position['size']
                positions[coin].pop(0)
            else:
                # 部分平仓
                holding_time_ms = time - position['time']
                holding_time_hours = holding_time_ms / (1000 * 60 * 60)
                
                close_record = {
                    'holding_time_hours': holding_time_hours,
                    'size': remaining_size,
                    'open_time': position['time'],
                    'close_time': time,
                    'coin': coin,
                    'is_spot': is_spot
                }
                
                holding_times[coin].append(close_record)
                self.all_closes.append(close_record)  # 记录所有平仓
                
                position['size'] -= remaining_size
                remaining_size = 0
    
    def get_close_frequency_stats(self):
        """
        获取平仓频率统计
        
        Returns:
            dict: 包含各项频率统计的字典
        """
        if not self.all_closes:
            return None
        
        # 获取当前时间（毫秒）
        now_ms = datetime.now().timestamp() * 1000
        one_day_ago_ms = now_ms - (24 * 60 * 60 * 1000)
        
        # 统计最近1天的平仓数
        recent_closes = [c for c in self.all_closes if c['close_time'] >= one_day_ago_ms]
        recent_close_count = len(recent_closes)
        
        # 统计总交易天数
        if self.all_closes:
            close_times = [c['close_time'] for c in self.all_closes]
            first_close = min(close_times)
            last_close = max(close_times)
            total_days = (last_close - first_close) / (1000 * 60 * 60 * 24)
            
            # 至少算1天
            if total_days < 1:
                total_days = 1
            
            # 计算平均每天平仓数
            avg_daily_close_count = len(self.all_closes) / total_days
        else:
            total_days = 0
            avg_daily_close_count = 0
        
        return {
            'recent_24h_close_count': recent_close_count,
            'avg_daily_close_count': avg_daily_close_count,
            'total_close_count': len(self.all_closes),
            'total_days': total_days,
            'first_close_time': datetime.fromtimestamp(first_close / 1000) if self.all_closes else None,
            'last_close_time': datetime.fromtimestamp(last_close / 1000) if self.all_closes else None
        }
    
    def meets_criteria(self, min_recent_closes=24, min_avg_daily_closes=24, max_avg_holding_hours=1):
        """
        检查地址是否满足筛选条件
        
        Args:
            min_recent_closes: 最近24小时最小平仓数
            min_avg_daily_closes: 平均每天最小平仓数
            max_avg_holding_hours: 最大平均持仓时间（小时）
            
        Returns:
            tuple: (是否满足条件, 统计数据字典)
        """
        freq_stats = self.get_close_frequency_stats()
        
        if not freq_stats:
            return False, None
        
        # 获取总体平均持仓时间
        overall = self.get_overall_statistics()
        if overall:
            avg_holding_hours = overall['overall_simple_avg']
        else:
            avg_holding_hours = 0
        
        # 三个筛选条件
        meets_recent = freq_stats['recent_24h_close_count'] >= min_recent_closes
        meets_avg = freq_stats['avg_daily_close_count'] >= min_avg_daily_closes
        meets_holding_time = avg_holding_hours <= max_avg_holding_hours
        
        freq_stats['avg_holding_hours'] = avg_holding_hours
        freq_stats['meets_recent_criteria'] = meets_recent
        freq_stats['meets_avg_criteria'] = meets_avg
        freq_stats['meets_holding_time_criteria'] = meets_holding_time
        freq_stats['meets_all_criteria'] = meets_recent and meets_avg and meets_holding_time
        
        return meets_recent and meets_avg and meets_holding_time, freq_stats
    
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
        
        total_size = 0
        for holding_times in holding_times_list:
            for coin_times in holding_times.values():
                total_size += sum(t['size'] for t in coin_times)
        
        return {
            'total_close_count': len(all_holding_times),
            'overall_simple_avg': sum(all_holding_times) / len(all_holding_times),
            'overall_weighted_avg': sum(all_weighted_times) / total_size if total_size > 0 else 0
        }
    
    def get_open_positions(self, is_spot=False):
        """
        获取未平仓位
        
        Args:
            is_spot: 是否为现货
        """
        positions = self.spot_positions if is_spot else self.perp_positions
        return {coin: pos for coin, pos in positions.items() if pos}
    
    def print_frequency_stats(self, freq_stats):
        """打印频率统计信息"""
        print("\n" + "=" * 80)
        print("【平仓频率统计】")
        print("=" * 80)
        print(f"  最近24小时平仓数: {freq_stats['recent_24h_close_count']}")
        print(f"  总平仓数: {freq_stats['total_close_count']}")
        print(f"  交易总天数: {freq_stats['total_days']:.2f} 天")
        print(f"  平均每天平仓数: {freq_stats['avg_daily_close_count']:.2f}")
        
        if freq_stats.get('first_close_time'):
            print(f"  首次平仓时间: {freq_stats['first_close_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        if freq_stats.get('last_close_time'):
            print(f"  最后平仓时间: {freq_stats['last_close_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n【筛选条件检查】")
        print(f"  ✓ 最近24小时平仓数 >= 24: {'通过' if freq_stats['meets_recent_criteria'] else '未通过'}")
        print(f"  ✓ 平均每天平仓数 >= 24: {'通过' if freq_stats['meets_avg_criteria'] else '未通过'}")
        print(f"\n  综合结果: {'✓ 满足所有条件' if freq_stats['meets_all_criteria'] else '✗ 不满足条件'}")
    
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
        print(f"地址: {self.user_address}")
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
 
    def analyze(self, show_full_stats=True, min_recent_closes=24, min_avg_daily_closes=24):
        """
        执行完整的分析流程
        
        Args:
            show_full_stats: 是否显示完整统计信息
            min_recent_closes: 最近24小时最小平仓数
            min_avg_daily_closes: 平均每天最小平仓数
            
        Returns:
            tuple: (是否满足条件, 用户地址, 频率统计)
        """
        print(f"正在获取用户 {self.user_address} 的交易记录...\n")
        
        try:
            # 获取数据
            fills = self.fetch_user_fills()
            
            if not fills:
                print("未找到交易记录")
                return False, self.user_address, None
            
            print(f"成功获取 {len(fills)} 条交易记录\n")
            
            # 统计合约和现货交易数量
            perp_count = sum(1 for f in fills if not self._is_spot_trade(f))
            spot_count = sum(1 for f in fills if self._is_spot_trade(f))
            print(f"其中: 合约交易 {perp_count} 条, 现货交易 {spot_count} 条\n")
            
            # 计算持仓时间
            self.calculate_average_holding_time()
            
            # 检查是否满足条件
            meets_criteria, freq_stats = self.meets_criteria(min_recent_closes, min_avg_daily_closes)
            
            # 打印频率统计
            if freq_stats:
                self.print_frequency_stats(freq_stats)
            
            # 如果满足条件且需要显示完整统计，则打印详细信息
            if meets_criteria and show_full_stats:
                self.print_statistics()
            
            return meets_criteria, self.user_address, freq_stats
            
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return False, self.user_address, None
        except Exception as e:
            print(f"发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False, self.user_address, None


def analyze_multiple_addresses(addresses, min_recent_closes=24, min_avg_daily_closes=24):
    """
    批量分析多个地址
    
    Args:
        addresses: 地址列表
        min_recent_closes: 最近24小时最小平仓数
        min_avg_daily_closes: 平均每天最小平仓数
        
    Returns:
        list: 满足条件的地址列表
    """
    qualified_addresses = []
    
    print("=" * 80)
    print(f"开始批量分析 {len(addresses)} 个地址")
    print(f"筛选条件: 最近24小时平仓数 >= {min_recent_closes}, 平均每天平仓数 >= {min_avg_daily_closes}")
    print("=" * 80)
    
    for i, address in enumerate(addresses, 1):
        print(f"\n[{i}/{len(addresses)}] 分析地址: {address}")
        print("-" * 80)
        
        analyzer = AverageHoldingTimeAnalyzer(address)
        meets_criteria, addr, freq_stats = analyzer.analyze(
            show_full_stats=False,
            min_recent_closes=min_recent_closes,
            min_avg_daily_closes=min_avg_daily_closes
        )
        
        if meets_criteria:
            qualified_addresses.append({
                'address': addr,
                'stats': freq_stats
            })
            print(f"\n✓ 地址 {addr} 满足条件，已加入筛选列表")
    
    # 打印汇总
    print("\n" + "=" * 80)
    print("【批量分析汇总】")
    print("=" * 80)
    print(f"总分析地址数: {len(addresses)}")
    print(f"满足条件地址数: {len(qualified_addresses)}")
    print(f"筛选通过率: {len(qualified_addresses) / len(addresses) * 100:.2f}%")
    
    if qualified_addresses:
        print("\n满足条件的地址列表:")
        for item in qualified_addresses:
            addr = item['address']
            stats = item['stats']
            print(f"\n  {addr}")
            print(f"    - 最近24小时平仓数: {stats['recent_24h_close_count']}")
            print(f"    - 平均每天平仓数: {stats['avg_daily_close_count']:.2f}")
            print(f"    - 总平仓数: {stats['total_close_count']}")
    
    return qualified_addresses


def main():
    """主函数"""
    
    # 示例1: 分析单个地址
    print("=" * 80)
    print("示例1: 分析单个地址")
    print("=" * 80)
    user_address = "0xf709deb9ca069e53a31a408fde397a87d025a352"
    analyzer = AverageHoldingTimeAnalyzer(user_address)
    analyzer.analyze(show_full_stats=True, min_recent_closes=24, min_avg_daily_closes=24)
    
    # 示例2: 批量分析多个地址
    # addresses = [
    #     "0x5c9c9ab381c841530464ef9ee402568f84c3b676",
    #     "0xf709deb9ca069e53a31a408fde397a87d025a352",
    #     # 添加更多地址...
    # ]
    # qualified = analyze_multiple_addresses(addresses, min_recent_closes=24, min_avg_daily_closes=24)


if __name__ == "__main__":
    main()