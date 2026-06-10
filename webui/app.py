"""Gradio web app for wiki-random, for hosting on Hugging Face Spaces.

Hugging Face Spaces give the Python process real outbound internet, so the live
Wikipedia lookup works server-side here (unlike LLM code sandboxes, which are
network-isolated). Deploy by creating a Gradio Space from this folder; the
engine is pulled from GitHub via requirements.txt.
"""

import json
import urllib.parse
import urllib.request

import gradio as gr

from wiki_random.oracle import oracle, format_ritual, format_verify

UA = "wiki-random-space/1.0 (https://github.com/potncoffee/wiki-random)"


def _summary(pageid):
    q = urllib.parse.urlencode({
        "action": "query", "pageids": str(pageid), "prop": "extracts",
        "exintro": "1", "explaintext": "1", "format": "json",
    })
    try:
        req = urllib.request.Request(
            "https://en.wikipedia.org/w/api.php?" + q, headers={"User-Agent": UA})
        d = json.load(urllib.request.urlopen(req, timeout=20))
        page = next(iter(d["query"]["pages"].values()))
        return page.get("extract", "")
    except Exception:
        return ""


def consult(seed_str, show_verify):
    seed_str = (seed_str or "").strip()
    try:
        seed = int(seed_str)
    except ValueError:
        return "Seed must be an integer.", ""
    result = oracle(seed)
    math_text = format_ritual(result)
    if show_verify:
        math_text += "\n\n" + format_verify(result)
    art = result["article"]
    summ = _summary(art["pageid"])
    md = f"### [{art['title']}]({art['url']})\n\n"
    if summ:
        md += summ + "\n\n"
    md += f"`{art['url']}`"
    return math_text, md


with gr.Blocks(title="wiki-random", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# wiki·random\n"
        "Turn any seed number into a real Wikipedia article through a "
        "deterministic, fully auditable modular-hash pipeline."
    )
    with gr.Row():
        seed = gr.Textbox(label="Input (seed) — any integer, any size", value="1729", scale=4)
        verify = gr.Checkbox(label="show paste-and-run proof", value=False, scale=1)
    go = gr.Button("Consult", variant="primary")
    math_out = gr.Code(label="The math", language=None)
    article_out = gr.Markdown(label="The article")
    go.click(consult, inputs=[seed, verify], outputs=[math_out, article_out])
    seed.submit(consult, inputs=[seed, verify], outputs=[math_out, article_out])

if __name__ == "__main__":
    demo.launch()
