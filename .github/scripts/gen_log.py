"""生成每日开发日志: GitHub提交数据 -> DeepSeek AI总结 -> README + 存档logs/"""
import json, os, urllib.request
from datetime import date, datetime

GH_TOKEN = os.environ.get("GH_TOKEN", "")
DS_TOKEN = os.environ.get("DEEPSEEK_TOKEN", "")
AUTHOR = os.environ.get("GH_AUTHOR", "hong2301")

def gh_api(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "log-gen",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def ds_ai(text):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": text}],
        "stream": False,
        "max_tokens": 200,
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

def build_log(date_str, commits, ai_text):
    lines = [f"# 📝 每日开发日志", "", f"## 今日日志 ({date_str})", ""]
    if ai_text:
        lines.append(ai_text.strip())
        lines.append("")
    if not commits:
        lines.append("*(今天没有提交记录，休息了一下)*")
    else:
        lines.append("| 时间 | 仓库 | 提交 |")
        lines.append("|---|---|---|")
        for c in commits:
            lines.append(f"| {c['time']} | {c['repo']} | {c['msg']} |")
    lines.append("")
    lines.append("📚 [查看历史日志](./logs/)")
    return "\n".join(lines)

if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    today = date.today().isoformat()
    commits = today_commits()
    ai_text = None
    if commits and DS_TOKEN:
        try:
            desc = "\n".join(
                f"- {c['time']} [{c['repo']}] {c['msg']}" for c in commits)
            ai_text = ds_ai(
                "以下是我今天(GitHub: hong2301)的所有代码提交记录:\n" + desc +
                "\n\n请用中文写一段简短的第一人称开发日志(80字内, 像程序员日记, 自然叙述今天做了什么, 不要列清单)")
            print("AI总结:", ai_text)
        except Exception as e:
            print("AI调用失败:", e)
    content = build_log(today, commits, ai_text)
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)
    os.makedirs(os.path.join(root, "logs"), exist_ok=True)
    with open(os.path.join(root, "logs", today + ".md"), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK: {len(commits)} commits -> README.md + logs/{today}.md")
