#!/usr/bin/env bash
# Git-scraping snapshotter (pattern: simonw/git-scraper-template).
# Fetches each guidance source, normalizes to stable text, writes to
# snapshots/. The workflow commits ONLY when content changed, so the git
# history of snapshots/ IS the changelog.
set -uo pipefail

UA="seo-guidance-watch/1.0 (+https://github.com/Second-Spring-Design/seo-guidance-watch)"
mkdir -p snapshots

fetch() { curl -fsSL --retry 3 --retry-delay 5 -A "$UA" "$1"; }

# HTML → readable text (drops markup/script noise; keeps link targets).
to_text() { python3 -m html2text --ignore-images --body-width=0; }

ok=0; fail=0
grab() { # grab <name> <url> <mode: text|raw|hash>
  local name="$1" url="$2" mode="$3" body
  if ! body="$(fetch "$url")"; then
    echo "FAIL: $name ($url)"; fail=$((fail+1)); return
  fi
  case "$mode" in
    text) printf '%s' "$body" | to_text > "snapshots/$name.txt" ;;
    raw)  printf '%s' "$body" > "snapshots/$name.txt" ;;
    hash) printf '%s' "$body" | sha256sum | cut -d' ' -f1 > "snapshots/$name.sha256" ;;
  esac
  ok=$((ok+1))
}

# --- Google Search Central (content: CC BY 4.0, see README attribution) ---
grab google-search-updates      "https://developers.google.com/search/updates"                                    text
grab google-sd-article          "https://developers.google.com/search/docs/appearance/structured-data/article"    text
grab google-sd-faq              "https://developers.google.com/search/docs/appearance/structured-data/faqpage"    text
grab google-sd-intro            "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data" text

# --- schema.org: track the vocabulary via release feed + content hash ---
grab schemaorg-releases         "https://github.com/schemaorg/schemaorg/releases.atom"                            raw
grab schemaorg-vocab            "https://schema.org/version/latest/schemaorg-current-https.jsonld"                hash

# --- Bing Webmaster blog (RSS) ---
grab bing-blog                  "https://blogs.bing.com/feed"                                                     raw

# --- AI/answer-engine crawler policies ---
grab openai-bots                "https://developers.openai.com/api/docs/bots"                                     text
grab perplexity-crawlers        "https://docs.perplexity.ai/docs/resources/perplexity-crawlers.md"                raw

# Strip volatile RSS/Atom fields that churn without content changes.
for f in snapshots/bing-blog.txt snapshots/schemaorg-releases.txt; do
  [ -f "$f" ] && sed -i -E 's#<(lastBuildDate|pubDate|updated)>[^<]*</\1>##g' "$f"
done

echo "done: $ok fetched, $fail failed"
# Never hard-fail the workflow on a single flaky source; only fail if
# EVERYTHING broke (network down / repo misconfig).
[ "$ok" -gt 0 ]
