# 每日开发日志v5: 词云+饼图拼接单张(4:1) + 12/3/6/9刻度 + AI总结30-500字
import json, math, os, re, urllib.request, colorsys
from datetime import date, datetime

GH_TOKEN = os.environ.get("GH_TOKEN", "")
DS_TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")
AUTHOR = os.environ.get("GH_AUTHOR", "hong2301")
FONT = os.environ.get("FONT_PATH", "")

REPO_NAMES = {
    "wechat-article-collector": "微信公众号OCR采集器",
    "enterprise-query-platform": "企业查询平台",
    "nea_license_query": "能源局许可查询器",
}

PALETTE = {
    "blue": "#58a6ff", "green": "#3fb950", "purple": "#bc8cff",
    "orange": "#d29922", "cyan": "#39c5cf", "pink": "#f778ba",
    "teal": "#4ec9b0", "yellow": "#e3b341",
}


def gh_api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + GH_TOKEN,
        "Accept": "application/vnd.github+json", "User-Agent": "log-gen"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def ds_ai(text, max_tokens=800):
    body = json.dumps({"model": "deepseek-chat",
        "messages": [{"role": "user", "content": text}],
        "stream": False, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=body, headers={"Authorization": "Bearer " + DS_TOKEN,
                             "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def today_commits():
    since = datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z")
    commits, page = [], 1
    while True:
        url = ("https://api.github.com/search/commits?q=author:" + AUTHOR +
               "+committer-date:>=" + since + "&per_page=100&page=" + str(page))
        items = gh_api(url).get("items", [])
        for it in items:
            c = it["commit"]
            commits.append({"time": (c.get("committer") or {}).get("date", "")[11:19],
                "repo": ((it.get("repository") or {}).get("full_name", "")).replace("hong2301/", ""),
                "msg": (c.get("message") or "").split("\n")[0]})
        if len(items) < 100 or page >= 10:
            break
        page += 1
    commits.sort(key=lambda x: x["time"])
    return commits


def ai_log_and_color(commits):
    desc = chr(10).join("- " + c["time"] + " [" + REPO_NAMES.get(c["repo"], c["repo"]) + "] " + c["msg"] for c in commits)
    prompt = (
        "以下是我今天(GitHub: hong2301)的所有代码提交记录:" + chr(10) + desc +
        chr(10) + chr(10) + "请完成两件事:" + chr(10) +
        "1. 写一篇30-500字的中文今日开发日志, 第一人称, 像程序员日记, "
        "根据今天内容多少灵活调整篇幅, 内容少就短一点, 千万不要写废话. "
        "重要: 涉及具体项目/版本号/功能时, 前面必须带项目中文名" + chr(10) +
        "2. 根据今天的工作内容与状态, 从以下8个主题色中选一个最贴合的颜色:" + chr(10) +
        "blue, green, purple, orange, cyan, pink, teal, yellow" + chr(10) +
        "严格只输出JSON: {\"text\": \"日志内容\", \"color\": \"颜色名\"}")
    raw = ds_ai(prompt)
    m = re.search(r"\{.*\}", raw, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            color = str(d.get("color", "blue")).strip().lower()
            if color not in PALETTE:
                color = "blue"
            return str(d.get("text", "")).strip(), color
        except Exception:
            pass
    return raw.strip(), "blue"


def shades(hexc, n):
    r, g, b = int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    out = []
    for i in range(n):
        ll = max(0.25, min(0.85, l + (i - (n - 1) / 2) * 0.09))
        rr, gg, bb = colorsys.hls_to_rgb(h, ll, max(0.35, min(0.75, s)))
        out.append("#%02x%02x%02x" % (int(rr * 255), int(gg * 255), int(bb * 255)))
    return out


def _hex_rgb(hexc):
    return (int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16))


def _wordcloud_img(commits, hexc, width, height):
    from PIL import Image
    import numpy as np
    from wordcloud import WordCloud
    import jieba
    text = " ".join(c["msg"] for c in commits)
    seg = " ".join(w for w in jieba.cut(text) if len(w.strip()) > 1)
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in _hex_rgb(hexc)))

    def cf(word, font_size, position, orientation, random_state=None, **kw):
        try:
            rv = random_state.rand()
        except Exception:
            rv = random_state.random()
        ll = max(0.3, min(0.85, l + (rv - 0.5) * 0.35))
        r, g, b = colorsys.hls_to_rgb(h, ll, max(0.4, min(0.75, s)))
        return int(r * 255), int(g * 255), int(b * 255)

    wc = WordCloud(font_path=FONT, width=width, height=height,
        background_color="white", color_func=cf,
        max_words=80, random_state=42, collocations=False).generate(seg)
    arr = np.array(wc.to_image())
    rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = arr
    white = (arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235)
    rgba[white, 3] = 0
    rgba[~white, 3] = 255
    return Image.fromarray(rgba, "RGBA")


def _pie_img(commits, hexc, size=360, bg=(13, 17, 23, 255)):
    """环形时间饼图, 12/3/6/9时钟刻度, 中心数字"""
    from PIL import Image, ImageDraw, ImageFont
    buckets = [0, 0, 0, 0, 0, 0]
    for c in commits:
        buckets[min(int(c["time"][:2]) // 4, 5)] += 1
    total = len(commits) or 1
    img = Image.new("RGBA", (size, size), bg)
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    r = size * 0.30          # 外环半径
    r2 = size * 0.155        # 内环半径
    colors = shades(hexc, 6)
    start = -90
    for i, v in enumerate(buckets):
        frac = v / total
        a0 = start
        a1 = start + frac * 360
        if frac > 0.001:
            # 外扇区
            d.pieslice([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=colors[i])
        start = a1
    # 挖内圆
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=bg)
    # 中心数字(白色文字, 与日志正文同色系)
    try:
        f_big = ImageFont.truetype(FONT, size=int(size * 0.12))
        f_small = ImageFont.truetype(FONT, size=int(size * 0.055))
    except Exception:
        f_big = f_small = None
    txt = str(total)
    tw = d.textlength(txt, font=f_big) if f_big else 20
    d.text((cx - tw / 2, cy - size * 0.075), txt, fill=(230, 237, 243, 255), font=f_big)
    tw2 = d.textlength("次提交", font=f_small) if f_small else 30
    d.text((cx - tw2 / 2, cy + size * 0.02), "次提交", fill=(140, 149, 158, 255), font=f_small)
    # 时钟刻度 12/3/6/9(外圈, 亮色)
    lab_col = (201, 209, 217, 255)
    f_lab = f_small
    for ang, label in ((-90, "12"), (0, "3"), (90, "6"), (180, "9")):
        rad = math.radians(ang)
        lx = cx + (r + size * 0.06) * math.cos(rad)
        ly = cy + (r + size * 0.06) * math.sin(rad)
        lw = d.textlength(label, font=f_lab) if f_lab else 10
        d.text((lx - lw / 2, ly - size * 0.03), label, fill=lab_col, font=f_lab)
    return img


def compose_chart(commits, hexc, out):
    """拼接单张图 宽:高=4:1, 右侧正方形饼图, 剩余给词云"""
    from PIL import Image
    H = 300
    W = H * 4          # 1200
    pie_size = H       # 300 正方形饼图(右侧)
    wc_w = W - pie_size   # 900 词云区域
    # 深色底
    canvas = Image.new("RGBA", (W, H), (13, 17, 23, 255))
    # 词云覆盖左侧
    wc = _wordcloud_img(commits, hexc, wc_w, H)
    canvas.alpha_composite(wc, (0, 0))
    # 饼图贴右侧
    pie = _pie_img(commits, hexc, size=pie_size)
    canvas.alpha_composite(pie, (wc_w, 0))
    canvas.convert("RGB").save(out, "PNG")
    return W, H


def cn_date(d):
    return "%d年%d月%d日" % (d.year, d.month, d.day)


def build_log(date_str, commits, ai_text, hexc):
    title = '<h1 style="color:%s">%s日志</h1>' % (hexc, cn_date(date.fromisoformat(date_str)))
    lines = [title, "", ""]
    if ai_text:
        paras = ai_text.strip().split(chr(10))
        indented = chr(10).join("\u3000\u3000" + p if p.strip() else "" for p in paras)
        lines.append(indented)
    else:
        lines.append("*(今天没有提交记录)*" if not commits else "*日志生成中...*")
    lines.append("")
    lines.append('<div align="center"><img src="chart.png" alt="今日提交词云与时间分布"/></div>')
    lines.append("")
    lines.append("📚 [查看历史日志](./logs/)")
    return chr(10).join(lines)


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    today = date.today().isoformat()
    commits = today_commits()
    ai_text, color_name = None, "blue"
    if commits and DS_TOKEN:
        try:
            ai_text, color_name = ai_log_and_color(commits)
            print("AI:", ai_text[:80], "| 主题色:", color_name, PALETTE[color_name])
        except Exception as e:
            print("AI失败:", e)
    hexc = PALETTE.get(color_name, "#58a6ff")
    if commits:
        try:
            W, H = compose_chart(commits, hexc, os.path.join(root, "chart.png"))
            print("拼接图OK:", W, "x", H)
        except Exception as e:
            print("拼接图失败:", e)
    content = build_log(today, commits, ai_text, hexc)
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)
    # 存档: 按日期文件夹
    day_dir = os.path.join(root, "logs", today)
    os.makedirs(day_dir, exist_ok=True)
    if commits and os.path.isfile(os.path.join(root, "chart.png")):
        import shutil
        shutil.copy(os.path.join(root, "chart.png"), os.path.join(day_dir, "chart.png"))
        arch_lines = content.replace('width="1200"', 'width="100%"')
        with open(os.path.join(day_dir, "日志.md"), "w", encoding="utf-8") as f:
            f.write(content.replace('src="chart.png"', 'src="chart.png"'))
    print("完成: %d commits, 主题色 %s" % (len(commits), color_name))
