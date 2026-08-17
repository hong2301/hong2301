<h1 style="color:#bc8cff">2026年8月17日日志</h1>


　　今天上午连续补了三次开发日志，其实是在整理之前的进度。下午集中把微信公众号OCR采集器收尾了，先写完了给用户看的README，然后处理了自签名证书的说明，因为自签名honononong导致拦截是正常现象，得提前讲清楚。之后发布了V3.0.1版本，给exe补齐了完整版本信息，合并到master后又清理了README里多余的证书章节。

　　晚上转去搞个人主页，折腾了好久。先是试了带HTML和统计卡的版本，结果渲染有问题，被我推翻了。后来干脆换了个全新思路，用中文风格配每日提交动态图。接着越做越上头，加了折线图、Actions自动更新，最后直接做成了每日开发日志页，用AI自动总结当天提交。期间一直在调布局：词云和饼图的尺寸比例改了好几轮，从420px统一到350px，又调整成3:2的宽高比，还把饼图换成玫瑰图再换回环形图，文字改成深色，缩进也反复调。最后又把代码同步到十几个order开头的项目仓库，像order-boss-crawler、order-jd-data-tool这些，确保它们保持一致。整体感觉是从下午到晚上都在打磨细节，挺累但挺有成就感的。

<div align="center"><img src="wordcloud.png" width="49%%" style="vertical-align:middle" alt="提交词云"/> &nbsp; <img src="pie.svg" width="32.7%%" style="vertical-align:middle" alt="提交时间分布"/></div>

📚 [查看历史日志](./logs/)