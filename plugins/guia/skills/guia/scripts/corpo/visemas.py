"""Visemas (formas de boca) a partir do texto e dos tempos de cada palavra.

Aproximação ortográfica para pt-PT — sem dependências, corre dentro e fora do Blender.
Visemas: X (repouso), MBP, A, E, O, U, FV, C (consoante, boca entreaberta).
"""
import re
import unicodedata

VISEMAS = ("X", "MBP", "A", "E", "O", "U", "FV", "C")
_VOGAL = {"a": "A", "e": "E", "i": "E", "y": "E", "o": "O", "u": "U"}
_PESO = {"A": 1.0, "E": 0.9, "O": 1.0, "U": 0.8, "MBP": 0.7, "FV": 0.7, "C": 0.55}


def _base(ch):
    return unicodedata.normalize("NFD", ch)[0]


def fonemas(palavra):
    """Lista de (visema, peso) para uma palavra escrita."""
    w = re.sub(r"[^\w]", "", palavra.lower())
    out = []
    i = 0
    while i < len(w):
        c, b = w[i], _base(w[i])
        dupla = w[i:i + 2]
        if dupla in ("ch", "nh", "lh", "ss", "rr"):
            out.append("C"); i += 2; continue
        if dupla in ("qu", "gu") and i + 2 < len(w) and _base(w[i + 2]) in "ei":
            out.append("C"); i += 2; continue
        if b == "h":
            i += 1; continue
        if b in "mn" and (i == len(w) - 1 or (i + 1 < len(w) and _base(w[i + 1]) not in "aeiouy")) \
                and out and out[-1] in ("A", "E", "O", "U"):
            i += 1; continue  # nasal depois de vogal ("com", "conta"): não fecha a boca
        if b in _VOGAL:
            v = _VOGAL[b]
            final = i == len(w) - 1 or (i == len(w) - 2 and w[-1] == "s")
            if final and b == "o" and len(w) > 2:
                v = "U"  # "-o" final reduz-se a [u] em pt-PT
            out.append(v); i += 1; continue
        if b in "mbp":
            out.append("MBP")
        elif b in "fv":
            out.append("FV")
        elif c.isalpha():
            out.append("C")
        i += 1
    return [(v, _PESO[v]) for v in out]


def segmentos(palavras, deslocamento=0.0):
    """(inicio, fim, visema) em segundos da cena, repartindo cada palavra pelos fonemas."""
    segs = []
    for p in palavras:
        f = fonemas(p["texto"])
        if not f:
            continue
        t0, t1 = p["inicio"] + deslocamento, p["fim"] + deslocamento
        total = sum(w for _, w in f)
        t = t0
        for v, w in f:
            d = (t1 - t0) * w / total
            segs.append((t, t + d, v))
            t += d
    return segs


def por_frame(palavras, n_frames, fps, deslocamento=0.0):
    """Um visema por frame (amostrado no centro do frame), com frames isolados alisados."""
    segs = segmentos(palavras, deslocamento)
    out = []
    j = 0
    for f in range(n_frames):
        t = (f + 0.5) / fps
        while j < len(segs) and segs[j][1] <= t:
            j += 1
        out.append(segs[j][2] if j < len(segs) and segs[j][0] <= t else "X")
    for f in range(1, n_frames - 1):  # tira tremores de 1 frame, mas mantém os fechos (MBP)
        if out[f] != out[f - 1] and out[f - 1] == out[f + 1] and out[f] != "MBP":
            out[f] = out[f - 1]
    return out
