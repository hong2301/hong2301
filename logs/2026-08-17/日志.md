<h1 style="color:#58a6ff">2026年8月17日日志</h1>


　　今天上午先更新了每日开发日志，下午集中完成微信公众号OCR采集器的收尾：整理README、补充签名说明，并发布了V3.0.1版本（含完整版本信息），随后合入主分支。晚上先重构了个人主页，加入中文介绍、统计卡和提交动态图，但反复调试渲染效果后，最终决定将主页改为每日开发日志模式——用AI总结今日提交并配上表格和历史存档。为此搭了GitHub Actions流水线，调用DeepSeek生成总结，并逐步优化图表：尝试词云、饼图和玫瑰图，调整比例、配色与透明背景，最终采用PIL词云加SVG环形图，按日期分目录存档。之后给order系列二十多个仓库做了代码同步。全天围绕自动化和可视化折腾，总算把日志系统打磨得比较顺手了。

<div align="center"><img src="wordcloud.png" width="49%%" style="vertical-align:middle" alt="提交词云"/> &nbsp; <img src="pie.svg" width="32.7%%" style="vertical-align:middle" alt="提交时间分布"/></div>

📚 [查看历史日志](./logs/)