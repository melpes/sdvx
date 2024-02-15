import pygame, sys, time, random, csv
from pygame.locals import QUIT, KEYDOWN, KEYUP, K_s, K_d, K_f, K_g, K_LSHIFT, K_RSHIFT, K_LALT, K_RALT, K_j, K_k, K_l, K_SEMICOLON
import numpy as np

# 키 이펙트 그리는 surface 새로 만들어서 투명도 적용하여 반영해야 함
# 노트만 그리는 surface도 추가하여 빈 공간은 완전투명하게 설정하기
# frame 바닥 surface와 덮개 surface 구분하여 만들어서 순서 잘 맞추기 (frame -> notes -> 판정선 + 덮개)
# surface들 각자 그려서 한번에 gs.surface에 그리기
# gs.rate 변경될 때마다 해당 판정 점수 1 올리기

class GameSystem:
    def __init__(self):
        pygame.init()

        self.w = 800
        self.h = self.w * (9 / 16)

        self.max_frame = 30

        self.surface = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption('SDVX')
        self.clock = pygame.time.Clock()

        self.run_main, self.run_ingame = True, True
        self.times = {}
        self.notesumt = [0, 0, 0, 0]

        self.combo, self.combo_effect, self.combo_effect2, self.miss_anim, self.last_combo = 0, 0, 0, 0, 0
        self.combo_time = time.time() + 1

        self.font_combo = pygame.font.Font(
            "freesansbold.ttf", int(self.w / 38 * self.combo_effect2))
        self.combo_text = self.font_combo.render(str(self.combo), False,
                                                 (255, 255, 255))

        self.rate = "PERFECT"
        self.font_rate = pygame.font.Font("freesansbold.ttf", int(self.w / 23))
        self.rate_text = self.font_rate.render(str(self.rate), False, (255, 255, 255))
        self.rate_text = pygame.transform.scale(self.rate_text, (int(self.w / 110 * len(self.rate) * self.combo_effect2), int(self.w / 58 * self.combo_effect * self.combo_effect2)))

        self.font_miss = pygame.font.Font("freesansbold.ttf",
                                          int(self.w / 38 * self.miss_anim))
        self.miss_text = self.font_miss.render(str(self.last_combo), False,
                                               (255, 0, 0))

        self.rate_range = {
            "perfect": 100,
            "near": 200,
            "bad": 300,
            "miss": 500
        }

        self.judgement_line = self.h / 12 * 9

        self.bpm = 120
        self.coef_bpm = 120
        self.count_bar = 0
        self.bar = []

        self.note_speed = 2
        self.long_tick = 32 # 비트단위

        self.map_data = []
        self.pop_effect = ((0, 0, 0, 0), (0, 0, 0, 0))

class KeySystem:
    def __init__(self):
        self.effect_level = np.zeros(6, float)
        self.keysets = np.zeros(6, int)
        self.long_keysets = np.zeros(6, int)

class Surfaces:
    def __init__(self, gs):
        self.note_surface = pygame.Surface((gs.w, gs.h), flags=pygame.SRCALPHA)
        self.frame_surface = pygame.Surface((gs.w, gs.h), flags=pygame.SRCALPHA)
        self.key_effect_surface = pygame.Surface((gs.w, gs.h), flags=pygame.SRCALPHA)
        self.triger_effect_surface = pygame.Surface((gs.w, gs.h), flags=pygame.SRCALPHA)
        self.effect_surface = pygame.Surface((gs.w, gs.h), flags=pygame.SRCALPHA)

    def refresh(self):
        color_erase = (0, 0, 0, 0)
        self.note_surface.fill(color_erase)
        self.key_effect_surface.fill(color_erase)
        self.triger_effect_surface.fill(color_erase)
        self.effect_surface.fill(color_erase)

def read_map(gs):
    data = []
    with open("map.csv", 'r') as f:
        for line in csv.reader(f):
            if len(line) == 0:
                continue
            if line[0][0] == '#':
                continue
            # float, (int, float), (int, float), ...
            loc, *notes = (v.split(',') for v in line)
            loc = float(loc[0])
            for i, note in enumerate(notes):
                notes[i] = (int(note[0]), float(note[1]))
            data.append((loc, notes))
    gs.map_data = data

def read_sound(gs):
    music = pygame.mixer.Sound("/FLuegeL.mp4")
    music.play()

def play_map(gs, note_datas):
    for line in gs.map_data:
        loc, *notes = line
        notes = notes[0]
        if gs.times["d_present"] * (gs.bpm / gs.coef_bpm) >= loc:
            for n, length in notes:
                sumon_note(gs, n, note_datas, length)
            gs.map_data.pop(0)

def main():
    gs = GameSystem()
    ks = KeySystem()
    sf = Surfaces(gs)
    note_datas = [list() for _ in range(6)]
    gs.times["start"] = time.time()
    gs.times["d_present"] = time.time() - gs.times["start"]
    read_map(gs)
    # read_sound(gs)
    while gs.run_ingame:
        ingame(gs, ks, sf, note_datas)
    return gs.run_main

def ingame(gs, ks, sf, note_datas):
    gs.times["d_present"] = time.time() - gs.times["start"]

    fps = gs.clock.get_fps()
    if fps == 0:
        fps = gs.max_frame

    word_renderings(gs)

    play_map(gs, note_datas)

    for event in pygame.event.get():
        if event.type == QUIT:
            gs.run_main, gs.run_ingame = False, False
        elif event.type == KEYDOWN:
            for i, k in enumerate(
                [K_s, K_d, K_l, K_SEMICOLON, K_LSHIFT, K_RSHIFT]):
                if event.key == k:
                    ks.keysets[i] = 1
                    if len(note_datas[i]) != 0:
                        if abs(gs.times["d_present"] - note_datas[i][0][1]) <= gs.rate_range["miss"] / 1000:
                            rating(gs, ks, sf, i, note_datas)
                            if note_datas[i][0][2] == 0:
                                note_datas[i].pop(0)
                        elif 0 < gs.times["d_present"] - note_datas[i][0][1] < gs.coef_bpm / gs.bpm * (note_datas[i][0][2]):
                            ks.long_keysets[i] = 1
            for i, k in enumerate([K_j, K_k, K_f, K_g, K_RALT, K_LALT]):
                if event.key == k:
                    ks.keysets[i] = 1
                    if len(note_datas[i]) != 0:
                        if abs(gs.times["d_present"] -
                               note_datas[i][0][1]) <= gs.rate_range["miss"] / 1000:
                            rating(gs, ks, sf, i, note_datas)
                            if note_datas[i][0][2] == 0:
                                note_datas[i].pop(0)
        elif event.type == KEYUP:
            for i, k in enumerate(
                [K_s, K_d, K_l, K_SEMICOLON, K_LSHIFT, K_RSHIFT]):
                if event.key == k:
                    ks.keysets[i] = 0
            for i, k in enumerate([K_j, K_k, K_f, K_g, K_RALT, K_LALT]):
                if event.key == k:
                    ks.keysets[i] = 0

    sf.refresh()

    draw_frame(gs, sf)
    gradation_key_effects(gs, ks, fps)
    key_effects(gs, ks, sf)
    spawn_bar(gs, sf)
    update_notes(gs, ks, sf, note_datas)
    draw_notes(gs, sf, note_datas)
    text_animation(gs, fps)

    bliting(gs, sf)

    pygame.display.update()
    gs.clock.tick(gs.max_frame)

def draw_frame(gs, sf):
    border_width = gs.w / 100

    rect = pygame.Rect(0, 0, 0, 0)
    rect.size = gs.w / 4 + border_width * 2, gs.h + int(border_width * 2)
    rect.center = gs.w / 2, gs.h / 2
    pygame.draw.rect(sf.frame_surface, (255, 255, 255), rect, int(border_width))
    rect.size = gs.w / 4, gs.h
    rect.center = gs.w / 2, gs.h / 2
    pygame.draw.rect(sf.frame_surface, (0, 0, 50), rect)

def bliting(gs, sf):
    gs.surface.fill((0, 0, 0))
    gs.surface.fill((70, 49, 49))
    gs.surface.blit(sf.frame_surface, (0, 0))
    gs.surface.blit(sf.triger_effect_surface, (0, 0))
    gs.surface.blit(sf.key_effect_surface, (0, 0))
    gs.surface.blit(sf.note_surface, (0, 0))
    gs.surface.blit(sf.effect_surface, (0, 0))
    pygame.draw.rect(gs.surface, *gs.pop_effect)
    pygame.draw.rect(gs.surface, (0, 0, 0), (gs.w / 2 - gs.w / 8, gs.judgement_line + gs.h / 10, gs.w / 4, gs.h / 4 - gs.h / 10)) # 가림막
    pygame.draw.rect(gs.surface, (255, 255, 255), (gs.w / 2 - gs.w / 8, gs.judgement_line + gs.h / 10, gs.w / 4, gs.h / 4 - gs.h / 10), int(gs.h / 100)) # 가림막 틀
    pygame.draw.rect(gs.surface, (255, 255, 255), (gs.w / 2 - gs.w / 8, gs.judgement_line, gs.w / 4, gs.h / 4), int(gs.h / 200)) # 판정선
    blit_letters(gs)

def rating(gs, ks, sf, n, note_datas):
    if note_datas[n][0][2] > 0:
        if abs(gs.times["d_present"] - note_datas[n][0][1]) <= gs.rate_range["near"] / 1000:
            ks.long_keysets[n] = 1
            gs.combo += 1
            gs.combo_effect = 0.2
            gs.combo_time = gs.times["d_present"] + 1
            gs.combo_effect2 = 1.3
            gs.rate = "PERFECT"
        else:
            ks.long_keysets[n] = 0
            gs.last_combo = gs.combo
            gs.miss_anim = 1
            gs.combo = 0
            gs.combo_effect = 0.2
            gs.combo_time = gs.times["d_present"] + 1
            gs.combo_effect2 = 1.3
            gs.rate = "miss"
    elif abs(gs.times["d_present"] - note_datas[n][0][1]) <= gs.rate_range["perfect"] / 1000:
        gs.combo += 1
        gs.combo_effect = 0.2
        gs.combo_time = gs.times["d_present"] + 1
        gs.combo_effect2 = 1.3
        gs.rate = "PERFECT"
        pop_effect(gs, sf, n, "PERFECT", note_datas)
    elif abs(gs.times["d_present"] -
             note_datas[n][0][1]) <= gs.rate_range["near"] / 1000:
        gs.combo += 1
        gs.combo_effect = 0.2
        gs.combo_time = gs.times["d_present"] + 1
        gs.combo_effect2 = 1.3
        gs.rate = "near"
        pop_effect(gs, sf, n, "near", note_datas)
    elif abs(gs.times["d_present"] -
             note_datas[n][0][1]) <= gs.rate_range["bad"] / 1000:
        gs.last_combo = gs.combo
        gs.miss_anim = 1
        gs.combo = 0
        gs.combo_effect = 0.2
        gs.combo_time = gs.times["d_present"] + 1
        gs.combo_effect2 = 1.3
        gs.rate = "bad"
        pop_effect(gs, sf, n, "bad", note_datas)
    else:
        gs.last_combo = gs.combo
        gs.miss_anim = 1
        gs.combo = 0
        gs.combo_effect = 0.2
        gs.combo_time = gs.times["d_present"] + 1
        gs.combo_effect2 = 1.3
        gs.rate = "miss"
        pop_effect(gs, sf, n, "miss", note_datas)

def pop_effect(gs, sf, n, rate, note_datas):
    if rate == "PERFECT":
        color = (255, 212, 0, gs.combo_effect * 150)
    elif rate == "near":
        color = (0, 0, 0, gs.combo_effect * 150)
    elif rate == "bad":
        color = (77, 14, 28, gs.combo_effect * 150)
    elif rate == "miss":
        color = (200, 20, 20, gs.combo_effect * 150)
    rect = pygame.Rect(0, 0, 0, 0)
    rect.size = gs.w / 16, gs.h / 50
    rect.centerx = gs.w / 2 - gs.w / 8 + gs.w / 32 + gs.w / 16 * n
    rect.centery = note_datas[n][0][0]
    gs.pop_effect = (color, rect)

def word_renderings(gs):
    gs.font_combo = pygame.font.Font("freesansbold.ttf", int(gs.w / 38 * gs.combo_effect2))
    gs.combo_text = gs.font_combo.render(str(gs.combo), False, (255, 255, 255))

    gs.font_rate = pygame.font.Font("freesansbold.ttf", int(gs.w / 23))
    gs.rate_text = gs.font_rate.render(str(gs.rate), False, (255, 255, 255))
    gs.rate_text = pygame.transform.scale(gs.rate_text, (int(gs.w / 110 * len(gs.rate) * gs.combo_effect2), int(gs.w / 58 * gs.combo_effect * gs.combo_effect2)))

    gs.font_miss = pygame.font.Font("freesansbold.ttf", int(gs.w / 38 * gs.miss_anim))
    gs.miss_text = gs.font_miss.render(str(gs.last_combo), False, (255, 0, 0))

def spawn_bar(gs, sf):
    # play_map 완성하면 gs.count_bar 제거하고 play_map의 마디 세는 변수 공유하기
    if gs.times["d_present"] >= gs.coef_bpm / gs.bpm * gs.count_bar:
        gs.count_bar += 1
        gs.bar.append([0, gs.times["d_present"] + 2])
    rect = pygame.Rect(0, 0, 0, 0)
    for bar in gs.bar:
        bar[0] = gs.judgement_line + (gs.times["d_present"] - bar[1]) * 350 * gs.note_speed * (gs.h / 900)
        if bar[0] >= gs.h:
            gs.bar.pop(0)
        rect.size = (gs.w / 4, gs.h / 200)
        rect.centerx = gs.w / 2
        rect.centery = bar[0]
        pygame.draw.rect(sf.note_surface, (255, 255, 255), rect)

def sumon_note(gs, n, note_datas, length=0):
    ty = 0
    tst = gs.times["d_present"] + 2

    start_tick = -(-(gs.rate_range["perfect"] / 1000) // (gs.coef_bpm / (gs.bpm * gs.long_tick/4)) )
    note_datas[n].append([ty, tst, length, start_tick]) # 노트 y좌표, 노트가 판정선에 도착하는 시간, 노트 길이(단노트는 0), 롱노트일 경우 틱수 계산용 정수

def gradation_key_effects(gs, ks, fps):
    ks.effect_level += (ks.keysets - ks.effect_level) / (2 * (gs.max_frame / fps))

def text_animation(gs, fps):
    if gs.times["d_present"] > gs.combo_time:
        gs.combo_effect += (0 - gs.combo_effect) / (7 * gs.max_frame / fps)
    if gs.times["d_present"] < gs.combo_time:
        gs.combo_effect += (1 - gs.combo_effect) / (7 * gs.max_frame / fps)

    gs.combo_effect2 += (2 - gs.combo_effect2) / (7 * gs.max_frame / fps)
    gs.miss_anim += (4 - gs.miss_anim) / (14 * gs.max_frame / fps)

def key_effects(gs, ks, sf):
    n = 20
    for i in range(n):
        for j in range(4):
            c1 = 40 - (40 / (n - 1) * i) + 20
            color = (c1, c1, c1, 255 * ks.effect_level[j])
            rect = pygame.Rect(0, 0, 0, 0)
            rect.width = gs.w / 16
            rect.height = gs.h / (n * 1.5)
            rect.centerx = gs.w / 2 - gs.w / 8 + gs.w / 32 + gs.w / 16 * j
            rect.bottom = gs.judgement_line - gs.h / (n * 1.5) * i
            pygame.draw.rect(sf.key_effect_surface, color, rect)
        for j in (4, 5):
            c1 = (100 - (100 / (n - 1) * i))
            color = (c1, c1 * 0.04, c1 * 0.36, 255 * ks.effect_level[j])
            rect = pygame.Rect(0, 0, 0, 0)
            rect.width = gs.w / 8
            rect.height = gs.h / (n * 1.5)
            rect.centerx = gs.w / 2 - gs.w / 16 + gs.w / 8 * (j - 4)
            rect.bottom = gs.judgement_line - gs.h / (n * 1.5) * i
            pygame.draw.rect(sf.triger_effect_surface, color, rect)

def update_notes(gs, ks, sf, note_datas):
    for i, line in enumerate(note_datas):
        for note in line:
            note[0] = gs.judgement_line + (gs.times["d_present"] - note[1]) * 350 * gs.note_speed * (gs.h / 900)
            if 0 < gs.times["d_present"] - note[1] < gs.coef_bpm / gs.bpm * (note[2]):
                if gs.times["d_present"] - note[1] >= gs.coef_bpm / (gs.bpm * gs.long_tick/4) * note[3]:
                    note[3] += 1
                    if ks.keysets[i] == 1 and ks.long_keysets[i] == 1:
                        gs.combo += 1
                        gs.combo_effect = 0.2
                        gs.combo_time = gs.times["d_present"] + 1
                        gs.combo_effect2 = 1.3
                        gs.rate = "PERFECT"
                    else:
                        gs.last_combo = gs.combo
                        gs.miss_anim = 1
                        gs.combo = 0
                        gs.combo_effect = 0.2
                        gs.combo_time = gs.times["d_present"] + 1
                        gs.combo_effect2 = 1.3
                        gs.rate = "miss"
            if gs.times["d_present"] - note[1] > gs.coef_bpm / gs.bpm * note[2]:
                ks.long_keysets[i] = 0
            if gs.times["d_present"] - note[1] > gs.rate_range["miss"] / 1000 + gs.coef_bpm / gs.bpm * note[2]:
                if note[2] == 0:
                    gs.last_combo = gs.combo
                    gs.miss_anim = 1
                    gs.combo = 0
                    gs.combo_effect = 0.2
                    gs.combo_time = gs.times["d_present"] + 1
                    gs.combo_effect2 = 1.3
                    gs.rate = "miss"
                    pop_effect(gs, sf, i, "miss", note_datas)
                line.pop(0)

def draw_notes(gs, sf, note_datas):
    
    white = (255, 255, 255)
    red = (250, 10, 90)
    rect = pygame.Rect(0, 0, 0, 0)
    for i, line in enumerate(note_datas):
        if i in (4, 5):
            for note in line:
                rect.width = gs.w / 8
                if note[2] == 0:
                    rect.height = gs.h / 50
                    rect.centery = note[0]
                else:
                    rect.height = 350 * gs.note_speed * (gs.h / 900) * gs.coef_bpm / gs.bpm * note[2]
                    rect.bottom = note[0]
                rect.centerx = gs.w / 2 - gs.w / 16 + gs.w / 8 * (i - 4)
                pygame.draw.rect(sf.note_surface, red, rect)
    for i, line in enumerate(note_datas):
        if i in (0, 1, 2, 3):
            for note in line:
                rect.width = gs.w / 16
                if note[2] == 0:
                    rect.height = gs.h / 50
                    rect.centery = note[0]
                else:
                    rect.height = 350 * gs.note_speed * (gs.h / 900) * gs.coef_bpm / gs.bpm * note[2]
                    rect.bottom = note[0]
                rect.centerx = gs.w / 2 - gs.w / 8 + gs.w / 32 + gs.w / 16 * i
                pygame.draw.rect(sf.note_surface, white, rect)

def blit_letters(gs):
    px = gs.w / 2 - gs.rate_text.get_width() / 2
    py = gs.h / 12 * 8 - gs.rate_text.get_height() / 2
    gs.surface.blit(gs.rate_text, (px, py))

    px = gs.w / 2 - gs.combo_text.get_width() / 2
    py = gs.h / 12 * 4 - gs.combo_text.get_height() / 2
    gs.surface.blit(gs.combo_text, (px, py))

    gs.miss_text.set_alpha(255 - (255 / 4) * gs.miss_anim)
    px = gs.w / 2 - gs.miss_text.get_width() / 2
    py = gs.h / 12 * 4 - gs.miss_text.get_height() / 2
    gs.surface.blit(gs.miss_text, (px, py))

if __name__ == "__main__":
    while True:
        run_main = main()
        if run_main == False:
            break
    pygame.quit()
    sys.exit()
