# laoyu-software-center-downloads
捞鱼软件中心 Windows 下载包与校验值；应用源码另行维护。

## 集中下载统计

统一入口：<https://lyzbcy.github.io/laoyu-software-center-downloads/stats/downloads.json>

每天上海时间09:43计划采集，GitHub调度可能延迟。公开仓库使用标准Ubuntu运行器，不创建常驻服务器，也不上传Actions产物或使用缓存。注册信息在 `products.json`，只包含公开产品ID、仓库和安装包匹配规则，应用私有源码不公开。

统计所有公开Release附件（包括预发布，排除草稿）的累计 `download_count`，包含版本更新和重复下载，不代表独立用户数。没有Release来源的产品为 `null/untracked`，不写成0。单个项目采集失败保留上次计数及其真实更新时间，标记 `stale`；全部失败则保留现有公开文件。各产品计数均为GitHub附件统计，服务器、网盘和第三方镜像未计入。

`scripts/collect.py` 一次采集所有项目，同一仓库的分页列表共享；当前9个仓库约16次采集请求/天，API分页增多时按实际请求计。版本展示信息共用该入口，实际下载的版本和哈希仍由客户端点击时核实。每日快照保留最近730天。

妙妙工具合集通过独立的 `statsRepo` 统计 `lyzbcy/laoyu-miaomiao-tools` 的全部 Skill ZIP 附件，统计源不等于 Windows 安装渠道。新加的统计来源放在 `additionalStats`，新客户端合并展示；`products` 的兼容条目保持旧客户端可读，避免旧版因为不认识 Skill 下载而拒绝整个数据入口。

Actions提交后显式请求Pages重建，避免内置GITHUB_TOKEN提交不触发部署而导致入口停留在旧数据。支持手动运行，API失败及推送冲突会显示失败结果。

GitHub规则依据：[Actions计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)、[REST额度](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)。GITHUB_TOKEN额度为每仓库每小时1000次请求；客户端读取Pages静态JSON不占GitHub REST API额度。
