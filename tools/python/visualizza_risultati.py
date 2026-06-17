#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import resource
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


@dataclass
class AlgorithmResult:
    actions: List[str]
    cost: int
    time_s: float
    stack_mb: float
    process_mb: float
    peak_process_mb: float


@dataclass
class MazeDomain:
    rows: int
    cols: int
    start: Tuple[int, int]
    goals: List[Tuple[int, int]]
    obstacles: set[Tuple[int, int]]


@dataclass
class PuzzleDomain:
    start: List[int]
    goal: List[int]


def parse_prolog_list(raw: str) -> List[str]:
    text = raw.strip()
    if not text.startswith("[") or not text.endswith("]"):
        raise ValueError(f"Lista Prolog non valida: {raw}")

    inner = text[1:-1].strip()
    if not inner:
        return []

    parts = [p.strip() for p in inner.split(",")]
    return [p.strip("'\"") for p in parts if p]


def parse_number_list(raw: str) -> List[int]:
    text = raw.strip().replace(" ", "")
    try:
        val = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        raise ValueError(f"Impossibile leggere lista numerica Prolog: {raw}")

    if not isinstance(val, list) or not all(isinstance(x, int) for x in val):
        raise ValueError(f"Lista numerica non valida: {raw}")
    return val


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_maze_domain(root: Path) -> MazeDomain:
    text = read_text(root / "src/prolog/domini/labirinto/labirinto.pl")

    rows_match = re.search(r"num_righe\((\d+)\)\.", text)
    cols_match = re.search(r"num_col\((\d+)\)\.", text)
    start_match = re.search(r"iniziale\(pos\((\d+),(\d+)\)\)\.", text)
    goal_matches = re.findall(r"finale\(pos\((\d+),(\d+)\)\)\.", text)

    if not all([rows_match, cols_match, start_match]) or not goal_matches:
        raise ValueError("Dati dominio labirinto incompleti in src/prolog/domini/labirinto/labirinto.pl")

    obstacles = {(int(r), int(c)) for r, c in re.findall(r"occupata\(pos\((\d+),(\d+)\)\)\.", text)}

    return MazeDomain(
        rows=int(rows_match.group(1)),
        cols=int(cols_match.group(1)),
        start=(int(start_match.group(1)), int(start_match.group(2))),
        goals=[(int(r), int(c)) for r, c in goal_matches],
        obstacles=obstacles,
    )


def parse_puzzle_domain(root: Path, variant: str = "puzzle") -> PuzzleDomain:
    filename = "puzzle.pl" if variant == "puzzle8" or variant == "puzzle" else "puzzle15.pl"
    text = read_text(root / f"src/prolog/domini/puzzle/{filename}")
    init_match = re.search(r"iniziale\((\[[^\]]*\])\)\.", text)
    goal_match = re.search(r"finale\((\[[^\]]*\])\)\.", text)

    if not init_match or not goal_match:
        raise ValueError(f"Dati dominio puzzle incompleti in src/prolog/domini/puzzle/{filename}")

    return PuzzleDomain(start=parse_number_list(init_match.group(1)), goal=parse_number_list(goal_match.group(1)))


def build_swipl_goal(algo: str) -> str:
    if algo == "astar":
        solve_call = "cercaAStar(Azioni,Costo)"
    else:
        solve_call = "cercaIDAStar(Azioni),length(Azioni,Costo)"

    return (
        "statistics(runtime,[T0|_]),"
        f"{solve_call},"
        "statistics(runtime,[T1|_]),"
        "Tempo is (T1-T0)/1000,"
        "statistics(stack,MemStack),"
        "statistics(memory,[MemProc,_]),"
        "format('RESULT|~q|~w|~6f|~w|~w~n',[Azioni,Costo,Tempo,MemStack,MemProc]),"
        "halt"
    )


def run_prolog(root: Path, domain: str, algo: str) -> AlgorithmResult:
    files = [
        "src/prolog/algoritmi/aStar.pl",
        "src/prolog/algoritmi/idaStar.pl",
        "src/prolog/euristica/euristica.pl",
    ]
    if domain == "labirinto":
        files += [
            "src/prolog/domini/labirinto/labirinto.pl",
            "src/prolog/domini/labirinto/labirinto_azioni.pl",
        ]
    else:
        # support puzzle8 and puzzle15
        if domain == "puzzle15":
            files += [
                "src/prolog/domini/puzzle/puzzle15.pl",
                "src/prolog/domini/puzzle/puzzle15_azioni.pl",
            ]
        else:
            files += [
                "src/prolog/domini/puzzle/puzzle.pl",
                "src/prolog/domini/puzzle/puzzle_azioni.pl",
            ]

    cmd: List[str] = ["swipl", "-q"]
    for f in files:
        cmd.extend(["-s", str(root / f)])
    cmd.extend(["-g", build_swipl_goal(algo)])

    try:
        completed = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("swipl non trovato. Installa SWI-Prolog e riprova.") from exc

    if completed.returncode != 0:
        raise RuntimeError("Errore esecuzione Prolog:\n" f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}")

    line = ""
    for out_line in completed.stdout.splitlines():
        if out_line.startswith("RESULT|"):
            line = out_line
            break

    if not line:
        raise RuntimeError("Nessun risultato parsabile trovato in output Prolog. " f"Output completo:\n{completed.stdout}")

    _, actions_raw, cost_raw, time_raw, stack_raw, process_raw = line.split("|", 5)
    actions = parse_prolog_list(actions_raw)
    cost = int(cost_raw)
    time_s = float(time_raw)
    stack_mb = float(stack_raw) / (1024 * 1024)
    process_mb = float(process_raw) / (1024 * 1024)
    peak_process_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024

    return AlgorithmResult(
        actions=actions,
        cost=cost,
        time_s=time_s,
        stack_mb=stack_mb,
        process_mb=process_mb,
        peak_process_mb=peak_process_mb,
    )


def apply_maze_action(state: Tuple[int, int], action: str) -> Tuple[int, int]:
    r, c = state
    moves = {"nord": (-1, 0), "sud": (1, 0), "est": (0, 1), "ovest": (0, -1)}
    if action not in moves:
        raise ValueError(f"Azione labirinto non riconosciuta: {action}")
    dr, dc = moves[action]
    return (r + dr, c + dc)


def reconstruct_maze_path(start: Tuple[int, int], actions: Sequence[str]) -> List[Tuple[int, int]]:
    path = [start]
    cur = start
    for act in actions:
        cur = apply_maze_action(cur, act)
        path.append(cur)
    return path


def apply_puzzle_action(state: Sequence[int], action: str) -> List[int]:
    s = list(state)
    n = int(len(s) ** 0.5)
    zero = s.index(0)
    offsets = {"su": -n, "giu": n, "sinistra": -1, "destra": 1}
    if action not in offsets:
        raise ValueError(f"Azione puzzle non riconosciuta: {action}")
    j = zero + offsets[action]
    s[zero], s[j] = s[j], s[zero]
    return s


def reconstruct_puzzle_states(start: Sequence[int], actions: Sequence[str]) -> List[List[int]]:
    states = [list(start)]
    cur = list(start)
    for act in actions:
        cur = apply_puzzle_action(cur, act)
        states.append(cur)
    return states


def format_actions(actions: Sequence[str], per_line: int = 14) -> str:
    if not actions:
        return "[]"

    chunks = [actions[i: i + per_line] for i in range(0, len(actions), per_line)]
    rendered = [", ".join(chunk) for chunk in chunks]
    return "\n".join(rendered)


def print_report(domain: str, algo: str, result: AlgorithmResult) -> None:
    title = f"RISULTATI {algo.upper()} - {domain.upper()}"
    print("\n" + "=" * len(title))
    print(title)
    print("=" * len(title))
    print(f"Costo soluzione:          {result.cost}")
    print(f"Numero azioni:           {len(result.actions)}")
    print(f"Tempo esecuzione:        {result.time_s:.3f} s")
    print(f"Memoria stack:           {result.stack_mb:.2f} MB")
    print(f"Memoria processo totale: {result.process_mb:.2f} MB")
    print(f"Picco RAM processo:      {result.peak_process_mb:.2f} MB")
    print("Azioni:")
    print(format_actions(result.actions))


def ensure_matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise RuntimeError("matplotlib non installato. Installa con: pip install matplotlib")


def is_animation_path(path: Path | None) -> bool:
    if path is None:
        return False
    return path.suffix.lower() in {".gif", ".mp4"}


def enable_scroll_zoom(ax, base_scale: float = 1.2):
    def on_scroll(event):
        if event.inaxes != ax:
            return

        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata
        if xdata is None or ydata is None:
            return

        if event.button == "up":
            scale_factor = 1 / base_scale
        elif event.button == "down":
            scale_factor = base_scale
        else:
            scale_factor = 1

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
        ax.figure.canvas.draw_idle()

    ax.figure.canvas.mpl_connect("scroll_event", on_scroll)


def plot_maze(
    domain: MazeDomain,
    path: Sequence[Tuple[int, int]],
    result: AlgorithmResult,
    save: Path | None,
    animate: bool,
    delay_ms: int,
) -> None:
    ensure_matplotlib()
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from matplotlib.colors import ListedColormap

    grid = [[0 for _ in range(domain.cols)] for _ in range(domain.rows)]
    for r, c in domain.obstacles:
        grid[r - 1][c - 1] = 1

    fig_w = max(9, min(18, domain.cols / 12))
    fig_h = max(8, min(18, domain.rows / 12))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    cmap = ListedColormap(["#f3f7f0", "#3a4a57", "#c3ecd6"])
    ax.imshow(grid, cmap=cmap, origin="upper")

    sr, sc = domain.start
    ax.scatter([sc - 1], [sr - 1], marker="o", s=180, c="#1b9e77", edgecolors="black", label="Start")
    goal_label_used = False
    for gr, gc in domain.goals:
        ax.scatter([gc - 1], [gr - 1], marker="X", s=220, c="#d95f02", edgecolors="black", label="Goal" if not goal_label_used else None)
        goal_label_used = True

    line, = ax.plot([], [], color="#24577a", linewidth=2.8, alpha=0.95, label="Percorso")
    current = ax.scatter([], [], marker="o", s=120, c="#1f78b4", edgecolors="black", zorder=5, label="Posizione")

    if domain.cols <= 40:
        ax.set_xticks(range(domain.cols))
        ax.set_xticklabels(range(1, domain.cols + 1))
    else:
        step_x = max(1, domain.cols // 20)
        ticks_x = list(range(0, domain.cols, step_x))
        ax.set_xticks(ticks_x)
        ax.set_xticklabels([str(t + 1) for t in ticks_x])

    if domain.rows <= 40:
        ax.set_yticks(range(domain.rows))
        ax.set_yticklabels(range(1, domain.rows + 1))
    else:
        step_y = max(1, domain.rows // 20)
        ticks_y = list(range(0, domain.rows, step_y))
        ax.set_yticks(ticks_y)
        ax.set_yticklabels([str(t + 1) for t in ticks_y])

    ax.set_xlabel("Colonne")
    ax.set_ylabel("Righe")
    ax.set_title("Labirinto - animazione percorso", fontsize=12)
    ax.grid(which="major", color="white", linestyle="-", linewidth=0.8)
    ax.legend(loc="upper right")
    ax.set_aspect("equal")
    enable_scroll_zoom(ax)
    ax.text(0.01, 1.01, "Usa rotellina per zoomare, trascina per spostarti", transform=ax.transAxes, fontsize=9, color="#444444", va="bottom")
    plt.tight_layout()

    def set_frame(frame_index: int):
        partial = path[: frame_index + 1]
        xs = [c - 1 for _, c in partial]
        ys = [r - 1 for r, _ in partial]
        line.set_data(xs, ys)
        current.set_offsets([[xs[-1], ys[-1]]])
        ax.set_title((f"Labirinto - step {frame_index}/{len(path) - 1}" f" | costo={result.cost} | tempo={result.time_s:.3f}s"), fontsize=12)
        return line, current

    if animate:
        ani = FuncAnimation(fig, set_frame, frames=len(path), interval=delay_ms, repeat=False, blit=False)
        fig._ani = ani

        if save and is_animation_path(save):
            if save.suffix.lower() == ".gif":
                try:
                    from matplotlib.animation import PillowWriter
                except ImportError:
                    raise RuntimeError("Per salvare GIF serve Pillow: pip install pillow")
                fps = max(1, int(round(1000 / max(1, delay_ms))))
                ani.save(save, writer=PillowWriter(fps=fps), dpi=140)
            else:
                fps = max(1, int(round(1000 / max(1, delay_ms))))
                ani.save(save, fps=fps, dpi=140)
            print(f"\nAnimazione salvata in: {save}")
            return
    else:
        set_frame(len(path) - 1)

    if save and not animate:
        fig.savefig(save, dpi=180)
        print(f"\nGrafico salvato in: {save}")
    elif save and animate and not is_animation_path(save):
        fig.savefig(save, dpi=180)
        print(f"\nSalvato frame finale in: {save}")
    else:
        plt.show()


def plot_maze_preview(domain: MazeDomain, save: Path | None) -> None:
    ensure_matplotlib()
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    grid = [[0 for _ in range(domain.cols)] for _ in range(domain.rows)]
    for r, c in domain.obstacles:
        grid[r - 1][c - 1] = 1

    fig_w = max(9, min(18, domain.cols / 12))
    fig_h = max(8, min(18, domain.rows / 12))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    cmap = ListedColormap(["#f3f7f0", "#3a4a57"])
    ax.imshow(grid, cmap=cmap, origin="upper")

    sr, sc = domain.start
    ax.scatter([sc - 1], [sr - 1], marker="o", s=180, c="#1b9e77", edgecolors="black", label="Start")
    goal_label_used = False
    for gr, gc in domain.goals:
        ax.scatter([gc - 1], [gr - 1], marker="X", s=220, c="#d95f02", edgecolors="black", label="Goal" if not goal_label_used else None)
        goal_label_used = True

    if domain.cols <= 40:
        ax.set_xticks(range(domain.cols))
        ax.set_xticklabels(range(1, domain.cols + 1))
    else:
        step_x = max(1, domain.cols // 20)
        ticks_x = list(range(0, domain.cols, step_x))
        ax.set_xticks(ticks_x)
        ax.set_xticklabels([str(t + 1) for t in ticks_x])

    if domain.rows <= 40:
        ax.set_yticks(range(domain.rows))
        ax.set_yticklabels(range(1, domain.rows + 1))
    else:
        step_y = max(1, domain.rows // 20)
        ticks_y = list(range(0, domain.rows, step_y))
        ax.set_yticks(ticks_y)
        ax.set_yticklabels([str(t + 1) for t in ticks_y])

    ax.set_xlabel("Colonne")
    ax.set_ylabel("Righe")
    ax.set_title("Labirinto - mappa", fontsize=12)
    ax.grid(which="major", color="white", linestyle="-", linewidth=0.8)
    ax.legend(loc="upper right")
    ax.set_aspect("equal")
    enable_scroll_zoom(ax)
    ax.text(0.01, 1.01, "Usa rotellina per zoomare, trascina per spostarti", transform=ax.transAxes, fontsize=9, color="#444444", va="bottom")
    plt.tight_layout()

    if save:
        fig.savefig(save, dpi=180)
        print(f"\nGrafico salvato in: {save}")
    else:
        plt.show()


def puzzle_to_rows(state: Sequence[int]) -> List[List[int]]:
    n = int(len(state) ** 0.5)
    return [list(state[i: i + n]) for i in range(0, len(state), n)]


def pick_keyframes(states: Sequence[Sequence[int]], max_frames: int = 12) -> List[Tuple[int, Sequence[int]]]:
    if len(states) <= max_frames:
        return [(i, s) for i, s in enumerate(states)]

    idxs = sorted(set(int(round(i * (len(states) - 1) / (max_frames - 1))) for i in range(max_frames)))
    return [(i, states[i]) for i in idxs]


def plot_puzzle(
    states: Sequence[Sequence[int]],
    result: AlgorithmResult,
    save: Path | None,
    animate: bool,
    delay_ms: int,
) -> None:
    ensure_matplotlib()
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from matplotlib.patches import Rectangle

    n = int(len(states[0]) ** 0.5)
    size_label = f"Puzzle {n*n}"

    if not animate:
        keyframes = list(enumerate(states))
        cols = min(6, max(3, int(len(keyframes) ** 0.5)))
        rows = (len(keyframes) + cols - 1) // cols

        fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 3.6 * rows))
        if rows == 1 and cols == 1:
            axes = [[axes]]
        elif rows == 1:
            axes = [axes]
        elif cols == 1:
            axes = [[ax] for ax in axes]

        for ax in [a for row_axes in axes for a in row_axes]:
            ax.axis("off")

        for i, (step, state) in enumerate(keyframes):
            r = i // cols
            c = i % cols
            ax = axes[r][c]
            ax.set_xlim(0, n)
            ax.set_ylim(0, n)
            ax.set_aspect("equal")
            ax.axis("off")

            rowsN = puzzle_to_rows(state)
            for rr in range(n):
                for cc in range(n):
                    val = rowsN[rr][cc]
                    y = n - 1 - rr
                    if val == 0:
                        fill = "#eef2f5"
                        text = ""
                    else:
                        fill = "#5a8f7b"
                        text = str(val)
                    rect = Rectangle((cc, y), 1, 1, facecolor=fill, edgecolor="#1f2d3a", linewidth=1.8)
                    ax.add_patch(rect)
                    if text:
                        ax.text(cc + 0.5, y + 0.5, text, ha="center", va="center", color="white", fontsize=14, weight="bold")

            ax.set_title(f"Step {step}", fontsize=10)

        fig.suptitle(f"{size_label} - {len(result.actions)} mosse | costo={result.cost} | tempo={result.time_s:.3f}s", fontsize=14)
        plt.tight_layout()

        if save:
            fig.savefig(save, dpi=180)
            print(f"\nGrafico salvato in: {save}")
        else:
            plt.show()
        return

    n = int(len(states[0]) ** 0.5)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect("equal")
    ax.axis("off")

    tile_rects = []
    tile_texts = []
    for rr in range(n):
        for cc in range(n):
            y = n - 1 - rr
            rect = Rectangle((cc, y), 1, 1, facecolor="#eef2f5", edgecolor="#1f2d3a", linewidth=2)
            ax.add_patch(rect)
            txt = ax.text(cc + 0.5, y + 0.5, "", ha="center", va="center", color="white", fontsize=20, weight="bold")
            tile_rects.append(rect)
            tile_texts.append(txt)

    size_label = f"Puzzle {n*n}"

    def set_state(step: int):
        state = states[step]
        for idx, val in enumerate(state):
            if val == 0:
                tile_rects[idx].set_facecolor("#eef2f5")
                tile_texts[idx].set_text("")
            else:
                tile_rects[idx].set_facecolor("#5a8f7b")
                tile_texts[idx].set_text(str(val))
        ax.set_title((f"{size_label} - step {step}/{len(states) - 1}" f" | costo={result.cost} | tempo={result.time_s:.3f}s"), fontsize=12)
        return tile_rects + tile_texts

    ani = FuncAnimation(fig, set_state, frames=len(states), interval=delay_ms, repeat=False, blit=False)
    fig._ani = ani
    plt.tight_layout()

    if save and is_animation_path(save):
        if save.suffix.lower() == ".gif":
            try:
                from matplotlib.animation import PillowWriter
            except ImportError:
                raise RuntimeError("Per salvare GIF serve Pillow: pip install pillow")
            fps = max(1, int(round(1000 / max(1, delay_ms))))
            ani.save(save, writer=PillowWriter(fps=fps), dpi=140)
        else:
            fps = max(1, int(round(1000 / max(1, delay_ms))))
            ani.save(save, fps=fps, dpi=140)
        print(f"\nAnimazione salvata in: {save}")
    elif save:
        set_state(len(states) - 1)
        fig.savefig(save, dpi=180)
        print(f"\nSalvato frame finale in: {save}")
    else:
        plt.show()


def plot_puzzle_preview(state: Sequence[int], save: Path | None) -> None:
    ensure_matplotlib()
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.set_aspect("equal")
    ax.axis("off")

    rows3 = puzzle_to_rows(state)
    for rr in range(3):
        for cc in range(3):
            val = rows3[rr][cc]
            y = 2 - rr
            if val == 0:
                fill = "#eef2f5"
                text = ""
            else:
                fill = "#5a8f7b"
                text = str(val)
            rect = Rectangle((cc, y), 1, 1, facecolor=fill, edgecolor="#1f2d3a", linewidth=1.8)
            ax.add_patch(rect)
            if text:
                ax.text(cc + 0.5, y + 0.5, text, ha="center", va="center", color="white", fontsize=14, weight="bold")

    ax.set_title("Puzzle 8 - mappa iniziale", fontsize=14)
    plt.tight_layout()

    if save:
        fig.savefig(save, dpi=180)
        print(f"\nGrafico salvato in: {save}")
    else:
        plt.show()


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualizza i risultati degli algoritmi Prolog")
    parser.add_argument("--domain", choices=["labirinto", "puzzle8", "puzzle15"], required=True, help="Dominio da risolvere")
    parser.add_argument("--algo", choices=["astar", "idastar"], default="astar", help="Algoritmo di ricerca")
    parser.add_argument("--show", action="store_true", help="Mostra la visualizzazione grafica")
    parser.add_argument("--map-only", action="store_true", help="Mostra solo la mappa iniziale del dominio, senza eseguire la ricerca")
    parser.add_argument("--delay-ms", type=int, default=2, help="Delay tra i passaggi dell'animazione in millisecondi (tenuto solo per compatibilita')")
    parser.add_argument("--static", action="store_true", help="Disattiva l'animazione e mostra solo grafico statico")
    parser.add_argument("--save", type=str, default="", help="Percorso output: PNG per frame statico, GIF/MP4 per animazione")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parents[2]

    try:
        save_path = Path(args.save).expanduser().resolve() if args.save else None
        if args.map_only:
            if args.domain == "labirinto":
                domain = parse_maze_domain(root)
                plot_maze_preview(domain, save_path)
            else:
                domain = parse_puzzle_domain(root, args.domain)
                plot_puzzle_preview(domain.start, save_path)
            return 0

        result = run_prolog(root, args.domain, args.algo)
        print_report(args.domain, args.algo, result)

        if not args.show and not args.save:
            return 0

        animate = False

        if args.domain == "labirinto":
            domain = parse_maze_domain(root)
            path = reconstruct_maze_path(domain.start, result.actions)
            if path[-1] not in domain.goals:
                print("\nAttenzione: l'ultimo stato ricostruito non coincide con il goal atteso.", file=sys.stderr)
            plot_maze(domain, path, result, save_path, animate=animate, delay_ms=args.delay_ms)
        else:
            domain = parse_puzzle_domain(root, args.domain)
            states = reconstruct_puzzle_states(domain.start, result.actions)
            if states[-1] != domain.goal:
                print("\nAttenzione: l'ultimo stato ricostruito non coincide con il goal atteso.", file=sys.stderr)
            plot_puzzle(states, result, save_path, animate=animate, delay_ms=args.delay_ms)

        return 0

    except Exception as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
