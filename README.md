# Boxing Daily Digest

A small news digest site hosted on GitHub Pages that shows the latest boxing headlines.

- `fetch_news.py` reads 5 public RSS/Atom feeds (BBC Sport, The Guardian, ESPN via Google News, Sky Sports, Bad Left Hook),
  making one request per feed, and saves the headline, source, link and publish time to `data.json`.
  It uses only the Python standard library.
- `.github/workflows/update-news.yml` runs the script every day at 11:17 UTC. It can also be started with the
  **Run workflow** button on the Actions tab. It commits `data.json` back to the repo when the headlines change.
- `index.html` reads `data.json` and shows the headlines as cards, newest first.

If a feed fails, the page shows a short message and keeps that source's earlier headlines.
ESPN's own RSS feed blocks automated requests (it returns an empty response), so ESPN stories come from a
Google News search limited to espn.com. Those links open through Google News before reaching ESPN.

To add or remove feeds, edit the `FEEDS` list at the top of `fetch_news.py`.

Run it locally with `python fetch_news.py`, then serve the folder (for example `python -m http.server`)
and open http://localhost:8000.
