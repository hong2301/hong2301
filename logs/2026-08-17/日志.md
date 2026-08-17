<h1 style="color:#bc8cff">2026年8月17日日志</h1>


　　今天上午先更新了几次日常开发日志，下午集中打磨了「微信公众号OCR采集器」，发布了V3.0.1版本，补全了exe的版本信息，还清理了README，补充了发布者签名说明。之后花了不少精力重做个人主页，先试了带统计卡的方案但渲染有问题，最后换成有趣中文版加每日提交动态图，还加了折线图和GitHub Actions自动更新。晚上把十几个order系列项目用脚本统一同步了一遍，因为commit信息都一样，AI日志里就按项目名指代了。后半场主要在折腾个人主页的日志模块，反复调词云和饼图的尺寸、颜色、透明度和布局，从双图改为拼接单张，饼图从普通图改成环形，并加了时钟刻度，文字颜色也改成跟随主题自适应。最后修复了图片缓存问题，给URL加了日期版本参数，还顺便修了词云图的显示bug。整体今天主要是收尾和打磨，挺充实的。

---

<div align="center"><img src="https://cdn.jsdelivr.net/gh/hong2301/hong2301@main/wordcloud.png" width="49%" style="vertical-align:middle" alt="提交词云"/> &nbsp; <img src="https://cdn.jsdelivr.net/gh/hong2301/hong2301@main/pie.svg" width="32.7%" style="vertical-align:middle" alt="提交时间分布"/></div>

📚 [查看历史日志](./logs/)