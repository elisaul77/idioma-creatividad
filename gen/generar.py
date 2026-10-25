"""Genera los SVG: 10 prompts x 10 idiomas x N muestras con un modelo.

Uso: python3 gen/generar.py --modelo haiku --muestras 3 --paralelo 6
Llama a `claude -p` aislado (sin herramientas, sin settings, system prompt mínimo).
Idempotente: salta lo que ya existe en data/svg/.
"""
import argparse, json, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SVG_DIR = RAIZ / "data" / "svg"
LOG = RAIZ / "data" / "generacion.jsonl"
CWD_VACIO = tempfile.mkdtemp(prefix="idioma-gen-")


def extraer_svg(texto):
    m = re.search(r"<svg\b.*?</svg>", texto, re.S | re.I)
    return m.group(0) if m else None


def generar(modelo, lang, pid, n, texto):
    destino = SVG_DIR / f"{modelo}_{lang}_{pid}_{n}.svg"
    if destino.exists():
        return "existe"
    cmd = ["claude", "-p", "--model", modelo, "--tools", "", "--setting-sources", "",
           "--no-session-persistence", "--system-prompt", "SVG", "--output-format", "json", texto]
    for intento in range(3):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=CWD_VACIO)
            out = json.loads(r.stdout)
            svg = extraer_svg(out.get("result", ""))
            if svg:
                destino.write_text(svg, encoding="utf-8")
                with LOG.open("a") as f:
                    f.write(json.dumps({"archivo": destino.name, "modelo": modelo, "lang": lang,
                                        "prompt": pid, "muestra": n, "intento": intento,
                                        "costo": out.get("total_cost_usd"),
                                        "tokens": out.get("usage", {}).get("output_tokens")}) + "\n")
                return "ok"
        except Exception as e:
            print(f"  error {destino.name}: {e}", file=sys.stderr)
    return "fallo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="haiku")
    ap.add_argument("--muestras", type=int, default=3)
    ap.add_argument("--paralelo", type=int, default=6)
    a = ap.parse_args()
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((RAIZ / "gen" / "prompts.json").read_text())
    tareas = [(a.modelo, lang, p["id"], n, plantilla.replace("{p}", p[lang]))
              for p in cfg["prompts"] for lang, plantilla in cfg["instruccion"].items()
              for n in range(1, a.muestras + 1)]
    print(f"{len(tareas)} tareas con {a.modelo}")
    with ThreadPoolExecutor(a.paralelo) as ex:
        res = list(ex.map(lambda t: generar(*t), tareas))
    print({k: res.count(k) for k in set(res)})


if __name__ == "__main__":
    main()
