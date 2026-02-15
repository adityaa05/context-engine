import re
from dataclasses import dataclass


STOP_WORDS = {
    "youtube",
    "google",
    "search",
    "stackoverflow",
    "github",
    "docs",
    "documentation",
    "home",
    "watch",
    "video",
    "player",
}


def normalize(text: str) -> str:
    text = text.lower()

    # remove urls & separators
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[-–—|•·]", " ", text)

    # remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # collapse spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_keywords(title: str):
    title = normalize(title)

    words = [w for w in title.split() if len(w) > 2 and w not in STOP_WORDS]

    # keep top 4 words only (working memory constraint)
    return tuple(words[:4])


@dataclass(frozen=True)
class Anchor:
    app: str
    tokens: tuple

    def id(self):
        return f"{self.app}:{' '.join(self.tokens)}"


def extract_anchor(event):
    tokens = extract_keywords(event.title)

    if not tokens:
        tokens = (event.app.lower(),)

    return Anchor(event.app, tokens)
