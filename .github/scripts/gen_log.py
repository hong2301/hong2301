# 每日开发日志v3: AI判断主题色(全篇统一) + 日期标题 + 100字总结 + 词云&饼图
import json, math, os, re, urllib.request, colorsys
from datetime import date, datetime

GH_TOKEN = os.environ.get("GH_TOKEN", "")
DS_TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")
AUTHOR = os.environ.get("GH_AUTHOR", "hong2301")
FONT = os.environ.get("FONT_PATH", "")

# 低饱和易读色板(AI 从中选)
PALETTE = {
    "blue":   "#58a6ff",
    "green":  "#3fb950",
    "purple": "#bc8cff",
    "orange": "#d29922",
    "cyan":   "#39c5cf",
    "pink":   "#f778ba",
    "teal":   "#4ec9b0",
    "yellow": "#e3b341",
}

def gh_api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "User-Agent": "log-gen",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def ds_ai(text, max_tokens=500):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=body, headers={
            "Authorization": "Bearer " + DS_TOKEN,
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
        url = ("https://api.github.com/search/commits?q=author:" + AUTHOR +
               "+committer-date:>=" + since + "&per_page=100&page=" + str(page))
        data = gh_api(url)
        items = data.get("items", [])
        for it in items:
            c = it["commit"]
            commits.append({
                "time": (c.get("committer") or {}).get("date", "")[11:19],
                "repo": ((it.get("repository") or {}).get("full_name", "")).replace("hong2301/", ""),
                "msg": (c.get("message") or "").split("\n")[0],
            })
        if len(items) < 100 or page >= 10:
            break
        page += 1
    commits.sort(key=lambda x: x["time"])
    return commits

def ai_log_and_color(commits):
    """AI 生成日志文本 + 判断主题色(返回 (text, color_name))"""
    desc = "\n".join("- " + c["time"] + " [" + c["repo"] + "] " + c["msg"] for c in commits)
    prompt = (
        "以下是我今天(GitHub: hong2301)的所有代码提交记录:\n" + desc +
        "\n\n请完成两件事:\n"
        "1. 写一篇约100字的中文今日开发日志, 第一人称, 像程序员日记, "
        "自然叙述今天做了什么、解决了什么问题, 不要列清单, 不要说'今天提交了N次代码'这类废话\n"
        "2. 根据今天的工作内容与状态, 从以下8个主题色中选一个最贴合的颜色"
        "(例如: 大量写码忙碌→orange/yellow, 平静收尾→blue/green, 有成就热情→pink/purple, 创新探索→cyan/teal):\n"
        "blue, green, purple, orange, cyan, pink, teal, yellow\n"
        "严格只输出JSON, 格式: {\"text\": \"日志内容\", \"color\": \"颜色名\"}"
    )
    raw = ds_ai(prompt)
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            text = str(d.get("text", "")).strip()
            color = str(d.get("color", "blue")).strip().lower()
            if color not in PALETTE:
                color = "blue"
            return text, color
        except Exception:
            pass
    return raw.strip(), "blue"

def shades(hexc, n):
    """主色生成 n 个同色系明度变体(低饱和易读)"""
    r = int(hexc[1:3], 16); g = int(hexc[3:5], 16); b = int(hexc[5:7], 16)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    out = []
    for i in range(n):
        ll = max(0.25, min(0.85, l + (i - (n - 1) / 2) * 0.09))
        ss = max(0.35, min(0.75, s))
        rr, gg, bb = colorsys.hls_to_rgb(h, ll, ss)
        out.append("#%02x%02x%02x" % (int(rr * 255), int(gg * 255), int(bb * 255)))
    return out

def build_wordcloud(commits, out, hexc):
    from wordcloud import WordCloud
    import jieba
    text = " ".join(c["msg"] for c in commits)
    seg = " ".join(w for w in jieba.cut(text) if len(w.strip()) > 1)
    base = (int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16))
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in base))

    def color_func(word, font_size, position, orientation, random_state=None, **kw):
        try:
            rv = random_state.rand()      # numpy RandomState
        except AttributeError:
            rv = random_state.random()    # python random.Random
        ll = max(0.3, min(0.85, l + (rv - 0.5) * 0.35))
        ss = max(0.4, min(0.75, s))
        r, g, b = colorsys.hls_to_rgb(h, ll, ss)
        return int(r * 255), int(g * 255), int(b * 255)

    wc = WordCloud(font_path=FONT, width=760, height=420,
                   background_color="#0d1117", color_func=color_func,
                   max_words=80, random_state=42, collocations=False).generate(seg)
    wc.to_file(out)

def _polar(cx, cy, r, deg):
    rad = math.radians(deg)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)

def build_pie_svg(commits, hexc):
    buckets = [("0-3点", 0), ("4-7点", 0), ("8-11点", 0),
               ("12-15点", 0), ("16-19点", 0), ("20-23点", 0)]
    for c in commits:
        hh = int(c["time"][:2])
        b = min(hh // 4, 5)
        buckets[b] = (buckets[b][0], buckets[b][1] + 1)
    total = len(commits) or 1
    W, H, cx, cy, r, r2 = 520, 420, 185, 210, 120, 66
    colors = shades(hexc, len(buckets))
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W, H, W, H),
         '<rect width="100%%" height="100%%" fill="#0d1117"/>']
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
            d = ("M %.1f %.1f A %d %d 0 %d 1 %.1f %.1f L %.1f %.1f A %d %d 0 %d 0 %.1f %.1f Z"
                 % (x0, y0, r, r, large, x1, y1, x2, y2, r2, r2, large, x3, y3))
            s.append('<path d="' + d + '" fill="' + colors[i] + '"/>')
        start = a1
    s.append('<text x="%d" y="%d" fill="#e6edf3" font-size="22" text-anchor="middle" font-family="sans-serif">共 %d</text>'
             % (cx, cy - 6, total))
    s.append('<text x="%d" y="%d" fill="#8b949e" font-size="13" text-anchor="middle" font-family="sans-serif">次提交</text>'
             % (cx, cy + 18))
    ly = 36
    for i, (name, v) in enumerate(buckets):
        pct = v / total * 100
        s.append('<rect x="330" y="%d" width="14" height="14" rx="3" fill="%s"/>' % (ly, colors[i]))
        s.append('<text x="352" y="%d" fill="#c9d1d9" font-size="13" font-family="sans-serif">%s  %d (%.0f%%)</text>'
                 % (ly + 12, name, v, pct))
        ly += 30
    s.append('</svg>')
    return "".join(s)

def cn_date(d):
    return "%d年%d月%d日" % (d.year, d.month, d.day)

def build_log(date_str, commits, ai_text, hexc, img_line):
    title = '<h1 style="color:%s">%s日志</h1>' % (hexc, cn_date(date.fromisoformat(date_str)))
    lines = [title, "", ""]
    if ai_text:
        lines.append(ai_text.strip())
    else:
        lines.append("*(今天没有提交记录)*" if not commits else "*日志生成中...*")
    lines.append("")
    lines.append(img_line)
    lines.append("")
    lines.append("📚 [查看历史日志](./logs/)")
    return "\n".join(lines)

if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    today = date.today().isoformat()
    commits = today_commits()
    ai_text, color_name = None, "blue"
    if commits and DS_TOKEN:
        try:
            ai_text, color_name = ai_log_and_color(commits)
            print("AI:", ai_text[:60], "| 主题色:", color_name, PALETTE[color_name])
        except Exception as e:
            print("AI失败:", e)
    hexc = PALETTE.get(color_name, "#58a6ff")
    img_now = ('<img src="wordcloud.png" width="49%" alt="提交词云"/> '
               '<img src="pie.svg" width="49%" alt="提交时间分布"/>')
    if commits:
        try:
            build_wordcloud(commits, os.path.join(root, "wordcloud.png"), hexc)
            print("词云OK")
        except Exception as e:
            print("词云失败:", e)
        with open(os.path.join(root, "pie.svg"), "w", encoding="utf-8") as f:
            f.write(build_pie_svg(commits, hexc))
        print("饼图OK")
    content = build_log(today, commits, ai_text, hexc, img_now)
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)
    os.makedirs(os.path.join(root, "logs"), exist_ok=True)
    if commits:
        import shutil
        wc_a, pie_a = today + "-wordcloud.png", today + "-pie.svg"
        shutil.copy(os.path.join(root, "wordcloud.png"), os.path.join(root, "logs", wc_a))
        shutil.copy(os.path.join(root, "pie.svg"), os.path.join(root, "logs", pie_a))
        img_arch = ('<img src="%s" width="49%%" alt="提交词云"/> '
                    '<img src="%s" width="49%%" alt="提交时间分布"/>' % (wc_a, pie_a))
    else:
        img_arch = img_now
    with open(os.path.join(root, "logs", today + ".md"), "w", encoding="utf-8") as f:
        f.write(build_log(today, commits, ai_text, hexc, img_arch))
    print("完成: %d commits, 主题色 %s" % (len(commits), color_name))
