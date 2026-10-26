"""Genera reports/informe-haiku.html y las figuras sueltas de docs/ (HTML para capturar) desde data/stats.json.

Uso: python3 analisis/informe.py   →  reports/informe-haiku.html + build/fig-*.html
"""
import json, math
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
S = json.loads((RAIZ / "data" / "stats.json").read_text())
PROMPTS = {p["id"]: p["es"] for p in json.loads((RAIZ / "gen" / "prompts.json").read_text())["prompts"]}
NOMBRE = {x["lang"]: x["nombre"] for x in S["grupos"]["todos"]}
EDAD = {e["id"]: e["edad"] for e in S["evaluadores"]}

CSS = """
:root{--bg:#0d1117;--card:#161b22;--line:#2a313c;--ink:#e6edf3;--mut:#8b949e;--kid:#ffb454;--adu:#7aa2ff;
--all:#3ad1a8;--bad:#ff6b8b;--accent:#d97757}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1040px;margin:auto;padding:40px 16px 80px}h1{font-size:40px;line-height:1.1;margin:.2em 0}
h2{font-size:26px;margin:56px 0 12px;border-top:1px solid var(--line);padding-top:28px}h3{margin:24px 0 8px}
.eyebrow{letter-spacing:.22em;text-transform:uppercase;color:var(--accent);font-size:13px;font-weight:700}
.mut{color:var(--mut)}.lead{font-size:20px;color:#c9d1d9}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:760px){.grid2{grid-template-columns:1fr}}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}@media(max-width:760px){.kpis{grid-template-columns:1fr 1fr}}
.kpi b{display:block;font-size:30px}.kpi span{color:var(--mut);font-size:14px}
table{width:100%;border-collapse:collapse;font-size:15px}td,th{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--mut);font-weight:600}td.n{text-align:right;font-variant-numeric:tabular-nums}
.gal{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}@media(max-width:760px){.gal{grid-template-columns:repeat(2,1fr)}}
.gal figure{margin:0}.gal img{width:100%;aspect-ratio:1;border-radius:12px;display:block;background:#fff}
.gal figcaption{font-size:13px;color:var(--mut);margin-top:4px}
.tag{display:inline-block;padding:2px 10px;border-radius:99px;font-size:13px;font-weight:600}
.sig{background:#ff6b8b22;color:var(--bad)}.leg span{margin-right:16px;font-size:14px}
svg text{fill:var(--ink);font:13px system-ui,sans-serif}svg .m{fill:var(--mut)}
"""


def forest(series, ancho=900, titulo=""):
    """Gráfico de intervalos: una fila por idioma, un punto por serie. series=[(etiqueta, color, tabla)]."""
    orden = [x["lang"] for x in series[0][2]]
    lo, hi = math.log(0.18), math.log(6.5)
    x0, x1 = 120, ancho - 70
    X = lambda v: x0 + (math.log(max(min(v, 6.5), .18)) - lo) / (hi - lo) * (x1 - x0)
    fila = 34
    alto = 40 + fila * len(orden) + 30
    o = [f'<svg viewBox="0 0 {ancho} {alto}" width="100%" role="img" aria-label="{titulo}">']
    for v in (0.25, 0.5, 1, 2, 4):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="30" y2="{alto-26}" stroke="{"#8b949e" if v==1 else "#2a313c"}" '
                 f'stroke-dasharray="{"" if v==1 else "3 4"}"/><text class="m" x="{X(v):.1f}" y="{alto-8}" text-anchor="middle">{v:g}</text>')
    o.append(f'<text class="m" x="{x0}" y="18">← menos elegido</text><text class="m" x="{x1}" y="18" text-anchor="end">más elegido →</text>')
    k = len(series)
    for i, l in enumerate(orden):
        y = 40 + i * fila + fila / 2
        o.append(f'<text x="{x0-14}" y="{y+4}" text-anchor="end">{NOMBRE[l]}</text>')
        for j, (_, color, tabla) in enumerate(series):
            r = next(x for x in tabla if x["lang"] == l)
            yy = y + (j - (k - 1) / 2) * 9
            o.append(f'<line x1="{X(r["ic"][0]):.1f}" x2="{X(r["ic"][1]):.1f}" y1="{yy:.1f}" y2="{yy:.1f}" '
                     f'stroke="{color}" stroke-width="4" stroke-linecap="round" opacity=".35"/>')
            borde = ' stroke="#fff" stroke-width="2"' if r["significativo"] else ""
            o.append(f'<circle cx="{X(r["fuerza"]):.1f}" cy="{yy:.1f}" r="{6 if r["significativo"] else 4.5}" '
                     f'fill="{color}"{borde}/>')
    o.append("</svg>")
    leyenda = "".join(f'<span><b style="color:{c}">●</b> {e}</span>' for e, c, _ in series)
    return f'<div class="leg">{leyenda}</div>' + "".join(o)


def barras_complejidad(ancho=900):
    el = S["elementos_por_idioma"]
    orden = sorted(el, key=lambda l: -el[l])
    adu = {x["lang"]: x["pct"] for x in S["por_evaluador"]["E3"]}
    x0, x1, fila = 120, ancho - 120, 30
    alto = 20 + fila * len(orden) + 10
    m = max(el.values())
    o = [f'<svg viewBox="0 0 {ancho} {alto}" width="100%" role="img" aria-label="Elementos por dibujo">']
    for i, l in enumerate(orden):
        y = 20 + i * fila
        w = el[l] / m * (x1 - x0)
        o.append(f'<text x="{x0-14}" y="{y+15}" text-anchor="end">{NOMBRE[l]}</text>'
                 f'<rect x="{x0}" y="{y+3}" width="{w:.1f}" height="16" rx="4" fill="#3ad1a8" opacity=".85"/>'
                 f'<text x="{x0+w+8:.1f}" y="{y+15}">{el[l]:.0f}</text>'
                 f'<text class="m" x="{ancho-10}" y="{y+15}" text-anchor="end">adulto: {adu[l]:.0f} %</text>')
    o.append("</svg>")
    return "".join(o)


def tabla_grupos():
    fil = []
    t = {g: {x["lang"]: x for x in S["grupos"][g]} for g in ("todos", "ninos", "adultos")}
    for x in S["grupos"]["todos"]:
        l = x["lang"]
        celdas = ""
        for g in ("todos", "ninos", "adultos"):
            r = t[g][l]
            s = ' <span class="tag sig">sig.</span>' if r["significativo"] else ""
            celdas += f'<td class="n">{r["pct"]:.0f} %{s}</td><td class="n mut">{r["ic"][0]:.2f}–{r["ic"][1]:.2f}</td>'
        fil.append(f"<tr><td>{NOMBRE[l]}</td>{celdas}<td class='n'>{S['elementos_por_idioma'][l]:.0f}</td></tr>")
    return ("<table><tr><th>Idioma</th><th class='n'>Todos</th><th class='n'>IC 95 %</th><th class='n'>Niños</th>"
            "<th class='n'>IC 95 %</th><th class='n'>Adulto</th><th class='n'>IC 95 %</th><th class='n'>Elementos</th></tr>"
            + "".join(fil) + "</table>")


def galeria(pid, muestra=1, ruta="../data/svg/"):
    orden = ["es", "en", "zh", "ja", "ar", "ru", "de", "hi", "sw", "qu"]
    return '<div class="gal">' + "".join(
        f'<figure><img src="{ruta}haiku_{l}_{pid}_{muestra}.svg" alt="{NOMBRE[l]}" loading="lazy">'
        f'<figcaption>{NOMBRE[l]}</figcaption></figure>' for l in orden) + "</div>"


def pagina(cuerpo, titulo):
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{titulo}</title><style>{CSS}</style></head>'
            f'<body><main>{cuerpo}</main></body></html>')


def main():
    g = S["grupos"]
    sp = S["acuerdo_spearman"]
    cs = S["spearman_complejidad_vs_fuerza"]
    gc = S["pct_gana_el_mas_complejo"]
    gen = S["generacion"]
    serie_edades = [("Niños (7 y 11 años)", "#ffb454", g["ninos"]), ("Adulto (36 años)", "#7aa2ff", g["adultos"])]
    prompts = "".join(f"<tr><td>{pid}</td><td>{PROMPTS[pid]}</td><td>{NOMBRE[v['mejor']]} ({v['pct_mejor']} %)</td>"
                      f"<td class='mut'>{NOMBRE[v['peor']]} ({v['pct_peor']} %)</td></tr>"
                      for pid, v in S["por_prompt"].items())
    ev = "".join(f"<tr><td>{e['id']}</td><td class='n'>{e['edad']}</td><td class='n'>{e['votos']}</td>"
                 f"<td class='n'>{gc[e['id']]:.0f} %</td><td class='n'>{cs[e['id']]:+.2f}</td></tr>" for e in S["evaluadores"])

    cuerpo = f"""
<div class="eyebrow">Experimento · ronda 1 · Claude Haiku</div>
<h1>¿Un idioma hace más creativa a una IA?</h1>
<p class="lead">300 dibujos SVG de Claude Haiku: 10 ideas × 10 idiomas × 3 muestras. Tres personas de 7, 11 y 36 años
votaron a ciegas en duelos de dos dibujos. El idioma <b>no</b> hizo al modelo más creativo para todos: cambió
<b>cuánto dibuja</b>, y cada edad premió una cosa distinta.</p>
<div class="kpis">
 <div class="card kpi"><b>300</b><span>dibujos generados (${gen['costo_usd']:.2f})</span></div>
 <div class="card kpi"><b>{S['votos_validos']}</b><span>votos válidos de {S['votos_totales']}</span></div>
 <div class="card kpi"><b>0</b><span>idiomas ganadores en el total</span></div>
 <div class="card kpi"><b>ρ = {cs['E3']:+.2f}</b><span>complejidad ↔ gusto del adulto</span></div>
</div>

<h2>1 · El mismo encargo, diez idiomas</h2>
<p>«Un animal que nunca ha existido», primera muestra de cada idioma. En quechua el modelo dibujó una llama común en un prado.</p>
{galeria('p01')}

<h2>2 · Resultado por edad</h2>
<p>Fuerza Bradley-Terry: 1 es el promedio y 2 significa que gana el doble. La barra es el intervalo de confianza del 95 %
(bootstrap, 1000 remuestreos). Un punto con borde blanco es significativo: su intervalo no toca el 1.</p>
<div class="card">{forest(serie_edades, titulo='Fuerza por idioma y edad')}</div>
<h3>Tabla completa (% de duelos ganados)</h3>
<div class="card">{tabla_grupos()}</div>

<h2>3 · Lo que de verdad cambia: cuánto dibuja</h2>
<p>Elementos SVG medios por dibujo (formas, trazos, grupos). En quechua, árabe y suajili Haiku hace dibujos
<b>hasta un 40 % más simples</b> que en chino o japonés, y también escribe menos: {gen['tokens_salida_por_idioma']['qu']} tokens de salida
de media en quechua frente a {gen['tokens_salida_por_idioma']['ja']} en japonés.</p>
<div class="card">{barras_complejidad()}</div>
<h3>Quién premia lo complejo</h3>
<div class="card"><table><tr><th>Evaluador</th><th class='n'>Edad</th><th class='n'>Votos</th>
<th class='n'>Elige el más complejo</th><th class='n'>ρ complejidad ↔ gusto</th></tr>{ev}</table>
<p class="mut">El adulto elige el dibujo con más elementos en el {gc['E3']:.0f} % de los duelos y su ranking de idiomas sigue
casi exacto el de complejidad (ρ = {cs['E3']:+.2f}). Los niños eligen a cara o cruz respecto a la complejidad
y, por idioma, van en sentido contrario (ρ = {cs['E1']:+.2f} y {cs['E2']:+.2f}).</p></div>

<h2>4 · Los tres votantes no se ponen de acuerdo</h2>
<div class="grid2">
 <div class="card"><h3 style="margin-top:0">Acuerdo entre rankings (Spearman)</h3><table>
 <tr><td>11 años ↔ 7 años</td><td class="n">{sp['E1-E2']:+.2f}</td></tr>
 <tr><td>11 años ↔ 36 años</td><td class="n">{sp['E1-E3']:+.2f}</td></tr>
 <tr><td>7 años ↔ 36 años</td><td class="n">{sp['E2-E3']:+.2f}</td></tr></table>
 <p class="mut">Cero es ningún acuerdo; negativo, gustos opuestos. Al sumar a los tres, las preferencias se cancelan.</p></div>
 <div class="card"><h3 style="margin-top:0">Únicos efectos significativos</h3>
 <p>• A la votante de 7 años le gusta el <b>quechua</b> (gana el {next(x for x in S['por_evaluador']['E2'] if x['lang']=='qu')['pct']:.0f} % de sus duelos).</p>
 <p>• Al adulto <b>no</b> le gusta el <b>árabe</b> (lo elige en el {next(x for x in g['adultos'] if x['lang']=='ar')['pct']:.0f} %).</p>
 <p class="mut">Ninguno sobrevive al juntar a todos.</p></div>
</div>

<h2>5 · El ganador cambia en cada idea</h2>
<div class="card"><table><tr><th>#</th><th>Idea</th><th>Más elegido</th><th>Menos elegido</th></tr>{prompts}</table></div>

<h2>6 · Cómo se hizo</h2>
<div class="card"><ul>
<li><b>Generación:</b> <code>claude -p --model haiku</code> sin herramientas, sin configuración y con un system prompt mínimo («SVG»), una sesión por dibujo. Toda la instrucción va en el idioma de prueba y le pide pensar en ese idioma.</li>
<li><b>Traducción:</b> hecha por Claude Opus. Las de quechua y suajili son las menos fiables.</li>
<li><b>Votación:</b> web local en tablets y móviles. Cada duelo enfrenta el mismo prompt en dos idiomas distintos, sin decir cuáles; primero salen los dibujos con menos votos.</li>
<li><b>Limpieza:</b> se descartan los votos de menos de 500 ms (toques dobles).</li>
<li><b>Estadística:</b> Bradley-Terry con prior suave + bootstrap de 1000 remuestreos.</li></ul></div>

<h2>7 · Límites</h2>
<div class="card"><ul>
<li><b>Tres votantes de la misma familia.</b> Es un estudio piloto: sirve para formular hipótesis, no para probarlas.</li>
<li><b>Un solo adulto.</b> El patrón «adultos premian la complejidad» necesita más adultos para confirmarse.</li>
<li><b>Votantes desiguales:</b> el de 11 años hizo 341 votos, el adulto 223.</li>
<li><b>Calidad de la traducción:</b> en quechua el modelo pudo entender mal la idea; eso se mezcla con el efecto del idioma.</li>
<li><b>Un solo modelo:</b> Haiku. Sonnet y Opus vienen en la siguiente ronda.</li></ul></div>
<p class="mut" style="margin-top:40px">Datos y código: data/votos.csv · data/stats.json · analisis/</p>
"""
    out = RAIZ / "reports"
    out.mkdir(exist_ok=True)
    (out / "informe-haiku.html").write_text(pagina(cuerpo, "Idioma y creatividad · Haiku"), encoding="utf-8")

    b = RAIZ / "build"
    b.mkdir(exist_ok=True)
    fig = lambda c: pagina(c, "fig").replace("padding:40px 16px 80px", "padding:28px 32px")
    (b / "fig-edades.html").write_text(fig(f'<div class="card">{forest(serie_edades)}</div>'), encoding="utf-8")
    (b / "fig-complejidad.html").write_text(fig(f'<div class="card">{barras_complejidad()}</div>'), encoding="utf-8")
    (b / "fig-galeria.html").write_text(fig(galeria("p01", ruta="../data/svg/")), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
