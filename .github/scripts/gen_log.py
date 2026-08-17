"""生成每日开发日志v2: 日期标题 + AI总结(100字) + 词云(左) + 时间饼图(右) + 历史存档"""
import json, math, os, urllib.request
from datetime import date, datetime

GH_TOKEN = os.environ.get("GH_TOKEN", "")
DS_TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")
AUTHOR = os.environ.get("GH_AUTHOR", "hong2301")
FONT = os.environ.get("FONT_PATH", "")

def gh_api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "log-gen",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def ds_ai(text, max_tokens=400):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=body, headers={
            "Authorization": f"Bearer {DS_TOKEN}",
            "Content-Type": "application/json",
        })
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]

def today_commits():
    since = datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z")
    commits = []
    page = 1
    while True:
        url = (f"https://api.github.com/search/commits?q=author:{AUTHOR}"
               f"+committer-date:>={since}&per_page=100&page={page}")
        data = gh_api(url)
        items = data.get("items", [])
        for it in items:
            c = it["commit"]
            commits.append({
                "time": (c.get("committer") or {}).get("date", "")[11:19],
                "repo": ((it.get("repository") or {}).get("full_name", "")).replace("hong2301/", ""),
                "msg": (c.get("message") or "").split("\n")[0],
                "sha": it.get("sha", "")[:7],
            })
        if len(items) < 100 or page >= 10:
            break
        page += 1
    commits.sort(key=lambda x: x["time"])
    return commits

def build_wordcloud(commits, out):
    from wordcloud import WordCloud
    import jieba
    text = " ".join(c["msg"] for c in commits)
    seg = " ".join(w for w in jieba.cut(text) if len(w.strip()) > 1)
    wc = WordCloud(font_path=FONT, width=760, height=420,
                   background_color="#0d1117", colormap="Greens",
                   max_words=80, random_state=42, collocations=False).generate(seg)
    wc.to_file(out)

def _polar(cx, cy, r, deg):
    rad = math.radians(deg)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)

def build_pie_svg(commits):
    buckets = [("0-3点", 0), ("4-7点", 0), ("8-11点", 0),
               ("12-15点", 0), ("16-19点", 0), ("20-23点", 0)]
    for c in commits:
        h = int(c["time"][:2])
        buckets[min(h // 4, 5)] = (buckets[min(h // 4, 5)][0],
                                   buckets[min(h // 4, 5)][1] + 1)
    total = len(commits) or 1
    W, H, cx, cy, r, r2 = 520, 420, 185, 210, 120, 66
    colors = ["#2ea043", "#3fb950", "#56d364", "#7ee787", "#aff5b4", "#d9ffdd"]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="100%" height="100%" fill="#0d1117"/>']
    start = -90
    for i, (name, v) in enumerate(buckets):
        frac = v / total
        a0, a1 = start, start + frac * 360
        if frac > 0.001:
            x0, y0 = _polar(cx, cy, r, a0)
            x1, y1 = _polar(cx, cy, r, a1)
            x2, y2 = _polar(cx, cy, r2, a1)
            x3, y3 = _polar(cx, cy, r2, a0)
            large = 1 if (a1 - a0) > 180 else 0
            d = (f"M {x0:.1f} {y0:.1f} A {r} {r} 0 {large} 1 {x1:.1f} {y1:.1f} "
                 f"L {x2:.1f} {y2:.1f} A {r2} {r2} 0 {large} 0 {x3:.1f} {y3:.1f} Z")
            s.append(f'<path d="{d}" fill="{colors[i % len(colors)]}"/>')
        start = a1
    s.append(f'<text x="{cx}" y="{cy-6}" fill="#e6edf3" font-size="22" text-anchor="middle" font-family="sans-serif">共 {total}</text>')
    s.append(f'<text x="{cx}" y="{cy+18}" fill="#8b949e" font-size="13" text-anchor="middle" font-family="sans-serif">次提交</text>')
    ly = 36
    for i, (name, v) in enumerate(buckets):
        pct = v / total * 100
        s.append(f'<rect x="{330}" y="{ly}" width="14" height="14" rx="3" fill="{colors[i % len(colors)]}"/>')
        s.append(f'<text x="{352}" y="{ly+12}" fill="#c9d1d9" font-size="13" font-family="sans-serif">{name}  {v} ({pct:.0f}%)</text>')
        ly += 30
    s.append('</svg>')
    return "".join(s)

def cn_date(d):
    return f"{d.year}年{d.month}月{d.day}日"

def build_log(date_str, commits, ai_text, img_line):
    lines = [f"# {cn_date(date.fromisoformat(date_str))}日志", "", ""]
    if ai_text:
        lines.append(ai_text.strip())
    else:
        lines.append("*(今天没有提交记录)*" if not commits else "*日志生成中...*")
    lines.append("")
    lines.append(img_line)
    lines.append("")
    lines.append(f"📚 [查看历史日志](./logs/)")
    return "\n".join(lines)

if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    today = date.today().isoformat()
    commits = today_commits()
    ai_text = None
    if commits and DS_TOKEN:
        try:
            desc = "\n".join(f"- {c['time']} [{c['repo']}] {c['msg']}" for c in commits)
            ai_text = ds_ai(
                "以下是我今天(GitHub: hong2301)的所有代码提交记录:\n" + desc +
                "\n\n请用中文写一篇约100字的今日开发日志, 第一人称, 像程序员日记, "
                "自然叙述今天做了什么、解决了什么问题, 不要列清单, 不要说'今天提交了N次代码'这类废话")
            print("AI:", ai_text)
        except Exception as e:
            print("AI失败:", e)
    # 词云 + 饼图
    if commits:
        try:
            build_wordcloud(commits, os.path.join(root, "wordcloud.png"))
            print("词云OK")
        except Exception as e:
            print("词云失败:", e)
        with open(os.path.join(root, "pie.svg"), "w", encoding="utf-8") as f:
            f.write(build_pie_svg(commits))
        print("饼图OK")
    # README(引用根目录图) + 存档(复制按日期命名的图)
    import shutil
    img_now = '<img src="wordcloud.png" width="49%" alt="提交词云"/> <img src="pie.svg" width="49%" alt="提交时间分布"/>'
    content = build_log(today, commits, ai_text, img_now)
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)
    os.makedirs(os.path.join(root, "logs"), exist_ok=True)
    if commits:
        wc_a, pie_a = f"{today}-wordcloud.png", f"{today}-pie.svg"
        shutil.copy(os.path.join(root, "wordcloud.png"), os.path.join(root, "logs", wc_a))
        shutil.copy(os.path.join(root, "pie.svg"), os.path.join(root, "logs", pie_a))
        img_arch = (f'<img src="{wc_a}" width="49%" alt="提交词云"/> '
                    f'<img src="{pie_a}" width="49%" alt="提交时间分布"/>')
    else:
        img_arch = img_now
    with open(os.path.join(root, "logs", today + ".md"), "w", encoding="utf-8") as f:
        f.write(build_log(today, commits, ai_text, img_arch))
    print(f"完成: {len(commits)} commits")
