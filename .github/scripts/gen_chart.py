"""生成每日提交量折线图 SVG (过去90天)"""
import json, os, sys, urllib.request
from datetime import date, timedelta

TOKEN = os.environ.get("GH_TOKEN", "")
AUTHOR = os.environ.get("GH_AUTHOR", "hong2301")
DAYS = 90

def api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "chart-gen",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def daily_commits():
    counts = {}
    since = (date.today() - timedelta(days=DAYS)).isoformat()
    page = 1
    while True:
        url = (f"https://api.github.com/search/commits?q=author:{AUTHOR}"
               f"+committer-date:>{since}&per_page=100&page={page}")
        data = api(url)
        items = data.get("items", [])
        for it in items:
            d = it["commit"]["committer"]["date"][:10]
            counts[d] = counts.get(d, 0) + 1
        if len(items) < 100 or page >= 10:
            break
        page += 1
    full = {}
    for i in range(DAYS):
        d = (date.today() - timedelta(days=DAYS - 1 - i)).isoformat()
        full[d] = counts.get(d, 0)
    return full

def make_svg(daily):
    W, H = 820, 300
    PL, PR, PT, PB = 44, 20, 24, 44
    pw, ph = W - PL - PR, H - PT - PB
    maxv = max(daily.values()) or 1
    n = len(daily)
    pts = []
    for i, (d, v) in enumerate(daily.items()):
        x = PL + i * pw / (n - 1)
        y = PT + ph - (v / maxv) * ph
        pts.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{PL:.1f},{PT+ph:.1f} " + poly + f" {W-PR:.1f},{PT+ph:.1f}"

    dates = list(daily.keys())
    labels = [dates[0], dates[len(dates)//2], dates[-1]]
    lx = [PL, PL + pw/2, W - PR]

    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    s.append('<rect width="100%" height="100%" fill="#0d1117"/>')
    # 网格线
    for g in range(5):
        gy = PT + ph * g / 4
        s.append(f'<line x1="{PL}" y1="{gy:.0f}" x2="{W-PR}" y2="{gy:.0f}" stroke="#21262d" stroke-width="1"/>')
    # 面积 + 折线
    s.append(f'<polygon points="{area}" fill="rgba(46,160,67,0.25)"/>')
    s.append(f'<polyline points="{poly}" fill="none" stroke="#2ea043" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
    # 点
    for x, y in pts:
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="#56d364"/>')
    # 标签
    for lab, x in zip(labels, lx):
        s.append(f'<text x="{x:.0f}" y="{H-PB+24}" fill="#8b949e" font-size="13" text-anchor="middle">{lab}</text>')
    s.append(f'<text x="{PL}" y="{PT-6}" fill="#8b949e" font-size="13">每日提交数 (近{DAYS}天)</text>')
    s.append(f'<text x="{W-PR}" y="{PT-6}" fill="#8b949e" font-size="13" text-anchor="end">峰值 {maxv}</text>')
    s.append('</svg>')
    return "".join(s)

if __name__ == "__main__":
    daily = daily_commits()
    out = make_svg(daily)
    path = os.path.join(os.path.dirname(__file__), "..", "..", "chart.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    total = sum(daily.values())
    print(f"OK: {total} commits in {DAYS} days -> chart.svg")
