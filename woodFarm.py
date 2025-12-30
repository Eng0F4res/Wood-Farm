import keyboard
import minescript as m
import time
import math
import json
import os


# =========================
# CONFIG LOAD/SAVE
# =========================

CONFIG_FILE  = "wood_farm_config.json"
CONFIG_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)
MAX_RADIUS   = 5   # blocks
WALK_SPEED   = 4.317  # blocks per second

def ask_coord(name):
    print(f"Press '0' to set {name}")
    while True:
        ASK_key_is_pressed = keyboard.is_pressed('0')
        if ASK_key_is_pressed:
            pos = m.player().position
            print(f"{name} set to current player position: {pos}")
            time.sleep(0.5)
            return [int(pos[0]), int(pos[1]), int(pos[2])]
        

def setup_config():
    config = {}
    config["PLAYER_START_POS"] = ask_coord("Player start position")
    config["TREE_BASE_POS"]    = ask_coord("Tree base (bottom-left of 2x2)")
    config["BED_POS"]          = ask_coord("Bed position")
    config["CHEST_POS"]        = ask_coord("Chest position")
    config["STATE"]            = {"TREE_PLANTED": False,"TREE_GROWEN": False}
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)
    print(f"Ok: Config saved to {CONFIG_FILE}")
    return config


def load_or_setup_config():
    if os.path.exists(CONFIG_PATH):
        print(f"Config file found at {CONFIG_PATH}. Load it? (y/n): ")
        while True:
            if keyboard.is_pressed('y'):
                print("Loaded config:", CONFIG_FILE)
                with open(CONFIG_PATH, "r") as f:
                    return json.load(f)
            elif keyboard.is_pressed('n'):
                os.remove(CONFIG_PATH)
                print("Old config deleted. Creating new one...")
                return setup_config()
    else:
        return setup_config()


config = load_or_setup_config()

PLAYER_START_POS = tuple(config["PLAYER_START_POS"])
TREE_BASE_POS    = tuple(config["TREE_BASE_POS"])
BED_POS          = tuple(config["BED_POS"])
CHEST_POS        = tuple(config["CHEST_POS"])

# =========================
# CORE HELPERS
# =========================

def face_offset(face):
    match face:
        case "top":    return (0.5, 1.0, 0.5)
        case "bottom": return (0.5, 0.0, 0.5)
        case "west":   return (1.0, 0.5, 0.5)
        case "east":   return (0.0, 0.5, 0.5)
        case "north":  return (0.5, 0.5, 1.0)
        case "south":  return (0.5, 0.5, 0.0)
        case _:        return (0.5, 0.5, 0.5)
        

def look_at(x, y, z, face="top"):
    ox, oy, oz = face_offset(face)
    m.player_look_at(x + ox, y + oy, z + oz)


def use_block(x, y, z, face="top", hold=0.2):
    look_at(x, y, z, face)
    time.sleep(0.1)
    m.player_press_use(True)
    time.sleep(hold)
    m.player_press_use(False)


def attack_block(x, y, z, face="top", hold=0.3):
    look_at(x, y, z, face)
    time.sleep(0.1)
    m.player_press_attack(True)
    time.sleep(hold)
    m.player_press_attack(False)


def get_target_block_id():
    block = m.player_get_targeted_block()
    if block is None:
        return None
    return block.type.split("[")[0]


def is_log(block_id):
    return block_id is not None and block_id.endswith("_log")


def find_hotbar_item(name_contains):
    inv = m.player_inventory()
    for item in inv:
        if 0 <= item.slot <= 8:
            if name_contains in item.item:
                return item.slot
    return None


def switch_to_item(name_contains):
    slot = find_hotbar_item(name_contains)
    if slot is None:
        return False
    m.player_inventory_select_slot(slot)
    time.sleep(0.1)
    return True


def use_at_player_pos():
    bx, by, bz = PLAYER_START_POS
    use_block(bx, by, bz, "bottom", hold=0.2)


def face_direction(direction):
    px, py, pz = PLAYER_START_POS
    if direction == "east":
        look_at(px + 10, py, pz,face="east")
    elif direction == "west":
        look_at(px - 10, py, pz,face="west")


def move_blocks(target_blocks, direction):
    start = get_pos()

    face_direction(direction)
    m.player_press_forward(True)

    start_time = time.time()

    while True:
        cur = get_pos()
        moved = horizontal_distance(cur, start)

        # Stop when reached
        if moved >= target_blocks - 0.05:
            break

        # Safety timeout
        if time.time() - start_time > (target_blocks / WALK_SPEED) * 2:
            m.player_press_forward(False)
            print("STOP: movement timeout")
            return False

        time.sleep(0.01)

    m.player_press_forward(False)
    return True


def get_pos():
    x, y, z = m.player_position()
    return x, y, z


def block_pos(pos):
    return (
        math.floor(pos[0]),
        math.floor(pos[1]),
        math.floor(pos[2]),
    )

def horizontal_distance(a, b):
    return ((a[0] - b[0])**2 + (a[2] - b[2])**2) ** 0.5


def collect_items_cycle():
    # Activate button
    clear_head_space()
    use_at_player_pos()
    time.sleep(5)

    # Deactivate
    use_at_player_pos()
    time.sleep(2.5)

    # Move away
    clear_head_space()
    if not move_blocks(2.0, "east"):
        return False
    time.sleep(1)

    # Return precisely
    if not move_blocks(2.0, "west"):
        return False
    time.sleep(1)

    if not ensure_back_to_start():
        return False


def clear_head_space():
    px, py, pz = PLAYER_START_POS
    look_at(px, py + 1, pz, "top")
    time.sleep(0.1)

    if "leaves" in (get_target_block_id() or ""):
        print("INFO: Clearing leaves above player")
        attack_block(px, py + 1, pz, "top", hold=1)
        time.sleep(0.5)

# =========================
# 
# =========================


def plant_tree_2x2(x, y, z):
    if not switch_to_item("sapling"):
        return False, "No saplings left"
    
    blocks = [
        (x+1, y, z),
        (x+1, y, z+1),
        (x, y, z),
        (x, y, z+1),
    ]

    for bx, by, bz in blocks:
        use_block(bx, by, bz, "bottom",hold=0.05)
        time.sleep(0.15)
    return True, None


def apply_bonemeal(x, y, z, uses=10):
    if not switch_to_item("bone_meal"):
        return False, "No bonemeal left"
    
    look_at(x, y, z, "bottom")
    time.sleep(0.05)

    for _ in range(uses):
        block_id = get_target_block_id()
        if block_id != "minecraft:spruce_sapling":
            return True, None
        m.player_press_use(True)
        time.sleep(0.05)
        m.player_press_use(False)
        time.sleep(0.25)

    time.sleep(0.5)
    block_id = get_target_block_id()
    if block_id != "minecraft:spruce_sapling":
        return True, None
    
    return False, "Tree did not grow"


def chop_tree(x, y, z, hold = 1):
    if not switch_to_item("_axe"):
        return False, "No axe found"
    
    look_at(x, y, z, "bottom")
    time.sleep(0.1)

    if is_log(get_target_block_id()):
        attack_block(x, y, z, "bottom", hold=hold)
        time.sleep(3)
        return True, None
    
    return False, "No log detected"

# =========================
# VALIDATION
# =========================

def dist(a, b):
    return math.sqrt(
        (a[0] - b[0])**2 +
        (a[1] - b[1])**2 +
        (a[2] - b[2])**2
    )


def validate_radius(player_pos):
    targets = {
        "TREE_BASE_POS": TREE_BASE_POS,
        "BED_POS": BED_POS,
        "CHEST_POS": CHEST_POS,
    }

    for name, pos in targets.items():
        if dist(player_pos, pos) > MAX_RADIUS:
            print(f"ERROR: {name} is out of radius ({MAX_RADIUS})")
            return False
    return True


def sleep(bed_x, bed_y, bed_z):
    world_time = m.world_info().day_ticks % 24000
    print("Current world time:", world_time)
    # If it's not night, do nothing
    if world_time < 13000 :
        return

    # Look at the bed (top face is safest)
    look_at(bed_x, bed_y, bed_z, "bottom")
    time.sleep(0.2)

    # Use the bed
    m.player_press_use(True)
    time.sleep(0.3)
    m.player_press_use(False)

    # Wait until morning
    start = time.time()
    while (m.world_info().day_ticks % 24000) > 1000:
        if time.time() - start > 15:
            print("WARN: Sleep failed or skipped")
            break
        time.sleep(0.5)


def ensure_back_to_start():
    cur_block = block_pos(get_pos())
    if cur_block != PLAYER_START_POS:
        print("STOP: Failed to return to start block")
        print("Current block:", cur_block)
        print("Expected block:", PLAYER_START_POS)
        return False
    return True


def inventory_full():
    inv = m.player_inventory()
    all_slots = 0
    for slot in inv:
        if 0 <= slot.slot <= 35:
            all_slots+=1
    if all_slots == 36:
        return True
    return False


def save_state(tree_planted, tree_growen):
    config["STATE"]["TREE_PLANTED"] = tree_planted
    config["STATE"]["TREE_GROWEN"]  = tree_growen
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)

# =========================
# STARTUP LOGIC
# =========================

def start():
    player = m.player().position
    player_pos = (int(player[0]), int(player[1]), int(player[2]))

    if player_pos != PLAYER_START_POS:
        print("ERROR: Player is not at the starting position:", PLAYER_START_POS)
        return False

    if not validate_radius(player_pos):
        return False

    print("Ok: All positions validated. System ready.")
    return True


def main_loop():
    last_sleep_check = 0
    STATE = config.get("STATE", {})
    tree_planted = STATE.get("TREE_PLANTED", False)
    tree_growen  = STATE.get("TREE_GROWEN", False)
    while True:
        now = time.time()

        # check every 1 minutes (60 seconds)
        if now - last_sleep_check >= 60:
            sleep(BED_POS[0], BED_POS[1], BED_POS[2])
            last_sleep_check = now


        if not tree_planted:
            if inventory_full():
                print("STOP: Inventory full")
                break

            ok, reson = plant_tree_2x2(TREE_BASE_POS[0], TREE_BASE_POS[1], TREE_BASE_POS[2])

            if not ok:
                print("STOP:",reson)
                break
            tree_planted = True
            save_state(tree_planted, tree_growen)
            time.sleep(1)

        elif not tree_growen:
            ok, reson = apply_bonemeal(TREE_BASE_POS[0], TREE_BASE_POS[1], TREE_BASE_POS[2] + 1)

            if not ok:
                print("STOP:",reson)
                break
            tree_growen = True
            save_state(tree_planted, tree_growen)
            time.sleep(1)

        elif tree_growen:
            ok, reson = chop_tree(TREE_BASE_POS[0], TREE_BASE_POS[1], TREE_BASE_POS[2] + 1,hold=0.5)
            clear_head_space()
            if not ok:
                print("STOP:",reson)
                break
            ok = collect_items_cycle()
            if ok is False:
                print("STOP: Position desync after collection")
                break
            tree_planted = False
            tree_growen  = False
            save_state(tree_planted, tree_growen)
            time.sleep(1)

        if keyboard.is_pressed('x'):
            print("STOP: Manual interrupt")
            save_state(tree_planted, tree_growen)
            break

        time.sleep(0.1)


# =========================
# KEY LOOP
# =========================

key_was_pressed = False

while True:
    key_is_pressed = keyboard.is_pressed('-')

    if key_is_pressed and not key_was_pressed:
        if start():
            main_loop()
    if keyboard.is_pressed('='):
        print("Stopping Key Loop.")
        break

    key_was_pressed = key_is_pressed

    time.sleep(0.01)