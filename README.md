## 依赖该项目：

https://github.com/zhajingwen/filter-high-frequency-traders-from-from-apexliquid

---

## 依赖该网站：

https://apexliquid.bot/home
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