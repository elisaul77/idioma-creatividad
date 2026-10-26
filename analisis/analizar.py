"""Análisis reproducible de la ronda: lee data/votos.csv + data/svg y escribe data/stats.json.

Uso: python3 analisis/analizar.py
Solo biblioteca estándar. Descarta votos de menos de 500 ms (toques dobles o al azar).
"""
import csv, json, random, re
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IDIOMAS = {"es": "Español", "en": "Inglés", "zh": "Chino", "ja": "Japonés", "ar": "Árabe",
           "ru": "Ruso", "de": "Alemán", "hi": "Hindi", "sw": "Suajili", "qu": "Quechua"}
L = list(IDIOMAS)
MIN_MS = 500
BOOT = 1000


def bradley_terry(pares, iters=200):
    w = {i: 1.0 for i in L}
    vict = Counter(g for g, _ in pares)
    for _ in range(iters):
        den = defaultdict(float)
        for g, p in pares:
            s = 1.0 / (w[g] + w[p])
            den[g] += s
            den[p] += s
        # prior: medio triunfo y media derrota contra un rival virtual de fuerza 1
        w = {i: (vict[i] + 0.5) / (den[i] + 1.0 / (w[i] + 1.0)) for i in L}
        gm = 1.0
        for x in w.values():
            gm *= x
        gm **= 1 / len(w)
        w = {i: x / gm for i, x in w.items()}
    return w


def ranking(pares, semilla=7):
    base = bradley_terry(pares)
    rng = random.Random(semilla)
    bs = defaultdict(list)
    for _ in range(BOOT):
        for l, x in bradley_terry([rng.choice(pares) for _ in pares], 60).items():
            bs[l].append(x)
    out = []
    for l in L:
        s = sorted(bs[l])
        lo, hi = s[int(BOOT * .025)], s[int(BOOT * .975) - 1]
        t = sum(1 for x in pares if l in x)
        g = sum(1 for a, _ in pares if a == l)
        out.append(dict(lang=l, nombre=IDIOMAS[l], fuerza=round(base[l], 3), ic=[round(lo, 3), round(hi, 3)],
                        victorias=g, duelos=t, pct=round(100 * g / t, 1) if t else None,
                        significativo=lo > 1 or hi < 1))
    out.sort(key=lambda r: -r["fuerza"])
    return out


def spearman(a, b):
    def rangos(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for k, i in enumerate(o):
            r[i] = k
        return r
    ra, rb = rangos(a), rangos(b)
    n = len(a)
    return round(1 - 6 * sum((x - y) ** 2 for x, y in zip(ra, rb)) / (n * (n * n - 1)), 2)


def complejidad(nombre):
    t = (RAIZ / "data" / "svg" / nombre).read_text(encoding="utf-8")
    return len(re.findall(r"<(?!/|svg|defs|stop|\?)[a-zA-Z]+", t))


def main():
    filas = [r for r in csv.DictReader(open(RAIZ / "data" / "votos.csv"))]
    total = len(filas)
    filas = [r for r in filas if int(r["ms"]) >= MIN_MS]
    lang = lambda f: f.split("_")[1]
    evals = sorted({(r["evaluador"], int(r["edad"])) for r in filas})

    def pares(f):
        return [(lang(r["ganador"]), lang(r["perdedor"])) for r in filas if f(r)]

    stats = {"votos_totales": total, "votos_validos": len(filas), "min_ms": MIN_MS,
             "evaluadores": [{"id": e, "edad": a, "votos": sum(1 for r in filas if r["evaluador"] == e)}
                             for e, a in evals]}
    stats["grupos"] = {
        "todos": ranking(pares(lambda r: True)),
        "ninos": ranking(pares(lambda r: int(r["edad"]) <= 12)),
        "adultos": ranking(pares(lambda r: int(r["edad"]) >= 18)),
    }
    stats["por_evaluador"] = {e: ranking(pares(lambda r, e=e: r["evaluador"] == e)) for e, _ in evals}

    # acuerdo entre evaluadores: Spearman de las fuerzas por idioma
    fz = {e: {x["lang"]: x["fuerza"] for x in stats["por_evaluador"][e]} for e, _ in evals}
    ids = [e for e, _ in evals]
    stats["acuerdo_spearman"] = {f"{a}-{b}": spearman([fz[a][l] for l in L], [fz[b][l] for l in L])
                                 for i, a in enumerate(ids) for b in ids[i + 1:]}

    # ganador por prompt
    por_prompt = {}
    for pid in sorted({r["ganador"].split("_")[2] for r in filas}):
        w, t = Counter(), Counter()
        for r in filas:
            if f"_{pid}_" in r["ganador"]:
                w[lang(r["ganador"])] += 1
                t[lang(r["ganador"])] += 1
                t[lang(r["perdedor"])] += 1
        orden = sorted(t, key=lambda l: -w[l] / t[l])
        por_prompt[pid] = {"mejor": orden[0], "pct_mejor": round(100 * w[orden[0]] / t[orden[0]]),
                           "peor": orden[-1], "pct_peor": round(100 * w[orden[-1]] / t[orden[-1]])}
    stats["por_prompt"] = por_prompt

    # complejidad del dibujo (nº de elementos SVG) por idioma y si cada evaluador premia lo complejo
    svgs = sorted(p.name for p in (RAIZ / "data" / "svg").glob("*.svg"))
    cx = {s: complejidad(s) for s in svgs}
    stats["elementos_por_idioma"] = {l: round(sum(cx[s] for s in svgs if lang(s) == l) /
                                          sum(1 for s in svgs if lang(s) == l), 1) for l in L}
    gana_complejo = {}
    for e, a in evals:
        dif = [(cx[r["ganador"]] > cx[r["perdedor"]]) for r in filas
               if r["evaluador"] == e and cx[r["ganador"]] != cx[r["perdedor"]]]
        gana_complejo[e] = round(100 * sum(dif) / len(dif), 1)
    stats["pct_gana_el_mas_complejo"] = gana_complejo
    el = [stats["elementos_por_idioma"][l] for l in L]
    stats["spearman_complejidad_vs_fuerza"] = {e: spearman(el, [fz[e][l] for l in L]) for e in ids}

    gen = [json.loads(l) for l in open(RAIZ / "data" / "generacion.jsonl")]
    stats["generacion"] = {"svg": len(gen), "costo_usd": round(sum(g["costo"] or 0 for g in gen), 3),
                           "tokens_salida_por_idioma": {l: round(sum(g["tokens"] for g in gen if g["lang"] == l) /
                                                            sum(1 for g in gen if g["lang"] == l)) for l in L}}
    (RAIZ / "data" / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    print(json.dumps({k: stats[k] for k in ("votos_validos", "evaluadores", "acuerdo_spearman",
                                            "elementos_por_idioma", "pct_gana_el_mas_complejo")},
                     ensure_ascii=False))
    for g, t in stats["grupos"].items():
        print(g, [(x["lang"], x["fuerza"], x["pct"], "*" if x["significativo"] else "") for x in t])
    for e, t in stats["por_evaluador"].items():
        print(e, [(x["lang"], x["pct"], "*" if x["significativo"] else "") for x in t])
    print(stats["generacion"]["tokens_salida_por_idioma"])


if __name__ == "__main__":
    main()
