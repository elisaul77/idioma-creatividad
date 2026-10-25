"""Plataforma de evaluación ciega: duelos de dos SVG del mismo prompt en idiomas distintos."""
import random, re, sqlite3, time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DATA = Path("/data")
SVG_DIR = DATA / "svg"
DB = DATA / "votos.db"
STATIC = Path(__file__).parent / "static"
NOMBRE = re.compile(r"^([a-z0-9-]+)_([a-z]{2})_(p\d\d)_(\d+)\.svg$")
GRUPOS = {"ninos": (0, 12), "adolescentes": (13, 17), "adultos": (18, 200), "todos": (0, 200)}
IDIOMAS = {"es": "Español", "en": "Inglés", "zh": "Chino", "ja": "Japonés", "ar": "Árabe",
           "ru": "Ruso", "de": "Alemán", "hi": "Hindi", "sw": "Suajili", "qu": "Quechua"}

app = FastAPI()


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


with db() as c:
    c.executescript("""
    CREATE TABLE IF NOT EXISTS evaluadores(id INTEGER PRIMARY KEY, alias TEXT, edad INTEGER, creado REAL);
    CREATE TABLE IF NOT EXISTS votos(id INTEGER PRIMARY KEY, evaluador INTEGER, ganador TEXT,
        perdedor TEXT, ms INTEGER, creado REAL);
    """)


def catalogo():
    out = {}
    for f in SVG_DIR.glob("*.svg"):
        m = NOMBRE.match(f.name)
        if m:
            out[f.name] = dict(modelo=m[1], lang=m[2], prompt=m[3], muestra=int(m[4]))
    return out


class Registro(BaseModel):
    alias: str = Field(min_length=1, max_length=30)
    edad: int = Field(ge=3, le=110)


class Voto(BaseModel):
    evaluador: int
    ganador: str
    perdedor: str
    ms: int = 0


@app.post("/api/registro")
def registro(r: Registro):
    with db() as c:
        cur = c.execute("INSERT INTO evaluadores(alias,edad,creado) VALUES(?,?,?)",
                        (r.alias.strip(), r.edad, time.time()))
        return {"id": cur.lastrowid}


@app.get("/api/modelos")
def modelos():
    return sorted({v["modelo"] for v in catalogo().values()})


@app.get("/api/duelo")
def duelo(evaluador: int, modelo: str = "haiku"):
    cat = {k: v for k, v in catalogo().items() if v["modelo"] == modelo}
    if len(cat) < 2:
        raise HTTPException(404, "Todavía no hay dibujos")
    with db() as c:
        vistos = {frozenset((r["ganador"], r["perdedor"])) for r in
                  c.execute("SELECT ganador, perdedor FROM votos WHERE evaluador=?", (evaluador,))}
        cuenta = {}
        for r in c.execute("SELECT ganador, perdedor FROM votos"):
            for k in (r["ganador"], r["perdedor"]):
                cuenta[k] = cuenta.get(k, 0) + 1
    # el menos votado primero, rival del mismo prompt en otro idioma
    orden = sorted(cat, key=lambda k: (cuenta.get(k, 0), random.random()))
    for a in orden[:20]:
        rivales = [b for b in cat if cat[b]["prompt"] == cat[a]["prompt"]
                   and cat[b]["lang"] != cat[a]["lang"] and frozenset((a, b)) not in vistos]
        if rivales:
            rivales.sort(key=lambda k: (cuenta.get(k, 0), random.random()))
            par = [a, rivales[0]]
            random.shuffle(par)
            return {"a": par[0], "b": par[1]}
    raise HTTPException(410, "Ya viste todos")


@app.post("/api/voto")
def voto(v: Voto):
    cat = catalogo()
    if v.ganador not in cat or v.perdedor not in cat:
        raise HTTPException(400, "dibujo desconocido")
    with db() as c:
        c.execute("INSERT INTO votos(evaluador,ganador,perdedor,ms,creado) VALUES(?,?,?,?,?)",
                  (v.evaluador, v.ganador, v.perdedor, v.ms, time.time()))
        n = c.execute("SELECT COUNT(*) FROM votos WHERE evaluador=?", (v.evaluador,)).fetchone()[0]
    return {"votos": n}


def bradley_terry(pares, items, iters=200):
    """pares: lista (ganador, perdedor). Devuelve fuerza normalizada (media geométrica = 1)."""
    w = {i: 1.0 for i in items}
    vict = {i: 0 for i in items}
    for g, _ in pares:
        vict[g] += 1
    for _ in range(iters):
        den = {i: 0.0 for i in items}
        for g, p in pares:
            s = 1.0 / (w[g] + w[p])
            den[g] += s
            den[p] += s
        w = {i: (vict[i] + 0.5) / (den[i] + 1.0 / w[i]) for i in items}  # prior suave
        prod = 1.0
        for x in w.values():
            prod *= x
        g = prod ** (1 / len(w))
        w = {i: x / g for i, x in w.items()}
    return w


@app.get("/api/resultados")
def resultados(modelo: str = "haiku", grupo: str = "todos"):
    lo, hi = GRUPOS.get(grupo, GRUPOS["todos"])
    cat = catalogo()
    with db() as c:
        filas = c.execute("""SELECT v.ganador, v.perdedor FROM votos v JOIN evaluadores e
                             ON e.id=v.evaluador WHERE e.edad BETWEEN ? AND ?""", (lo, hi)).fetchall()
        evals = c.execute("""SELECT COUNT(DISTINCT v.evaluador) FROM votos v JOIN evaluadores e
                             ON e.id=v.evaluador WHERE e.edad BETWEEN ? AND ?""", (lo, hi)).fetchone()[0]
    pares = [(cat[g]["lang"], cat[p]["lang"]) for g, p in filas
             if g in cat and p in cat and cat[g]["modelo"] == modelo]
    langs = list(IDIOMAS)
    base = bradley_terry(pares, langs)
    rng = random.Random(7)
    boot = {l: [] for l in langs}
    if pares:
        for _ in range(150):
            m = [rng.choice(pares) for _ in pares]
            for l, x in bradley_terry(m, langs, 60).items():
                boot[l].append(x)
    tabla = []
    for l in langs:
        g = sum(1 for a, _ in pares if a == l)
        t = sum(1 for a, b in pares if l in (a, b))
        bs = sorted(boot[l]) or [1.0]
        tabla.append(dict(lang=l, nombre=IDIOMAS[l], fuerza=round(base[l], 3),
                          ic_bajo=round(bs[int(len(bs) * .025)], 3), ic_alto=round(bs[int(len(bs) * .975) - 1 if len(bs) > 1 else 0], 3),
                          victorias=g, duelos=t, pct=round(100 * g / t, 1) if t else None))
    tabla.sort(key=lambda r: -r["fuerza"])
    return {"modelo": modelo, "grupo": grupo, "votos": len(pares), "evaluadores": evals, "tabla": tabla}


@app.get("/svg/{nombre}")
def svg(nombre: str):
    if not NOMBRE.match(nombre):
        raise HTTPException(404)
    f = SVG_DIR / nombre
    if not f.exists():
        raise HTTPException(404)
    # servido como imagen: los scripts dentro de un <img> SVG no se ejecutan
    return FileResponse(f, media_type="image/svg+xml",
                        headers={"Content-Security-Policy": "script-src 'none'"})


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
