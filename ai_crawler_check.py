#!/usr/bin/env python3
"""ai-crawler-check — is your site visible to AI search crawlers?

Checks a site's robots.txt (and the site itself) for the five crawlers
that decide whether you exist in ChatGPT, Claude, Perplexity, Google AI,
and the Common Crawl datasets most models train on.

Usage:
    python ai_crawler_check.py example.com
    python ai_crawler_check.py https://example.com --json

Zero dependencies — Python 3.8+ standard library only.
MIT License.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from urllib.robotparser import RobotFileParser

AI_BOTS = {
    "GPTBot": "OpenAI / ChatGPT search & training",
    "ClaudeBot": "Anthropic / Claude",
    "PerplexityBot": "Perplexity AI",
    "Google-Extended": "Google AI (Gemini grounding & training)",
    "CCBot": "Common Crawl (feeds most open datasets)",
}

# A regular browser UA for the edge-block probe, and each bot's UA for
# the per-bot probe. Cloudflare-style edge blocking returns 403 to bot
# UAs *before* robots.txt is ever consulted — robots.txt alone can't
# detect it.
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ai-crawler-check/1.0"
TIMEOUT = 10


def fetch(url: str, user_agent: str) -> tuple[int, str]:
    """Return (status_code, body). Never raises; errors map to (0, reason)."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(65536).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def normalize(site: str) -> str:
    if not site.startswith(("http://", "https://")):
        site = "https://" + site
    return site.rstrip("/")


def check_site(site: str) -> dict:
    base = normalize(site)
    result = {"site": base, "robots_txt": None, "llms_txt": False,
              "bots": {}, "edge_block_suspected": False, "notes": []}

    # 1. robots.txt — parse once, evaluate per bot
    robots_url = f"{base}/robots.txt"
    status, body = fetch(robots_url, BROWSER_UA)
    parser = None
    if status == 200:
        result["robots_txt"] = "found"
        parser = RobotFileParser()
        parser.parse(body.splitlines())
    elif status == 0:
        result["robots_txt"] = "unreachable"
        result["notes"].append(f"robots.txt unreachable: {body}")
    else:
        # No robots.txt (404 etc.) = nothing is blocked by it
        result["robots_txt"] = f"absent (HTTP {status})"

    for bot in AI_BOTS:
        verdict = {"robots_allowed": True, "note": ""}
        if parser is not None:
            verdict["robots_allowed"] = parser.can_fetch(bot, base + "/")
        result["bots"][bot] = verdict

    # 2. Edge-block probe: fetch homepage as browser vs as GPTBot.
    #    Browser 200 + bot 403 => something above the app (Cloudflare
    #    "Block AI Bots", WAF rule) is rejecting bots at the edge.
    b_status, _ = fetch(base + "/", BROWSER_UA)
    if b_status == 200:
        probe_status, _ = fetch(base + "/", "GPTBot/1.0 (+https://openai.com/gptbot)")
        if probe_status in (401, 403):
            result["edge_block_suspected"] = True
            result["notes"].append(
                "Homepage returns 200 to a browser but "
                f"{probe_status} to a GPTBot user-agent -- edge-level bot "
                "blocking (e.g. Cloudflare 'Block AI Bots') is likely ON. "
                "robots.txt can look permissive while the edge blocks everything.")
    elif b_status == 0:
        result["notes"].append("Homepage unreachable -- edge probe skipped.")

    # 3. llms.txt presence (bonus check). Status 200 alone is not enough:
    #    SPA sites often return their HTML shell with 200 for ANY path
    #    (soft-404). Require the body to actually look like a text file.
    l_status, l_body = fetch(base + "/llms.txt", BROWSER_UA)
    looks_html = l_body.lstrip()[:15].lower().startswith(("<!doctype", "<html"))
    result["llms_txt"] = l_status == 200 and bool(l_body.strip()) and not looks_html

    return result


def render(result: dict) -> int:
    """Pretty-print result; return process exit code (0 ok, 1 issues found).

    ASCII-only output on purpose: Windows consoles often run legacy code
    pages (cp1251/cp437) where unicode check marks crash print().
    """
    issues = 0
    print(f"\n  AI crawler visibility -- {result['site']}")
    print(f"  robots.txt: {result['robots_txt']}\n")
    for bot, verdict in result["bots"].items():
        ok = verdict["robots_allowed"]
        mark = "OK" if ok else "BLOCKED"
        if not ok:
            issues += 1
        print(f"  [{mark:>7}] {bot:<16} {AI_BOTS[bot]}")
    print()
    if result["edge_block_suspected"]:
        issues += 1
        print("  [WARNING] EDGE BLOCKING SUSPECTED -- see note below.")
    print(f"  [{'OK' if result['llms_txt'] else '--':>2}] llms.txt "
          f"{'found' if result['llms_txt'] else 'not found (optional, but cheap leverage)'}")
    for note in result["notes"]:
        print(f"\n  note: {note}")
    if issues == 0:
        print("\n  All five AI crawlers can reach this site.\n")
    else:
        print(f"\n  {issues} issue(s) found -- this site is partially or fully"
              " invisible to AI search.\n")
    return 1 if issues else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("site", help="domain or URL to check (e.g. example.com)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if not args.json:
        print(f"  checking {args.site} ...", flush=True)
    result = check_site(args.site)
    if args.json:
        print(json.dumps(result, indent=2))
        blocked = any(not v["robots_allowed"] for v in result["bots"].values())
        return 1 if (blocked or result["edge_block_suspected"]) else 0
    return render(result)


if __name__ == "__main__":
    sys.exit(main())
