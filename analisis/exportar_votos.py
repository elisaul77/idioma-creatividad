"""Exporta los votos de la base SQLite a data/votos.csv sin nombres (E1, E2… en orden de registro).

Uso: docker exec idioma-creatividad python - < analisis/exportar_votos.py > data/votos.csv
"""
import csv, sqlite3, sys

c = sqlite3.connect("/data/votos.db")
ids = [r[0] for r in c.execute("SELECT DISTINCT evaluador FROM votos ORDER BY evaluador")]
alias = {i: f"E{n + 1}" for n, i in enumerate(ids)}
w = csv.writer(sys.stdout)
w.writerow(["evaluador", "edad", "ganador", "perdedor", "ms"])
for e, edad, g, p, ms in c.execute("""SELECT v.evaluador, e.edad, ganador, perdedor, ms FROM votos v
                                      JOIN evaluadores e ON e.id = v.evaluador ORDER BY v.id"""):
    w.writerow([alias[e], edad, g, p, ms])
