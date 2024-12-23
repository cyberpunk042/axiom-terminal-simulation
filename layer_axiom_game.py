import curses
import logging
import math
import plotly.graph_objects as go
import sys
import random

# Other Configurations
LOG_FILENAME = "layer_axiom_game.log"
OUTPUT_FILENAME = "matrix_visualization.html"

logging.basicConfig(
    filename=LOG_FILENAME,
    filemode="w",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

DEFAULT_CHAR = "◦" # "\u25E6"  # Unicode bullet character
CENTER_CHAR = "O"

# Configuration Section
# =====================

# Visualization Modes for Each Layer
LAYER_VISUALIZATION_MODES = {
    "layer_0": "markers",         # Options: "lines", "markers", "text", "lines+markers"
    "layer_1": "lines+markers",
    "layer_1_plus": "lines",
}

# Axiom Settings
AXIOM_CONFIGS = {
    'A': {'color': 'red', 'label': 'A (XY plane)', 'opacity': 1},
    'B': {'color': 'blue', 'label': 'B (YZ plane)', 'opacity': 0},
    'C': {'color': 'green', 'label': 'C (XZ plane)', 'opacity': 0},
    'D': {'color': 'purple', 'label': 'D (Diagonal plane Y1)', 'opacity': 0},
    'E': {'color': 'brown', 'label': 'E (Diagonal plane Y2)', 'opacity': 1},
    'F': {'color': 'black', 'label': 'F (Diagonal plane Y3)', 'opacity': 0},
    'H': {'color': 'purple', 'label': 'H (Diagonal plane -Y1)', 'opacity': 0},
    'I': {'color': 'brown', 'label': 'I (Diagonal plane -Y2)', 'opacity': 1},
    'J': {'color': 'black', 'label': 'J (Diagonal plane -Y3)', 'opacity': 0},
}

LAYER0_OPACITY = 1
LAYER1_OPACITY = 1

# Prefill Settings
PREFILL = True
FILL_MODE = "full"  # Options: "full", "partial", "random"
FILLS = {
    'A': ['B'],
    'B': ['B'],
    'C': ['C'],
    'D': ['D'],
    'E': ['E'],
    'F': ['F'],
    'H': ['H'],
    'I': ['I'],
    'J': ['J'],
}

# =====================
# End Configuration Section

# Logging setup
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode="w",
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Global Data
current_layer = 0
current_axiom = 'A'
cursor_x, cursor_y = 0, 0
data = {}

def layer_dimension(layer):
    return 2 * layer + 1

def create_layer_axiom(layer, axiom):
    dim = layer_dimension(layer)
    grid = [[DEFAULT_CHAR for _ in range(dim)] for _ in range(dim)]
    read_only = [[False for _ in range(dim)] for _ in range(dim)]

    if layer == 0:
        grid[0][0] = CENTER_CHAR
        read_only[0][0] = False
    else:
        ensure_layer_axiom(layer - 1, axiom)
        prev_grid, prev_read_only = data[(layer - 1, axiom)]
        prev_dim = layer_dimension(layer - 1)
        offset = (dim - prev_dim) // 2

        for py in range(prev_dim):
            for px in range(prev_dim):
                ch = prev_grid[py][px]
                if ch == CENTER_CHAR:
                    ch = ' '
                grid[py + offset][px + offset] = ch
                read_only[py + offset][px + offset] = True

    data[(layer, axiom)] = (grid, read_only)

def ensure_layer_axiom(layer, axiom):
    if (layer, axiom) not in data:
        create_layer_axiom(layer, axiom)

def get_outer_ring_cells(layer, axiom):
    grid, ro = data[(layer, axiom)]
    dim = layer_dimension(layer)
    center = layer
    if layer == 0:
        ch = grid[0][0]
        return [(0, 0, ch)]
    ring = []
    N = layer
    for y in range(-N, N + 1):
        for x in range(-N, N + 1):
            if max(abs(x), abs(y)) == N:
                gx = x + center
                gy = y + center
                ch = grid[gy][gx]
                if ch in [' ', '', DEFAULT_CHAR]:
                    continue
                ring.append((x, y, ch))
    return ring

def calculate_coordinates(axiom, layer, angle, factor=math.sqrt(2) / 2):
    cosθ, sinθ = math.cos(angle), math.sin(angle)
    if axiom == 'A':  # XY plane
        return layer * cosθ, layer * sinθ, 0
    elif axiom == 'B':  # YZ plane
        return 0, layer * cosθ, layer * sinθ
    elif axiom == 'C':  # XZ plane
        return layer * cosθ, 0, layer * sinθ
    elif axiom == 'D':  # Diagonal plane Y1
        return layer * cosθ, layer * sinθ * factor, layer * sinθ * factor
    elif axiom == 'E':  # Diagonal plane Y2
        return layer * sinθ * factor, layer * cosθ, layer * sinθ * factor
    elif axiom == 'F':  # Diagonal plane Y3
        return layer * sinθ * factor, layer * sinθ * factor, layer * cosθ
    elif axiom == 'H':  # Diagonal plane -Y1
        return layer * cosθ, layer * sinθ * factor, -layer * sinθ * factor
    elif axiom == 'I':  # Diagonal plane -Y2
        return -layer * sinθ * factor, layer * cosθ, layer * sinθ * factor
    elif axiom == 'J':  # Diagonal plane -Y3
        return -layer * sinθ * factor, layer * sinθ * factor, layer * cosθ
    else:
        return 0, 0, 0  # Default case

def render_3d(filename=OUTPUT_FILENAME):
    layer_0_trace = {axiom: {'x': [], 'y': [], 'z': [], 'text': []} for axiom in AXIOM_CONFIGS}
    layer_1_trace = {axiom: {'x': [], 'y': [], 'z': [], 'text': []} for axiom in AXIOM_CONFIGS}
    layer_1_plus_traces = []

    max_layer = max(layer for layer, _ in data.keys())

    for (layer, axiom) in data.keys():
        ring_cells = get_outer_ring_cells(layer, axiom)
        if not ring_cells:
            continue

        ring_cells.sort(key=lambda c: math.atan2(c[1], c[0]))

        x_vals, y_vals, z_vals, text_vals = [], [], [], []
        for i, (ox, oy, ch) in enumerate(ring_cells):
            angle = 2 * math.pi * i / len(ring_cells)
            x, y, z = calculate_coordinates(axiom, layer, angle)
            x_vals.append(x)
            y_vals.append(y)
            z_vals.append(z)
            text_vals.append(ch)

        if len(x_vals) > 1:
            x_vals.append(x_vals[0])
            y_vals.append(y_vals[0])
            z_vals.append(z_vals[0])

        if layer == 0:
            layer_0_trace[axiom]['x'].extend(x_vals)
            layer_0_trace[axiom]['y'].extend(y_vals)
            layer_0_trace[axiom]['z'].extend(z_vals)
            layer_0_trace[axiom]['text'].extend(text_vals)
        elif layer == 1:
            layer_1_trace[axiom]['x'].extend(x_vals)
            layer_1_trace[axiom]['y'].extend(y_vals)
            layer_1_trace[axiom]['z'].extend(z_vals)
            layer_1_trace[axiom]['text'].extend(text_vals)
        else:
            layer_1_plus_traces.append({
                'axiom': axiom,
                'layer': layer,
                'x': x_vals,
                'y': y_vals,
                'z': z_vals,
                'text': text_vals
            })

    fig = go.Figure()

    for axiom, config in AXIOM_CONFIGS.items():
        fig.add_trace(go.Scatter3d(
            x=layer_0_trace[axiom]['x'],
            y=layer_0_trace[axiom]['y'],
            z=layer_0_trace[axiom]['z'],
            mode=LAYER_VISUALIZATION_MODES['layer_0'],
            text=layer_0_trace[axiom]['text'],
            marker=dict(
                size=10,
                color=config['color'],
                symbol='circle'
            ),
            opacity=LAYER0_OPACITY,
            name=f"Layer 0 - {config['label']}"
        ))

    for axiom, config in AXIOM_CONFIGS.items():
        fig.add_trace(go.Scatter3d(
            x=layer_1_trace[axiom]['x'],
            y=layer_1_trace[axiom]['y'],
            z=layer_1_trace[axiom]['z'],
            mode=LAYER_VISUALIZATION_MODES['layer_1'],
            text=layer_1_trace[axiom]['text'],
            marker=dict(
                size=8,
                color=config['color'],
                symbol='circle'
            ),
            opacity=LAYER1_OPACITY,
            name=f"Layer 1 - {config['label']}"
        ))

    for trace in layer_1_plus_traces:
        config = AXIOM_CONFIGS[trace['axiom']]
        fig.add_trace(go.Scatter3d(
            x=trace['x'],
            y=trace['y'],
            z=trace['z'],
            mode=LAYER_VISUALIZATION_MODES['layer_1_plus'],
            text=trace['text'],
            marker=dict(
                size=5,
                color=config['color'],
                symbol='circle'
            ),
            opacity=config['opacity'],
            name=f"Layer {trace['layer']} - {config['label']}"
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title="X", range=[-max_layer, max_layer]),
            yaxis=dict(title="Y", range=[-max_layer, max_layer]),
            zaxis=dict(title="Z", range=[-max_layer, max_layer]),
        ),
        title="3D Visualization",
        width=1000, height=800
    )

    fig.write_html(filename)
    print(f"Visualization saved to {filename}.")


def is_within_bounds(x, y):
    return (-current_layer <= x <= current_layer and -current_layer <= y <= current_layer)

def is_read_only(x, y):
    grid, ro = data[(current_layer, current_axiom)]
    center = current_layer
    gx = x + center
    gy = y + center
    return ro[gy][gx]

def jump_across(dx, dy):
    global cursor_x, cursor_y
    x, y = cursor_x, cursor_y
    while True:
        nx, ny = x + dx, y + dy
        if not is_within_bounds(nx, ny):
            return False
        if not is_read_only(nx, ny):
            cursor_x, cursor_y = nx, ny
            return True
        x, y = nx, ny

def move_cursor(dx, dy):
    if jump_across(dx, dy):
        return

def insert_char(ch):
    grid, read_only = data[(current_layer, current_axiom)]
    center = current_layer
    gx = cursor_x + center
    gy = cursor_y + center

    if not read_only[gy][gx]:
        grid[gy][gx] = ch

def go_to_layer_axiom(layer, axiom):
    global current_layer, current_axiom, cursor_x, cursor_y
    current_layer = layer
    current_axiom = axiom
    ensure_layer_axiom(current_layer, current_axiom)
    cursor_x, cursor_y = -current_layer, -current_layer

def get_outer_ring_cells(layer, axiom):
    grid, ro = data[(layer, axiom)]
    dim = layer_dimension(layer)
    center = layer
    if layer == 0:
        ch = grid[0][0]
        return [(0,0,ch)]
    ring = []
    N = layer
    for y in range(-N, N+1):
        for x in range(-N, N+1):
            if max(abs(x),abs(y)) == N:
                gx = x+center
                gy = y+center
                ch = grid[gy][gx]
                if ch in [' ', '', DEFAULT_CHAR]:
                    continue
                ring.append((x,y,ch))
    return ring


def draw_interface(stdscr):
    stdscr.clear()
    stdscr.addstr(0,0,f"Layer: {current_layer}, Axiom: {current_axiom}, Pos=({cursor_x},{cursor_y})")
    stdscr.addstr(1,0,"F1=A(XY), F2=B(YZ), F3=C(XZ), F4=D(Diag) | +/-=layers | Arrows=move | Type=insert | Ctrl+D=exit")
    stdscr.addstr(2,0,"Refresh matrix_visualization.html manually.")
    stdscr.addstr(3,0,"A=XY plane, B=YZ plane, C=XZ plane, D=diagonal plane")

    grid, read_only = data[(current_layer, current_axiom)]
    dim = layer_dimension(current_layer)
    center = current_layer

    VIEW_RADIUS = 5
    min_xv = max(cursor_x - VIEW_RADIUS, -current_layer)
    max_xv = min(cursor_x + VIEW_RADIUS, current_layer)
    min_yv = max(cursor_y - VIEW_RADIUS, -current_layer)
    max_yv = min(cursor_y + VIEW_RADIUS, current_layer)

    offset_line = 5
    offset_col = 2

    for draw_y in range(min_yv, max_yv+1):
        row_chars = []
        gy = draw_y + center
        for draw_x in range(min_xv, max_xv+1):
            gx = draw_x + center
            ch = grid[gy][gx]
            display_char = ' ' if read_only[gy][gx] else ch

            if draw_x == cursor_x and draw_y == cursor_y:
                if current_layer == 0 and current_axiom == 'A' and cursor_x == 0 and cursor_y == 0:
                    char = display_char
                else:
                    char = "▮" if display_char != DEFAULT_CHAR else "○"
            else:
                char = display_char

            row_chars.append(char)
        stdscr.addstr(offset_line+(draw_y - min_yv), offset_col, "".join(row_chars))

    stdscr.refresh()

def prefill_layers(mode, fillA, fillB, fillC, fillD, fillE, fillF, fillH, fillI, fillJ):
    # number of layers = max(len(fillA), len(fillB), len(fillC), len(fillD))
    max_layers = max(len(fillA), len(fillB), len(fillC), len(fillD), len(fillE), len(fillF), len(fillH), len(fillI), len(fillJ))
    random.seed(0)

    axioms = ['A','B','C','D','E','F','H','I','J']
    fills = {'A': fillA, 'B': fillB, 'C': fillC, 'D': fillD, 'E': fillE, 'F': fillF, 'H': fillH, 'I': fillI, 'J': fillJ}

    for layer in range(1, max_layers+1):
        for axiom in axioms:
            ensure_layer_axiom(layer, axiom)
            grid, ro = data[(layer, axiom)]
            center = layer
            N = layer

            ring_coords = []
            for y in range(-N, N+1):
                for x in range(-N, N+1):
                    if max(abs(x),abs(y)) == N:
                        gx = x+center
                        gy = y+center
                        if not ro[gy][gx]:
                            ring_coords.append((gx, gy))

            total = len(ring_coords)
            if total == 0:
                continue

            chars_list = fills[axiom]
            # Determine what char to use for full/partial, or how to pick random
            if layer <= len(chars_list):
                base_char = chars_list[layer-1]  # single char for this layer
            else:
                base_char = None

            ########################################
            #TODO: replace default char by nothing
            ########################################
            if mode == 'full':
                # Need a base_char to fill entire ring
                if base_char is not None:
                    for (gx,gy) in ring_coords:
                        if base_char not in [DEFAULT_CHAR]:
                            grid[gy][gx] = base_char

            elif mode == 'partial':
                # Fill half ring cells with base_char if available
                if base_char is not None:
                    #TODO: replace random select here
                    selected = random.sample(ring_coords, total//2)
                    for (gx,gy) in selected:
                        grid[gy][gx] = base_char
                # else no fill if no base_char

            elif mode == 'random':
                # Partial logic: half ring cells chosen
                # each chosen cell gets random char from chars_list
                if len(chars_list) > 0:
                    selected = random.sample(ring_coords, total//2)
                    for (gx,gy) in selected:
                        ch = random.choice(chars_list)
                        grid[gy][gx] = ch
                # if no chars_list empty, no fill


def run(stdscr):
    global current_layer, current_axiom
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)

    go_to_layer_axiom(0, 'A')

    while True:
        render_3d()
        draw_interface(stdscr)

        key = stdscr.getch()
        if key == -1:
            continue
        if key == 4: # Ctrl+D
            break

        if key == curses.KEY_F1:
            go_to_layer_axiom(current_layer, 'A')
        elif key == curses.KEY_F2:
            go_to_layer_axiom(current_layer, 'B')
        elif key == curses.KEY_F3:
            go_to_layer_axiom(current_layer, 'C')
        elif key == curses.KEY_F4:
            go_to_layer_axiom(current_layer, 'D')
        elif key == curses.KEY_F5:
            go_to_layer_axiom(current_layer, 'E')
        elif key == curses.KEY_F6:
            go_to_layer_axiom(current_layer, 'F')
        elif key == curses.KEY_F7:
            go_to_layer_axiom(current_layer, 'H')
        elif key == curses.KEY_F8:
            go_to_layer_axiom(current_layer, 'I')
        elif key == curses.KEY_F9:
            go_to_layer_axiom(current_layer, 'J')
        elif key == ord('+'):
            go_to_layer_axiom(current_layer+1, current_axiom)
        elif key == ord('-'):
            if current_layer > 0:
                go_to_layer_axiom(current_layer-1, current_axiom)
        elif key == curses.KEY_LEFT:
            move_cursor(-1, 0)
        elif key == curses.KEY_RIGHT:
            move_cursor(1, 0)
        elif key == curses.KEY_UP:
            move_cursor(0, -1)
        elif key == curses.KEY_DOWN:
            move_cursor(0, 1)
        elif 32 <= key < 127:
            ch = chr(key)
            insert_char(ch)

if __name__ == "__main__":
    prefill = '--prefill' in sys.argv
    fills = {
        'A': ['B'],
        'B': ['B'],
        'C': ['C'],
        'D': ['D'],
        'E': ['E'],
        'F': ['F'],
        'H': ['H'],
        'I': ['I'],
        'J': ['J'],
    }
    mode = 'full'

    # Parse command-line arguments
    for arg in sys.argv:
        if arg.startswith('--fill') and '=' in arg:
            key = arg.split('=')[0][6:]  # Extract the letter after '--fill'
            if key in fills:
                fills[key] = arg.split('=')[1].split(',')
        elif arg.startswith('--mode='):
            mode = arg.split('=')[1]

    if prefill:
        prefill_layers(mode, *(fills[letter] for letter in sorted(fills)))

    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    print("Exited.")
