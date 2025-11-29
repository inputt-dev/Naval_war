import pygame, sys, math, random
from pygame import gfxdraw

# ============================================================
# CONFIG & WEAPONS (unchanged)
# ============================================================
WORLD_W_KM = 40000
WORLD_H_KM = 20000
PIXELS_PER_KM_ZOOM1 = 0.02

WIN_W, WIN_H = 1400, 900
pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
pygame.display.set_caption("Blue Ocean Victory + Strategic Targets & Economy")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)
small_font = pygame.font.SysFont("Arial", 14)

OCEAN    = (10, 25, 80)
LAND     = (45, 120, 45)
COAST_RED= (255,50,50,80)
SELECTED = (255,255,0)
WHITE    = (255,255,255)
BLACK    = (0,0,0)

# Long-range weapons (unchanged)
WEAPONS = [
    ("NSM/JSM",          185,    250,   15,   800),
    ("LRASM",            560,    450,   8,    3000),
    ("Tomahawk Blk V",   1700,   450,   5,    1800),
    ("PrSM / Typhon",    500,    200,   10,   1200),
    ("Zircon 3M22",      1000,   400,   12,   2500),
    ("Hypersonic CPGS",  3500,   800,   3,    9000),
    ("Strategic HGV",   12000, 2000,   5,   40000),
]

# Building types: (name, color, production_type, rate, hp)
BUILDINGS = {
    "resource":  ("Resource Mine", (0,200,0), "resources", 50, 200),
    "shipyard":  ("Naval Shipyard", (0,150,255), "ships", 0.02, 500),  # fractional ships
    "factory":   ("Weapons Factory", (255,150,0), "weapons", 0.1, 400), # fractional weapons cost refund
    "base":      ("Military Base", (200,0,0), "army", 10, 300),
}

# ============================================================
# Economy globals
# ============================================================
blue_resources = 50000
red_resources = 50000
blue_army_pool = 0
red_army_pool = 0

# ============================================================
# Land + Camera (unchanged)
# ============================================================
def generate_land():
    land = pygame.Surface((WORLD_W_KM, WORLD_H_KM), pygame.SRCALPHA)
    land.fill((0,0,0,0))
    continents = [(10000,8000,8000,6000), (28000,7000,9000,7000),
                  (15000,3000,4000,3000), (20000,14000,6000,4000)]
    for x,y,w,h in continents:
        pygame.draw.ellipse(land, (*LAND,255), (x,y,w,h))
        for _ in range(2000):
            pygame.draw.circle(land, (*LAND,255),
                (x+random.randint(-w//4,w+w//4), y+random.randint(-h//4,h+h//4)),
                random.randint(200,1200))
    return land

land_surface = generate_land()

class Camera:
    def __init__(self):
        self.zoom = 1.0
        self.offset_x = WORLD_W_KM / 2
        self.offset_y = WORLD_H_KM / 2
    def world_to_screen(self, wx, wy):
        x = (wx - self.offset_x) * self.zoom * PIXELS_PER_KM_ZOOM1 + WIN_W//2
        y = (wy - self.offset_y) * self.zoom * PIXELS_PER_KM_ZOOM1 + WIN_H//2
        return x, y
    def screen_to_world(self, sx, sy):
        wx = (sx - WIN_W//2) / (self.zoom * PIXELS_PER_KM_ZOOM1) + self.offset_x
        wy = (sy - WIN_H//2) / (self.zoom * PIXELS_PER_KM_ZOOM1) + self.offset_y
        return wx, wy

camera = Camera()

# ============================================================
# Buildings class
# ============================================================
class Building:
    def __init__(self, x, y, btype, side):
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x-150, y-100, 300, 200)
        self.btype = btype
        self.side = side
        self.name, self.color, self.prod_type, self.rate, self.max_hp = BUILDINGS[btype]
        self.hp = self.max_hp
        self.selected = False

    def damage(self, power):
        global blue_resources, red_resources, blue_army_pool, red_army_pool
        self.hp -= power / 10  # scale damage
        if self.hp <= 0:
            # Destroyed - refund some resources to owner? No, loss
            buildings.remove(self)
        # Visual flash on damage
        self.flash = 20

    def produce(self):
        global blue_resources, red_resources, blue_army_pool, red_army_pool
        if self.side == "BLUE":
            if self.prod_type == "resources":
                blue_resources += self.rate
            elif self.prod_type == "ships":
                if random.random() < self.rate:
                    ships.append(Ship(self.x + random.randint(-200,200), self.y - 300, "BLUE"))
            elif self.prod_type == "weapons":
                blue_resources += int(self.rate * 100)  # refund weapon cost
            elif self.prod_type == "army":
                blue_army_pool += self.rate
        else:
            # RED
            if self.prod_type == "resources":
                red_resources += self.rate
            elif self.prod_type == "ships":
                if random.random() < self.rate:
                    ships.append(Ship(self.x + random.randint(-200,200), self.y - 300, "RED"))
            elif self.prod_type == "weapons":
                red_resources += int(self.rate * 100)
            elif self.prod_type == "army":
                red_army_pool += self.rate

    def draw(self, surf):
        px = (self.rect.centerx - camera.offset_x) * camera.zoom * PIXELS_PER_KM_ZOOM1 + WIN_W//2
        py = (self.rect.centery - camera.offset_y) * camera.zoom * PIXELS_PER_KM_ZOOM1 + WIN_H//2
        if not (0 < px < WIN_W*1.5 and 0 < py < WIN_H*1.5): return

        # Building outline
        size = 40 * camera.zoom
        col = (*self.color, 200) if self.side == "BLUE" else (*self.color, 180)
        if self.flash > 0:
            col = (255,100,100,200)
            self.flash -= 1
        pygame.draw.rect(surf, col, (px-size/2, py-size/2, size, size))
        pygame.draw.rect(surf, BLACK, (px-size/2, py-size/2, size, size), 3)

        if self.selected:
            pygame.draw.rect(surf, SELECTED, (px-size/2, py-size/2, size, size), 4)

        # Label
        txt = small_font.render(self.btype[0].upper(), True, WHITE)
        surf.blit(txt, (px - txt.get_width()/2, py + size/2 + 5))

# ============================================================
# Projectiles - now damage buildings
# ============================================================
class Projectile:
    def __init__(self, start_x, start_y, target_x, target_y, weapon_idx):
        self.x = start_x
        self.y = start_y
        self.tx = target_x
        self.ty = target_y
        self.weapon = WEAPONS[weapon_idx]
        self.t = 0.0
        self.duration = max(1.0, math.hypot(target_x-start_x, target_y-start_y)/2000)  # scale by distance

    def update(self, dt):
        self.t += dt / self.duration
        if self.t >= 1.0:
            # Impact - damage nearest building
            for b in buildings:
                if b.rect.collidepoint(self.tx, self.ty):
                    b.damage(self.weapon[2])
                    break
            return False
        self.x = self.x + (self.tx - self.x) * (self.t**1.2)  # faster arc
        self.y = self.y + (self.ty - self.y) * self.t + (self.t*(1-self.t))*200  # parabola
        return True

    def draw(self, surf):
        px, py = camera.world_to_screen(self.x, self.y)
        pygame.draw.circle(surf, (255,200,0), (int(px), int(py)), max(2, int(8*camera.zoom)))
        if self.t > 0.95:
            rad = int((self.t-0.95)/0.05 * 100 * camera.zoom)
            tx, ty = camera.world_to_screen(self.tx, self.ty)
            pygame.draw.circle(surf, (255,50,50,150), (int(tx),int(ty)), rad, 5)

# ============================================================
# Ship - unchanged except fire checks range vaguely
# ============================================================
class Ship:
    def __init__(self, x, y, side):
        self.x = x; self.y = y
        self.side = side
        self.selected = False
        self.coast_target_rect = None
        self.troops = 800 if side=="BLUE" else 600
        self.weapon_idx = 0
        self.resources = 0  # now national pool used

    def fire(self, tx, ty):
        global blue_resources
        w = WEAPONS[self.weapon_idx]
        dist = math.hypot(tx - self.x, ty - self.y)
        if dist > w[1] * 1.2: return  # out of range
        if blue_resources >= w[4]:
            blue_resources -= w[4]
            projectiles.append(Projectile(self.x, self.y, tx, ty, self.weapon_idx))

    def draw(self, surf):
        px, py = camera.world_to_screen(self.x, self.y)
        if not (0 < px < WIN_W*1.5 and 0 < py < WIN_H*1.5): return
        color = (100,180,255) if self.side=="BLUE" else (255,80,80)
        if self.selected:
            pygame.draw.circle(surf, SELECTED, (int(px),int(py)), 22, 4)
        points = [(px+14,py), (px-10,py+8), (px-10,py-8)]
        pygame.draw.polygon(surf, color, points)
        wname = WEAPONS[self.weapon_idx][0].split()[0]
        txt = small_font.render(wname,1,(255,255,0))
        surf.blit(txt, (px-20, py-30))

# Army - now uses pool for reinforcements (simple)
class Army:
    def __init__(self, x, y, side):
        self.x = x; self.y = y; self.side = side
        self.strength = 400

    def update(self):
        if random.random() < 0.02:
            angle = random.random()*math.pi*2
            self.x += math.cos(angle)*100
            self.y += math.sin(angle)*100

    def draw(self, surf, camera):
        px, py = camera.world_to_screen(self.x, self.y)
        color = (0,100,255) if self.side=="BLUE" else (200,0,0)
        size = int(5 + self.strength/50 * camera.zoom**0.5)
        pygame.draw.circle(surf, color, (int(px),int(py)), size)

# ============================================================
# Globals
# ============================================================
ships = []
projectiles = []
armies = []
buildings = []

# Starting fleets (ships unchanged)
for i in range(14):
    ships.append(Ship(8000 + i*500, 9000 + (i%4)*600, "BLUE"))
for i in range(12):
    ships.append(Ship(32000 + i*600, 8000 + (i%3)*700, "RED"))

# Generate buildings on land
def generate_buildings():
    # Blue left continent
    for _ in range(15):
        buildings.append(Building(random.randint(8000,16000), random.randint(6000,12000), random.choice(list(BUILDINGS.keys())), "BLUE"))
    # Red right continent
    for _ in range(20):
        buildings.append(Building(random.randint(26000,36000), random.randint(5000,13000), random.choice(list(BUILDINGS.keys())), "RED"))

generate_buildings()

selected_fleet = []
coast_sectors = []

def build_coast_sectors():
    global coast_sectors
    step = 1400
    for cx in range(2000, WORLD_W_KM-2000, step):
        for cy in range(1000, WORLD_H_KM-1000, step):
            if any(abs(cx-x)<1200 and abs(cy-y)<1200 for (x,y,_,_) in [(10000,8000,8000,6000),(28000,7000,9000,7000)]):
                owner = "RED" if cx > 22000 else "BLUE"
                coast_sectors.append((pygame.Rect(cx-700, cy-500, 1400, 1000), owner))

build_coast_sectors()

# ============================================================
# Main loop
# ============================================================
dragging = False
last_mouse = (0,0)
game_time = 0

while True:
    dt = clock.tick(60) / 1000.0
    game_time += dt

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        elif e.type == pygame.VIDEORESIZE:
            WIN_W, WIN_H = e.w, e.h
            screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
        elif e.type == pygame.MOUSEWHEEL:
            factor = 1.25 if e.y > 0 else 0.8
            old = camera.zoom
            camera.zoom = max(0.05, min(50, camera.zoom * factor))
            mx, my = pygame.mouse.get_pos()
            wx, wy = camera.screen_to_world(mx, my)
            camera.offset_x = wx - (mx - WIN_W//2) / (camera.zoom * PIXELS_PER_KM_ZOOM1)
            camera.offset_y = wy - (my - WIN_H//2) / (camera.zoom * PIXELS_PER_KM_ZOOM1)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            mx, my = e.pos
            wx, wy = camera.screen_to_world(mx, my)
            if e.button == 1:  # Left: select ships or buildings
                selected_fleet = []
                # Ships first
                for s in ships:
                    if s.side == "BLUE":
                        sx, sy = camera.world_to_screen(s.x, s.y)
                        if math.hypot(sx-mx, sy-my) < 30:
                            s.selected = True
                            selected_fleet.append(s)
                        else:
                            s.selected = False
                if not selected_fleet:
                    # Try buildings
                    for b in buildings:
                        if b.side == "BLUE" and b.rect.collidepoint(wx, wy):
                            b.selected = True
                            for other in buildings:
                                if other != b:
                                    other.selected = False
                            break
                        else:
                            b.selected = False
            elif e.button == 3:  # Right click
                if selected_fleet and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    # Fire!
                    for ship in selected_fleet:
                        ship.fire(wx, wy)
                else:
                    # Assault coast
                    best = None; best_dist = 999999
                    for rect, owner in coast_sectors:
                        if owner != "BLUE":
                            d = math.hypot(rect.centerx-wx, rect.centery-wy)
                            if d < best_dist:
                                best_dist = d
                                best = rect
                    if best:
                        for ship in selected_fleet:
                            ship.coast_target_rect = best
                            ship.selected = False
                        selected_fleet = []
            if e.button in (2, 3) and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                dragging = True
                last_mouse = e.pos
        elif e.type == pygame.MOUSEBUTTONUP:
            if e.button in (2, 3): dragging = False
        elif e.type == pygame.KEYDOWN:
            if selected_fleet and pygame.K_1 <= e.key <= pygame.K_7:
                idx = e.key - pygame.K_1
                if idx < len(WEAPONS):
                    for s in selected_fleet: s.weapon_idx = idx

    # Pan
    if dragging:
        mx, my = pygame.mouse.get_pos()
        dx, dy = mx - last_mouse[0], my - last_mouse[1]
        camera.offset_x -= dx / (camera.zoom * PIXELS_PER_KM_ZOOM1)
        camera.offset_y -= dy / (camera.zoom * PIXELS_PER_KM_ZOOM1)
        last_mouse = (mx, my)

    # Update
    projectiles = [p for p in projectiles if p.update(dt)]
    if int(game_time * 10) % 10 == 0:  # Produce every ~0.1s
        for b in buildings:
            b.produce()

    # Ship movement (add coast_target_rect logic)
    for s in ships:
        if s.coast_target_rect:
            tx, ty = s.coast_target_rect.centerx, s.coast_target_rect.centery
            dx, dy = tx - s.x, ty - s.y
            dist = math.hypot(dx, dy)
            if dist > 5:
                s.x += dx/dist * 0.6 * 60 * dt
                s.y += dy/dist * 0.6 * 60 * dt
            else:
                if s.troops > 0:
                    armies.append(Army(s.x, s.y, s.side))
                    s.troops = 0
                s.coast_target_rect = None

    for a in armies: a.update()

    # Draw
    screen.fill(OCEAN)

    # Land
    scale_w = int(WORLD_W_KM * camera.zoom * PIXELS_PER_KM_ZOOM1)
    scale_h = int(WORLD_H_KM * camera.zoom * PIXELS_PER_KM_ZOOM1)
    land_scaled = pygame.transform.smoothscale(land_surface, (scale_w, scale_h))
    ox = WIN_W//2 - camera.offset_x * camera.zoom * PIXELS_PER_KM_ZOOM1
    oy = WIN_H//2 - camera.offset_y * camera.zoom * PIXELS_PER_KM_ZOOM1
    screen.blit(land_scaled, (ox, oy))

    # Coast sectors
    for rect, owner in coast_sectors:
        if owner == "RED":
            r = pygame.Rect(rect.x * camera.zoom * PIXELS_PER_KM_ZOOM1 + ox,
                            rect.y * camera.zoom * PIXELS_PER_KM_ZOOM1 + oy,
                            rect.w * camera.zoom * PIXELS_PER_KM_ZOOM1,
                            rect.h * camera.zoom * PIXELS_PER_KM_ZOOM1)
            if r.colliderect(screen.get_rect()):
                s = pygame.Surface(r.size, pygame.SRCALPHA)
                s.fill(COAST_RED)
                screen.blit(s, r.topleft)

    # Buildings, armies, projectiles, ships
    for b in buildings: b.draw(screen)
    for a in armies: a.draw(screen, camera)
    for p in projectiles: p.draw(screen)
    for s in ships: s.draw(screen)

    # UI
    ui_w = 500
    ui = pygame.Surface((ui_w, 300), pygame.SRCALPHA)
    ui.fill((0,0,0,180))
    y = 10
    txt = font.render(f"BLUE Resources: ${blue_resources:,} | Army Pool: {int(blue_army_pool)}", True, WHITE)
    ui.blit(txt, (10,y)); y+=25
    txt = font.render(f"RED Resources: ${red_resources:,} | Army Pool: {int(red_army_pool)}", True, (255,100,100))
    ui.blit(txt, (10,y)); y+=25
    txt = font.render("1-7: Weapon | LClick: Select ships/buildings | CTRL+RClick: FIRE on targets!", True, WHITE)
    ui.blit(txt, (10,y)); y+=30
    if selected_fleet:
        w = WEAPONS[selected_fleet[0].weapon_idx]
        txt = font.render(f"Weapon: {w[0]} | Rng:{w[1]}km Pwr:{w[2]}kg CEP:{w[3]}m Cost:${w[4]}", True, (0,255,0))
        ui.blit(txt, (10,y))
    screen.blit(ui, (10,10))

    pygame.display.flip()
