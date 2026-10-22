"""Kuratierte Fallen für die Ethik-Fragen (items_candidates.json, src …ethik-kodex). Schlüssel = eindeutiger Teilstring des Fragetexts, damit die Zuordnung von der Kandidaten-ID unabhängig bleibt."""
STEMS = {
    "brother-in-law": "eth act",
    "falsifying concrete": "eth esc",
    "green status to executives": "eth act",
    "all-expenses-paid": "eth act",
    "senior developer jokes": "eth esc",
    "consultancy brings in": "eth role",
    "medical device software": "eth act",
    "internal candidate who is a close friend": "eth role",
    "understated cloud costs": "eth act",
    "unconfirmed rumors": "eth esc",
    "AI assistant to rank": "eth act",
    "junior engineer": "eth role",
}


def resolve(cands):
    """-> (ethics candidate items, {id: 'eth x'}); jede Kandidatenfrage mit src …ethik-kodex muss genau einen Treffer haben."""
    items, cur = [], {}
    for c in cands:
        if not str(c.get("src", "")).endswith("ethik-kodex"):
            continue
        hit = [t for k, t in STEMS.items() if k in c.get("q", "")]
        if len(hit) != 1:
            raise ValueError(f"{c.get('id')}: Ethik-Frage ohne eindeutige Fallen-Zuordnung ({len(hit)} Treffer)")
        items.append(c)
        cur[c["id"]] = hit[0]
    return items, cur
