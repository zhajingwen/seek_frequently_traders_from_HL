# 高频交易者筛选工具 (Seek Frequently Traders from HL)

这是一个用于从 Hyperliquid 平台筛选高频交易者的 Python 工具。通过分析交易者的持仓时间和交易频率，识别出具有高频率交易特征的用户。

## 项目概述

本项目的主要功能是：
- 从 ApexLiquid 平台获取符合条件的交易者地址列表
- 通过 Hyperliquid API 分析这些交易者的交易数据
- 基于持仓时间和交易频率筛选出高频交易者
- 支持合约和现货交易的分别分析

## 核心特性

- **多平台数据整合**: 从 ApexLiquid 获取初始交易者列表，通过 Hyperliquid API 获取详细交易数据
- **智能筛选算法**: 基于持仓时间、交易频率等多个维度进行筛选
- **黑名单机制**: 支持黑名单功能，过滤已知的低质量地址
- **分类分析**: 分别分析合约交易和现货交易的模式
- **批量处理**: 支持批量分析多个交易者地址

## 筛选条件

### ApexLiquid 初始筛选条件：
- 最少交易天数：10天
- 最小收益率：5%
- 最大回撤：80%

### Hyperliquid 高频交易者筛选条件：
- 最近24小时平仓数 ≥ 24次
- 平均每天平仓数 ≥ 24次
- 排除黑名单中的地址

## 依赖项目

### 主要依赖：
- [filter-high-frequency-traders-from-from-apexliquid](https://github.com/zhajingwen/filter-high-frequency-traders-from-from-apexliquid)

### 数据源网站：
- [ApexLiquid](https://apexliquid.bot/home)
拿到地址清单：
过程条件：
- 最少交易10天
- 收益率最少为5%
- 最大回撤80%
数据来源页面：https://apexliquid.bot/topTraders
数据来源接口：https://apexliquid.bot/v1/web/top_trades
获取方法：POST
{"pagination":{"page_number":1,"page_size":1000},"sort_options":[{"field":"dayRoe","descending":true}],"time_range":"DAY","minTradeAge":"10","maxMaxDrawdown":"80","minWeekRoe":"5","minMonthRoe":"5","minAllTimeRoe":"5","telegram_id":""}
获取方式：
fetch("https://apexliquid.bot/v1/web/top_trades", {
  "headers": {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Google Chrome\";v=\"141\", \"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"141\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
  },
  "referrer": "https://apexliquid.bot/topTraders",
  "body": "{\"pagination\":{\"page_number\":1,\"page_size\":1000},\"sort_options\":[{\"field\":\"dayRoe\",\"descending\":true}],\"time_range\":\"DAY\",\"minTradeAge\":\"10\",\"maxMaxDrawdown\":\"80\",\"minWeekRoe\":\"5\",\"minMonthRoe\":\"5\",\"minAllTimeRoe\":\"5\",\"telegram_id\":\"\"}",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
});
```

## 安装和使用

### 环境要求
- Python 3.12+
- 依赖包：requests

### 安装步骤
1. 克隆项目到本地
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   # 或使用 uv
   uv sync
   ```

### 使用方法

#### 1. 配置数据源
将 ApexLiquid 获取的交易者数据放入 `utils/config.py` 文件中的 `address_list` 变量。

#### 2. 运行分析
```bash
python main.py
```

#### 3. 自定义筛选条件
可以在代码中修改筛选参数：
- `min_recent_closes`: 最近24小时最小平仓数（默认24）
- `min_avg_daily_closes`: 平均每天最小平仓数（默认24）

### 项目结构

```
seek_frequently_traders_from_HL/
├── main.py                                    # 主程序入口
├── pyproject.toml                             # 项目配置
├── README.md                                  # 项目说明文档
├── utils/
│   ├── config.py                              # 配置文件（包含交易者地址数据）
│   ├── average_holding_time.py                # 平均持仓时间分析器（基础版本）
│   ├── short_holding_time_and_high_frequency.py  # 高频交易分析器（主版本）
│   └── blacklist.txt                          # 黑名单文件
└── uv.lock                                    # 依赖锁定文件
```

## 核心算法

### 交易类型识别
- **现货交易**: 通过 coin 字段包含 '/' 或特定标识符识别
- **合约交易**: 除现货交易外的所有交易

### 持仓时间计算
1. 识别开仓和平仓交易对
2. 计算每笔交易的持仓时间
3. 统计平均持仓时间和交易频率

### 筛选逻辑
1. 获取交易者所有交易记录
2. 计算最近24小时的平仓次数
3. 计算平均每天的平仓次数
4. 应用筛选条件判断是否为高频交易者

## API 接口

### Hyperliquid API
- **接口地址**: `https://api.hyperliquid.xyz/info`
- **请求方法**: POST
- **主要功能**: 获取用户交易记录

### ApexLiquid API
- **接口地址**: `https://apexliquid.bot/v1/web/top_trades`
- **请求方法**: POST
- **主要功能**: 获取符合条件的交易者列表

## 注意事项

1. **API 限制**: 请注意 API 调用频率限制，避免过于频繁的请求
2. **数据准确性**: 筛选结果仅供参考，实际投资决策需要进一步验证
3. **黑名单维护**: 定期更新黑名单文件，过滤低质量地址
4. **网络连接**: 确保网络连接稳定，API 调用需要访问外部服务

## 开发说明

### 扩展功能
- 可以修改筛选条件来适应不同的需求
- 支持添加更多的分析维度
- 可以集成其他数据源

### 性能优化
- 支持批量处理多个地址
- 可以添加缓存机制减少重复请求
- 支持异步处理提高效率

## 许可证

本项目仅供学习和研究使用，请遵守相关平台的使用条款。