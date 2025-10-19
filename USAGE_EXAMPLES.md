# 使用示例和配置说明

## 基本使用示例

### 1. 单地址分析示例

```python
from utils.short_holding_time_and_high_frequency import AverageHoldingTimeAnalyzer

# 创建分析器实例
analyzer = AverageHoldingTimeAnalyzer("0x1234567890abcdef...")

# 执行分析
meets_criteria, address, freq_stats = analyzer.analyze()

if meets_criteria:
    print(f"地址 {address} 符合高频交易者条件")
    print(f"频率统计: {freq_stats}")
else:
    print(f"地址 {address} 不符合条件")
```

### 2. 批量分析示例

```python
from utils.short_holding_time_and_high_frequency import analyze_multiple_addresses

# 地址列表
addresses = [
    "0x1234567890abcdef...",
    "0xabcdef1234567890...",
    "0x9876543210fedcba..."
]

# 批量分析
qualified_addresses = analyze_multiple_addresses(
    addresses,
    min_recent_closes=24,      # 最近24小时最小平仓数
    min_avg_daily_closes=24    # 平均每天最小平仓数
)

print(f"符合条件的高频交易者: {qualified_addresses}")
```

### 3. 自定义筛选条件示例

```python
from utils.short_holding_time_and_high_frequency import AverageHoldingTimeAnalyzer

analyzer = AverageHoldingTimeAnalyzer("0x1234567890abcdef...")

# 自定义筛选条件
meets_criteria, address, freq_stats = analyzer.analyze(
    show_full_stats=True,      # 显示详细统计信息
    min_recent_closes=50,      # 更严格的24小时平仓数要求
    min_avg_daily_closes=30    # 更严格的日均平仓数要求
)
```

## 配置说明

### 1. config.py 配置

在 `utils/config.py` 文件中配置 ApexLiquid 获取的数据：

```python
address_list = """{
    "data": {
        "trades": [
            {
                "address": "0x1234567890abcdef...",
                "dayRoe": "15.5",
                "maxDrawdown": "25.0",
                "tradeAge": "30"
            },
            {
                "address": "0xabcdef1234567890...",
                "dayRoe": "8.2",
                "maxDrawdown": "45.0",
                "tradeAge": "15"
            }
        ]
    }
}"""
```

### 2. 黑名单配置

在 `utils/blacklist.txt` 文件中添加需要排除的地址：

```
0x1111111111111111111111111111111111111111
0x2222222222222222222222222222222222222222
0x3333333333333333333333333333333333333333
```

### 3. 筛选参数配置

可以在代码中调整筛选参数：

```python
# 在 main.py 中修改
for trade in trades:
    address = trade.get("address")
    if address and address not in content:
        analyzer = AverageHoldingTimeAnalyzer(address)
        
        # 自定义筛选条件
        meets_criteria, addr, freq_stats = analyzer.analyze(
            show_full_stats=False,
            min_recent_closes=30,      # 提高24小时平仓数要求
            min_avg_daily_closes=25    # 提高日均平仓数要求
        )
        
        if meets_criteria:
            high_frequency_traders.append(addr)
```

## 高级使用示例

### 1. 分析特定时间段的数据

```python
from datetime import datetime, timedelta

class TimeFilteredAnalyzer(AverageHoldingTimeAnalyzer):
    def __init__(self, user_address, start_date, end_date):
        super().__init__(user_address)
        self.start_date = start_date
        self.end_date = end_date
    
    def filter_fills_by_time(self, fills):
        """根据时间范围过滤交易记录"""
        filtered_fills = []
        for fill in fills:
            fill_time = datetime.fromtimestamp(fill['time'] / 1000)
            if self.start_date <= fill_time <= self.end_date:
                filtered_fills.append(fill)
        return filtered_fills
    
    def fetch_user_fills(self):
        """获取过滤后的交易记录"""
        fills = super().fetch_user_fills()
        return self.filter_fills_by_time(fills)

# 使用示例
start_date = datetime.now() - timedelta(days=7)  # 最近7天
end_date = datetime.now()

analyzer = TimeFilteredAnalyzer("0x1234567890abcdef...", start_date, end_date)
meets_criteria, address, freq_stats = analyzer.analyze()
```

### 2. 导出分析结果

```python
import json
import csv
from datetime import datetime

def export_results(high_frequency_traders, filename="results.json"):
    """导出分析结果到文件"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_count": len(high_frequency_traders),
        "addresses": high_frequency_traders
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

def export_to_csv(high_frequency_traders, filename="results.csv"):
    """导出分析结果到CSV文件"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Address', 'Timestamp'])
        for address in high_frequency_traders:
            writer.writerow([address, datetime.now().isoformat()])

# 使用示例
export_results(high_frequency_traders, "high_frequency_traders.json")
export_to_csv(high_frequency_traders, "high_frequency_traders.csv")
```

### 3. 实时监控示例

```python
import time
from datetime import datetime

def monitor_traders(addresses, interval=3600):  # 每小时检查一次
    """实时监控交易者状态"""
    while True:
        print(f"\n[{datetime.now()}] 开始监控检查...")
        
        qualified_addresses = analyze_multiple_addresses(addresses)
        
        if qualified_addresses:
            print(f"发现 {len(qualified_addresses)} 个高频交易者:")
            for addr in qualified_addresses:
                print(f"  - {addr}")
        else:
            print("未发现符合条件的高频交易者")
        
        print(f"等待 {interval} 秒后进行下次检查...")
        time.sleep(interval)

# 使用示例
addresses = ["0x1234567890abcdef...", "0xabcdef1234567890..."]
monitor_traders(addresses, interval=1800)  # 每30分钟检查一次
```

### 4. 错误处理和重试机制

```python
import time
from requests.exceptions import RequestException

def robust_analyze(analyzer, max_retries=3, delay=1):
    """带重试机制的分析函数"""
    for attempt in range(max_retries):
        try:
            return analyzer.analyze()
        except RequestException as e:
            print(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))  # 指数退避
            else:
                print(f"地址 {analyzer.user_address} 分析失败，跳过")
                return False, analyzer.user_address, None
        except Exception as e:
            print(f"分析过程中出现未知错误: {e}")
            return False, analyzer.user_address, None

# 使用示例
analyzer = AverageHoldingTimeAnalyzer("0x1234567890abcdef...")
meets_criteria, address, freq_stats = robust_analyze(analyzer)
```

## 性能优化示例

### 1. 并发处理示例

```python
import concurrent.futures
from threading import Lock

def concurrent_analyze(addresses, max_workers=5):
    """并发分析多个地址"""
    results = []
    lock = Lock()
    
    def analyze_single(address):
        try:
            analyzer = AverageHoldingTimeAnalyzer(address)
            meets_criteria, addr, freq_stats = analyzer.analyze(show_full_stats=False)
            
            with lock:
                if meets_criteria:
                    results.append(addr)
                    print(f"✓ {addr} 符合条件")
                else:
                    print(f"✗ {addr} 不符合条件")
        except Exception as e:
            with lock:
                print(f"✗ {address} 分析失败: {e}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(analyze_single, addresses)
    
    return results

# 使用示例
addresses = ["0x1234567890abcdef...", "0xabcdef1234567890..."]
qualified_addresses = concurrent_analyze(addresses, max_workers=3)
```

### 2. 缓存机制示例

```python
import pickle
import os
from datetime import datetime, timedelta

class CachedAnalyzer(AverageHoldingTimeAnalyzer):
    def __init__(self, user_address, cache_dir="cache"):
        super().__init__(user_address)
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_file = os.path.join(cache_dir, f"{user_address}.pkl")
    
    def fetch_user_fills(self):
        """带缓存的交易记录获取"""
        # 检查缓存是否有效（1小时内）
        if os.path.exists(self.cache_file):
            cache_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
            if datetime.now() - cache_time < timedelta(hours=1):
                print(f"使用缓存数据: {self.user_address}")
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
        
        # 获取新数据并缓存
        print(f"获取新数据: {self.user_address}")
        fills = super().fetch_user_fills()
        with open(self.cache_file, 'wb') as f:
            pickle.dump(fills, f)
        return fills

# 使用示例
analyzer = CachedAnalyzer("0x1234567890abcdef...")
meets_criteria, address, freq_stats = analyzer.analyze()
```

## 调试和日志示例

### 1. 详细日志记录

```python
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analysis.log'),
        logging.StreamHandler()
    ]
)

class LoggedAnalyzer(AverageHoldingTimeAnalyzer):
    def analyze(self, **kwargs):
        logging.info(f"开始分析地址: {self.user_address}")
        
        try:
            result = super().analyze(**kwargs)
            meets_criteria, address, freq_stats = result
            
            if meets_criteria:
                logging.info(f"地址 {address} 符合高频交易者条件")
                logging.info(f"频率统计: {freq_stats}")
            else:
                logging.info(f"地址 {address} 不符合条件")
            
            return result
        except Exception as e:
            logging.error(f"分析地址 {self.user_address} 时出错: {e}")
            raise

# 使用示例
analyzer = LoggedAnalyzer("0x1234567890abcdef...")
meets_criteria, address, freq_stats = analyzer.analyze()
```

### 2. 调试模式

```python
class DebugAnalyzer(AverageHoldingTimeAnalyzer):
    def __init__(self, user_address, debug=False):
        super().__init__(user_address)
        self.debug = debug
    
    def analyze(self, **kwargs):
        if self.debug:
            print(f"调试模式: 分析地址 {self.user_address}")
            print(f"筛选参数: {kwargs}")
        
        result = super().analyze(**kwargs)
        
        if self.debug:
            meets_criteria, address, freq_stats = result
            print(f"分析结果: {meets_criteria}")
            print(f"频率统计: {freq_stats}")
        
        return result

# 使用示例
analyzer = DebugAnalyzer("0x1234567890abcdef...", debug=True)
meets_criteria, address, freq_stats = analyzer.analyze()
```
