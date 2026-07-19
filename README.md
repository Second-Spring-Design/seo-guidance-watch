# seo-guidance-watch

Zero-cost watcher for changes to the SEO/AEO guidance our content pipeline
depends on. Uses the [git-scraping](https://simonwillison.net/2020/Oct/9/git-scraping/)
pattern: a daily GitHub Action snapshots each source into `snapshots/` and
commits **only when the content changed** — so `git log -- snapshots/` is a
free, diffable changelog of the SEO landscape.

## Watched sources

| Snapshot | Source | Why |
|---|---|---|
| `google-search-updates` | [Search Central updates feed](https://developers.google.com/search/updates) | Canonical log of ranking/feature/policy changes |
| `google-sd-article` / `google-sd-faq` / `google-sd-intro` | Google structured-data docs | We emit Article + FAQPage JSON-LD |
| `schemaorg-releases` / `schemaorg-vocab` | schema.org releases + vocabulary hash | Vocabulary changes behind our JSON-LD |
| `bing-blog` | [Bing Webmaster blog RSS](https://blogs.bing.com/feed) | Bing/Copilot answer-engine guidance |
| `openai-bots` | [OpenAI crawler docs](https://developers.openai.com/api/docs/bots) | GPTBot/OAI-SearchBot policy (AEO) |
| `perplexity-crawlers` | [Perplexity crawler docs](https://docs.perplexity.ai/docs/resources/perplexity-crawlers.md) | PerplexityBot policy (AEO) |

## How it works

1. **`scrape.sh`** (daily cron, `.github/workflows/scrape.yml`): curl each
   source, normalize HTML → text (`html2text`), strip volatile RSS fields,
   write to `snapshots/`. A single flaky source never fails the run.
2. **Commit-on-change**: no diff → no commit → zero noise.
3. **LLM triage** (`triage.py`, second job, only runs on change): pipes the
   diff to a small model, classifies **actionable / notable / noise**, and
   files a GitHub issue for anything non-noise. **Degrades gracefully** —
   without an `ANTHROPIC_API_KEY` repo secret it files a plain
   "review manually" issue instead.

## Setup

- Nothing required for the watcher itself (public repo → Actions minutes are
  free; ~15 min/month).
- Optional: add `ANTHROPIC_API_KEY` in **Settings → Secrets and variables →
  Actions** to enable LLM triage (haiku-class model, ~$0.01/triage).
- Watch the repo (Issues) to get notified of guidance changes.

## Attribution

Google Search Central documentation content is used under
[CC BY 4.0](https://developers.google.com/terms/site-policies). Snapshots are
stored solely for change detection. Other sources are fetched from their
public pages/feeds with a descriptive User-Agent and daily (not aggressive)
frequency.
