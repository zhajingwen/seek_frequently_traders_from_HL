import json
from utils.config import address_list
from utils.average_holding_time import AverageHoldingTimeAnalyzer


address_list = json.loads(address_list)
trades = address_list.get("data", {}).get("trades", [])

high_frequency_traders = []

# 黑名单记录
with open("utils/blacklist.txt", "r") as f:
    content = f.read()

for trade in trades:
    address = trade.get("address")
    if address:
        # 如果地址在黑名单中，则跳过
        if address in content:
            continue

        # # 分析指定的地址
        # if address != '0x17eb41cc719d2b7406acea9bdb1dcf63ecd8067f':
        #     continue

        analyzer = AverageHoldingTimeAnalyzer(address)
        address = analyzer.analyze()
        if address:
            high_frequency_traders.append(address)
    else:
        print(f"Address is empty for trade: {trade}")

print(high_frequency_traders)
