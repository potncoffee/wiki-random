---
title: wiki-random
emoji: 🎲
colorFrom: yellow
colorTo: gray
sdk: gradio
app_file: app.py
pinned: false
license: mit
---

# wiki-random web UI builds

Two ways to run wiki-random in a browser, plus an honest note on what does NOT
work.

## The honest answer about "drop a zip into a web UI"

The tool's last step makes a **live call to the Wikipedia API**. An LLM **code
sandbox** is network-isolated, so a zip whose script tries to do the whole job
in the sandbox cannot reach Wikipedia and the lookup fails. The fix is to not do
the whole job in the sandbox: in ChatGPT and Claude.ai the assistant has a
*separate* web-browsing tool that does have internet, so it runs the math in the
sandbox and does the Wikipedia lookups through its browser. That split is what
[`../AI_START_HERE.md`](../AI_START_HERE.md) instructs.

| Target | Upload a zip? | Code sandbox has internet? | wiki-random works? |
|--------|---------------|----------------------------|--------------------|
| Open `index.html` in a browser | n/a (just open the file) | yes (your browser) | **Yes** |
| Hugging Face Spaces (Gradio) | yes | yes | **Yes** |
| Google Colab / Replit | yes / notebook | yes | Yes (with a run step) |
| Claude.ai (assistant + browsing) | yes | no, but its browser does | **Yes, via `AI_START_HERE.md`** |
| ChatGPT (assistant + browsing) | yes | no, but its browser does | **Yes, via `AI_START_HERE.md`** |
| A script run *only* in a code sandbox | yes | **no** | No (the walk cannot fetch) |
| ChatGPT Canvas (Pyodide) | code only | CORS-gated | Unreliable |

So "drop a zip into ChatGPT/Claude and it works" *is* possible, but only because
the assistant browses on the sandbox's behalf, not because the sandbox itself
reaches the network. The browser and Spaces paths below need no such split.

## 1. `index.html`: zero install, runs in the browser (recommended)

A single self-contained file. The entire oracle is reimplemented in JavaScript
(`BigInt` handles the 61-bit modular arithmetic exactly), and the Wikipedia
lookup happens **client-side** using the MediaWiki API's anonymous CORS support
(`origin=*`). No server, no account, no build step.

- **Just open it:** download `index.html` and double-click it. It loads a
  self-test badge that proves the JavaScript math matches the Python engine.
- **Or host it free:** drop `index.html` into a GitHub Pages site (or any static
  host) and share the URL. (If `file://` access is blocked by your browser's CORS
  policy, the hosted version always works.)

This is the closest thing to "download it from GitHub and it just works."

## 2. Hugging Face Spaces: a hosted, shareable web app

`app.py` is a Gradio interface. Hugging Face Spaces give the Python process real
outbound internet, so the live lookup works server-side.

To deploy:

1. Create a new **Gradio** Space on Hugging Face.
2. Upload the three files in this folder (`app.py`, `requirements.txt`, this
   `README.md`, whose frontmatter configures the Space).
3. The Space builds, installs the engine from GitHub, and serves a public URL.

`requirements.txt` pulls the engine straight from the GitHub repo, so the Space
always tracks the canonical source.

## What you get either way

The same labeled, auditable output as the CLI: the constants (modulus,
multipliers, increments), the worked computation, the resolved article with its
`?curid=` link and summary, and an optional paste-and-run proof snippet.
Disambiguation landings are flagged as such.
