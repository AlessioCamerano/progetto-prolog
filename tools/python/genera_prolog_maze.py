import random
import sys
from pathlib import Path

sys.setrecursionlimit(100000)

RIGHE, COLONNE = 200, 200

griglia = [[True for _ in range(COLONNE + 1)] for _ in range(RIGHE + 1)]
visitati = set()


def dentro(r, c):
    return 2 <= r < RIGHE and 2 <= c < COLONNE


def genera_labirinto_perfetto(r, c):
    visitati.add((r, c))
    griglia[r][c] = False
    direzioni = [(0, 2), (0, -2), (2, 0), (-2, 0)]
    random.shuffle(direzioni)

    for dr, dc in direzioni:
        nr, nc = r + dr, c + dc
        if dentro(nr, nc) and (nr, nc) not in visitati:
            griglia[r + dr // 2][c + dc // 2] = False
            genera_labirinto_perfetto(nr, nc)


def crea_biforcazioni_ingannevoli(probabilita=0.15):
    for r in range(3, RIGHE - 2, 2):
        for c in range(3, COLONNE - 2, 2):
            if griglia[r][c] and random.random() < probabilita:
                if random.choice([True, False]):
                    if not griglia[r - 1][c] and not griglia[r + 1][c]:
                        griglia[r][c] = False
                else:
                    if not griglia[r][c - 1] and not griglia[r][c + 1]:
                        griglia[r][c] = False


genera_labirinto_perfetto(3, 3)
crea_biforcazioni_ingannevoli(0.12)

iniziale_r, iniziale_c = 2, 2
uscita1_r, uscita1_c = RIGHE - 1, COLONNE - 1
uscita2_r, uscita2_c = RIGHE // 2, COLONNE - 1

griglia[iniziale_r][iniziale_c] = False
griglia[uscita1_r][uscita1_c] = False
griglia[uscita2_r][uscita2_c] = False

griglia[iniziale_r + 1][iniziale_c] = False
griglia[uscita1_r - 1][uscita1_c] = False
griglia[uscita2_r][uscita2_c - 1] = False

output_path = Path(__file__).resolve().parents[2] / "src/prolog/domini/labirinto/labirinto.pl"
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(":- multifile num_righe/1, num_col/1, iniziale/1, finale/1, occupata/1.\n\n")
    f.write(f"num_righe({RIGHE}).\n")
    f.write(f"num_col({COLONNE}).\n")
    f.write(f"iniziale(pos({iniziale_r},{iniziale_c})).\n")
    f.write(f"finale(pos({uscita1_r},{uscita1_c})).\n")
    f.write(f"finale(pos({uscita2_r},{uscita2_c})).\n\n")

    for r in range(1, RIGHE + 1):
        for c in range(1, COLONNE + 1):
            if griglia[r][c]:
                f.write(f"occupata(pos({r},{c})).\n")

print(f"Labirinto ad alta complessità ({RIGHE}x{COLONNE}) generato in '{output_path}'.")
