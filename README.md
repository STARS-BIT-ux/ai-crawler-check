# ai-crawler-check

**Is your website visible to AI search?** One command checks whether the
five crawlers that matter — GPTBot (ChatGPT), ClaudeBot (Claude),
PerplexityBot, Google-Extended (Gemini), and CCBot (Common Crawl) — can
actually reach your site.

```
$ python ai_crawler_check.py yoursite.com

  AI crawler visibility -- https://yoursite.com
  robots.txt: found

  [     OK] GPTBot           OpenAI / ChatGPT search & training
  [BLOCKED] ClaudeBot        Anthropic / Claude
  [     OK] PerplexityBot    Perplexity AI
  [     OK] Google-Extended  Google AI (Gemini grounding & training)
  [BLOCKED] CCBot            Common Crawl (feeds most open datasets)

  [--] llms.txt not found (optional, but cheap leverage)

  2 issue(s) found -- this site is partially or fully invisible to AI search.
```

## Why this matters

When someone asks ChatGPT or Perplexity a question your site answers,
you only get cited if the crawler could read your content in the first
place. One `Disallow` line — often left over from an old "block all
bots" rule or a default theme setting — makes everything else
irrelevant. Most sites never check.

## What it checks

1. **robots.txt rules** for each of the five AI crawlers, evaluated with
   Python's standard robots.txt parser (not naive string matching — real
   `User-agent` group resolution).
2. **Edge-level blocking** — the check robots.txt alone can't do. It
   fetches your homepage twice: once as a browser, once with a GPTBot
   user-agent. Browser `200` + bot `403` means something *above* your
   application (Cloudflare "Block AI Bots", a WAF rule) rejects crawlers
   before robots.txt is ever consulted. Your robots.txt can look
   perfectly permissive while the edge blocks everything.
3. **llms.txt presence** — the emerging convention for giving AI models
   a standardized map of your site.

## Install / run

No install, no dependencies — Python 3.8+ standard library only:

```bash
python ai_crawler_check.py example.com          # human-readable
python ai_crawler_check.py example.com --json   # machine-readable
```

Exit code `0` = all clear, `1` = at least one crawler blocked (usable in
CI — fail a deploy if someone's robots.txt change accidentally blocks
AI search).

## Limitations (honest ones)

- The edge probe sends a GPTBot *user-agent string*, not a request from
  OpenAI's actual IP ranges. Sites that verify crawler IPs (rare) may
  behave differently for the real bot.
- A `403` to the bot UA is strong evidence of edge blocking, but a
  passing probe doesn't *guarantee* the real crawler gets through.
- This checks reachability, not citability — being crawlable is the
  gate, not the whole game.

## Fixing what it finds

Ready-to-paste robots.txt snippets for WordPress, Shopify, Webflow,
custom/Nginx sites, and the Cloudflare fix are in the
[llms.txt + AI Crawler Setup Kit](https://rentry.co/nexus-catalog) — along with a
fill-in llms.txt template. The full 30-point AI visibility checklist is
[here](https://rentry.co/nexus-catalog) (full catalog, crypto checkout, instant delivery).

## License

MIT
