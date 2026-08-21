# 每日开发日志v6: 词云PIL透明 + 饼图SVG矢量透明 + 12/3/6/9刻度 + AI 30-500字
import json, math, os, re, urllib.request, colorsys
from urllib.parse import quote as _urlquote
from datetime import date, datetime, timezone, timedelta

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


def ds_ai(text, max_tokens=2000):
    body = json.dumps({"model": "deepseek-chat",
        "messages": [{"role": "user", "content": text}],
        "stream": False, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions",
        data=body, headers={"Authorization": "Bearer " + DS_TOKEN,
                             "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def bj_yesterday_dates():
    """返回(昨天北京日期str, 昨天北京时间范围UTC)"""
    bj = timezone(timedelta(hours=8))
    now = datetime.now(bj)
    y = (now - timedelta(days=1)).date()
    # 北京昨天全天 = UTC (y-1天 16:00) 到 (y 16:00)
    utc_start = datetime(y.year, y.month, y.day, 0, 0, 0, tzinfo=bj).astimezone(timezone.utc)
    utc_end = (utc_start + timedelta(days=1))
    return y.isoformat(), utc_start, utc_end


def today_commits():
    """查昨天(北京)全天提交: 遍历所有仓库所有分支(Repo Commits API), 避免漏掉非默认分支
    因为 GitHub Search Commits API 只搜默认分支, 会漏掉 feature/业务分支的提交"""
    date_str, utc_start, utc_end = bj_yesterday_dates()
    since = utc_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    until = utc_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    # 取用户所有仓库(含私有): 必须用 /user/repos 并分页, /users/{name}/repos 只返回公开仓库
    repos = []
    page = 1
    while True:
        _r = gh_api("https://api.github.com/user/repos?per_page=100&page=" + str(page) + "&type=all")
        repos.extend(_r if isinstance(_r, list) else [])
        if len(_r) < 100:
            break
        page += 1
    # 只保留近段有 push 的仓库, 大幅减少 API 调用
    _active = []
    for r in repos:
        if not isinstance(r, dict):
            continue
        pushed = r.get("pushed_at", "")
        try:
            pdt = datetime.fromisoformat(pushed.replace("Z", "+00:00")).astimezone(timezone.utc)
            if pdt >= utc_start - timedelta(days=3):   # 最近3天有push才深入遍历
                _active.append(r)
        except Exception:
            _active.append(r)
    repos = _active
    commits, seen = [], set()
    for r in repos:
        if not isinstance(r, dict):
            continue
        repo = r.get("name", "")
        if not repo:
            continue
        try:
            branches = gh_api("https://api.github.com/repos/" + AUTHOR + "/" + repo + "/branches?per_page=100")
        except Exception:
            continue
        for br in branches:
            if not isinstance(br, dict):
                continue
            branch = br.get("name", "")
            if not branch:
                continue
            page = 1
            while True:
                url = ("https://api.github.com/repos/" + AUTHOR + "/" + repo +
                       "/commits?sha=" + _urlquote(branch) + "&since=" + since + "&until=" + until +
                       "&per_page=100&page=" + str(page))
                try:
                    items = gh_api(url)
                except Exception:
                    items = []
                if not items:
                    break
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    c = it.get("commit") or {}
                    cd = (c.get("committer") or {}).get("date", "")
                    if not cd:
                        continue
                    try:
                        cd_dt = datetime.fromisoformat(cd.replace("Z", "+00:00")).astimezone(timezone.utc)
                    except Exception:
                        continue
                    if utc_start <= cd_dt < utc_end and it.get("sha") not in seen:
                        seen.add(it.get("sha"))
                        commits.append({"time": cd[11:19],
                            "_date": cd, "repo": repo,
                            "msg": (c.get("message") or "").split(chr(10))[0]})
                if len(items) < 100:
                    break
                page += 1
    commits.sort(key=lambda x: x["time"])
    return commits


def ai_log_and_color(commits):
    desc = chr(10).join("- " + c["time"] + " [" + REPO_NAMES.get(c["repo"], c["repo"]) + "] " + c["msg"] for c in commits)
    prompt = (
        "以下是我今天(GitHub: hong2301)的全部代码提交记录(共%d条):" % len(commits) + chr(10) + desc +
        chr(10) + chr(10) + "请完成两件事:" + chr(10) +
        "1. 写一篇30-500字的中文今日开发日志, 第一人称, 只客观记录当天做了什么+简评当天, "
        "根据今天内容多少灵活调整篇幅, 内容少就短一点, 千万不要写废话. "
        "重要: 涉及具体项目/版本号/功能时, 前面必须带项目中文名. "
        "严禁: 对未来的任何推测或期望(如'明天要...'、'明天应该...'、'接下来得...'), "
        "严禁情绪宣泄, 只描述事实与当天评价" + chr(10) +
        "2. 根据今天的工作内容与状态, 从以下8个主题色中选一个最贴合的颜色:" + chr(10) +
        "blue, green, purple, orange, cyan, pink, teal, yellow" + chr(10) +
        "严格只输出JSON: {\"text\": \"日志内容\", \"color\": \"颜色名\"}")
    raw = ds_ai(prompt)
    print("AI原始返回:", repr(raw[:500]))
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
    # fallback: JSON解析失败时用正则提取 text 字段
    tm = re.search(r'"text"\s*:\s*"(.*?)"', raw, re.S)
    if tm:
        try:
            return json.loads('"' + tm.group(1) + '"'), "blue"
        except Exception:
            pass
    # 最后兜底: 去掉可能的JSON壳
    t2 = re.sub(r'^\s*\{.*?"text"\s*:\s*"', "", raw, flags=re.S)
    t2 = re.sub(r'"\s*,\s*"color".*$', "", t2, flags=re.S)
    t2 = t2.strip().strip('"').strip()
    if t2 and len(t2) > 2:
        return t2, "blue"
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


def build_wordcloud(commits, out, hexc, width=630, height=350):
    """词云: PIL+wordcloud 透明 PNG(高质量)"""
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
        background_color="white", color_func=cf, prefer_horizontal=0.9,
        max_words=80, random_state=42, collocations=False).generate(seg)
    arr = np.array(wc.to_image())
    rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
    rgba[:, :, :3] = arr
    white = (arr[:, :, 0] > 235) & (arr[:, :, 1] > 235) & (arr[:, :, 2] > 235)
    rgba[white, 3] = 0
    rgba[~white, 3] = 255
    Image.fromarray(rgba, "RGBA").save(out, "PNG")


def _polar(cx, cy, r, deg):
    rad = math.radians(deg)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def build_pie_svg(commits, hexc, W=350, H=350):
    """饼图: SVG 矢量透明环形图 + 24小时制(24/6/12/18刻度) + 每2小时1扇区 + 颜色深浅按数量"""
    # 用北京时间分桶: 每2小时一个时段, 共12桶
    bj = timezone(timedelta(hours=8))
    N = 12
    buckets = [0] * N
    for c in commits:
        try:
            cd_dt = datetime.fromisoformat(c["_date"].replace("Z", "+00:00")).astimezone(bj)
            bh = cd_dt.hour
        except Exception:
            bh = (int(c["time"][:2]) + 8) % 24   # fallback: 假设 time 是 UTC
        buckets[min(bh // 2, N - 1)] += 1
    total = len(commits) or 1
    cx, cy, r, r2 = W / 2, H / 2, H * 0.42, H * 0.22
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
         % (W, H, W, H)]
    # 颜色深浅: 按提交数比例, 最多=最深(主题色), 为0=不画
    import colorsys
    hh, ll, ss = colorsys.rgb_to_hls(*(int(hexc[i:i+2], 16) / 255 for i in (1, 3, 5)))
    mx = max(buckets) or 1
    seg = 360.0 / N          # 每个时段固定角度(30°), 保证空时段留白
    all_d = []
    start = -90
    for i, v in enumerate(buckets):
        a0, a1 = start, start + seg
        if v > 0:
            x0, y0 = _polar(cx, cy, r, a0)
            x1, y1 = _polar(cx, cy, r, a1)
            x2, y2 = _polar(cx, cy, r2, a1)
            x3, y3 = _polar(cx, cy, r2, a0)
            large = 1 if (a1 - a0) > 180 else 0
            d = ("M %.1f %.1f A %.1f %.1f 0 %d 1 %.1f %.1f "
                 "L %.1f %.1f A %.1f %.1f 0 %d 0 %.1f %.1f Z"
                 % (x0, y0, r, r, large, x1, y1, x2, y2, r2, r2, large, x3, y3))
            # 深浅: 数量越多越深, 越少越浅
            t = v / mx
            rgb = colorsys.hls_to_rgb(hh, max(0.12, 1.0 - 0.9 * t), ss)
            c = "#%02x%02x%02x" % tuple(int(ch * 255) for ch in rgb)
            all_d.append((d, c))
        start = a1
    if all_d:
        # 外圆轮廓(主题色)
        s.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
                 'stroke-width="3" stroke-opacity="0.7"/>' % (cx, cy, r, hexc))
        # 内圆轮廓(主题色, 比外框细一倍, 透明度80%)
        s.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="%s" '
                 'stroke-width="1.5" stroke-opacity="0.8"/>' % (cx, cy, r2, hexc))
        # 扇区(无任何描边)
        s.append('<g>%s</g>' % "".join(
            '<path d="%s" fill="%s"/>' % (d, c)
            for d, c in all_d))
    # 24小时制刻度: 上24 右6 下12 左18
    for ang, label in ((-90, "24"), (0, "6"), (90, "12"), (180, "18")):
        lx, ly = _polar(cx, cy, r + H * 0.06, ang)
        s.append('<text x="%.1f" y="%.1f" fill="%s" font-size="17" font-weight="bold" '
                 'text-anchor="middle" font-family="sans-serif">%s</text>'
                 % (lx, ly + 6, hexc, label))
    # 中心数字
    s.append('<text x="%.1f" y="%d" fill="%s" font-size="34" font-weight="bold" '
             'text-anchor="middle" font-family="sans-serif">%d</text>'
             % (cx, int(cy - 2), hexc, total))
    s.append('<text x="%.1f" y="%d" fill="%s" font-size="14" font-weight="bold" '
             'text-anchor="middle" font-family="sans-serif">次提交</text>'
             % (cx, int(cy + 20), hexc))
    s.append('</svg>')
    return "".join(s)


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
    v = date_str.replace("-", "")
    lines.append('<table align="center"><tr><td>'
                 '<img src="wordcloud.png?v=%s" width="630" alt="提交词云"/></td><td>'
                 '<img src="pie.svg?v=%s" width="350" alt="提交时间分布"/></td></tr></table>'
                 % (v, v))
    lines.append("")
    lines.append("📚 [查看历史日志](./logs/)")
    return chr(10).join(lines)


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bj = timezone(timedelta(hours=8))
    today = (datetime.now(bj) - timedelta(days=1)).date().isoformat()   # 昨天(北京)
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
            build_wordcloud(commits, os.path.join(root, "wordcloud.png"), hexc)
            print("词云OK")
        except Exception as e:
            print("词云失败:", e)
        with open(os.path.join(root, "pie.svg"), "w", encoding="utf-8") as f:
            f.write(build_pie_svg(commits, hexc))
        print("饼图OK")
    content = build_log(today, commits, ai_text, hexc)
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)
    day_dir = os.path.join(root, "logs", today)
    os.makedirs(day_dir, exist_ok=True)
    os.makedirs(day_dir, exist_ok=True)
    if commits:
        import shutil
        if os.path.isfile(os.path.join(root, "wordcloud.png")):
            shutil.copy(os.path.join(root, "wordcloud.png"), os.path.join(day_dir, "wordcloud.png"))
        if os.path.isfile(os.path.join(root, "pie.svg")):
            shutil.copy(os.path.join(root, "pie.svg"), os.path.join(day_dir, "pie.svg"))
    with open(os.path.join(day_dir, "日志.md"), "w", encoding="utf-8") as f:
        f.write(content)
    print("完成: %d commits, 主题色 %s" % (len(commits), color_name))
