#!/usr/bin/env python3
"""Générique de début de live GTA 6 — style néon / coucher de soleil, voix grave.

Usage : python3 generer.py            -> vertical 1080x1920 (TikTok)
        python3 generer.py --paysage  -> 1920x1080 (Twitch / YouTube)
Voix : dossier voix/ (ElevenLabs, voix "Gideon" via Higgsfield), une phrase par fichier.
Dépendances : ffmpeg, numpy, pillow, police Bebas Neue.
"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ICI = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(ICI, "_tmp"); os.makedirs(TMP, exist_ok=True)
PAYSAGE = "--paysage" in sys.argv
W, H = (1920, 1080) if PAYSAGE else (1080, 1920)
FPS, SR = 30, 44100
FONT = "/usr/share/fonts/opentype/bebas-neue/BebasNeue-Bold.otf"
SORTIE = os.path.join(ICI, "generique_gta6_live_paysage.mp4" if PAYSAGE else "generique_gta6_live_vertical.mp4")

# ---------------------------------------------------------------- texte / voix
# (texte prononcé, texte affiché, pause après en s)
LIGNES = [
    ("Des années... qu'on attend.", "DES ANNÉES QU'ON ATTEND", 0.5),
    ("Des trailers regardés en boucle.", "DES TRAILERS EN BOUCLE", 0.5),
    ("Des rumeurs... des reports... des nuits entières à y croire.", "DES NUITS À Y CROIRE", 0.9),
    ("Et ce soir...", "ET CE SOIR...", 0.25),
    ("l'attente est terminée.", "L'ATTENTE EST TERMINÉE", 0.7),
    ("On y est. Ensemble.", "ON Y EST. ENSEMBLE.", 0.5),
    ("Bienvenue dans le live.", "BIENVENUE DANS LE LIVE", 0.6),
    ("Jé Té A six.", None, 0.5),
    ("C'est maintenant !", None, 0.0),
]
DROP_LIGNE = 3  # la musique démarre sur "Et ce soir..."
DEBUT_VOIX = 1.2


def lire_wav(p):
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    if w.getnchannels() == 2:
        x = x.reshape(-1, 2).mean(1)
    return x, w.getframerate()


DOSSIER_VOIX = os.path.join(ICI, "voix")  # l01.mp3, l02.mp3… : une phrase par fichier (ElevenLabs "Gideon" via Higgsfield)


def charger_voix(i):
    src, fin = os.path.join(DOSSIER_VOIX, f"l{i + 1:02d}.mp3"), f"{TMP}/l{i}.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-af",
                    "silenceremove=start_periods=1:start_threshold=-40dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-40dB,areverse,"
                    "highpass=f=45,equalizer=f=120:t=q:w=1:g=3,"
                    "acompressor=threshold=-18dB:ratio=3:attack=5:release=150,volume=1.4",
                    "-ac", "1", "-ar", str(SR), fin], check=True)
    return lire_wav(fin)[0]


print("> voix…")
morceaux = [charger_voix(i) for i in range(len(LIGNES))]
pistes, t = [], DEBUT_VOIX
for (dit, affiche, pause), x in zip(LIGNES, morceaux):
    pistes.append((t, x, affiche))
    t += len(x) / SR + pause
T_GTA = pistes[-2][0]
T_PARTI = pistes[-1][0]
DUREE = T_PARTI + 3.2
N = int(DUREE * SR)

# ---------------------------------------------------------------- audio
print("> musique…")
tt = np.arange(N) / SR
rng = np.random.default_rng(6)
BPM = 96; beat = 60 / BPM
mus = np.zeros(N, np.float32)


def env_adsr(n, a=0.01, r=0.3):
    e = np.ones(n, np.float32); na = max(1, int(a * SR)); nr = max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e


def ajoute(sig, t0, gain=1.0):
    i0 = int(t0 * SR)
    if i0 >= N: return
    seg = sig[: N - i0]; mus[i0:i0 + len(seg)] += gain * seg


def saw(f, n):
    ph = (np.arange(n) * f / SR) % 1.0; return (2 * ph - 1).astype(np.float32)


# nappe synthwave (accords Am - F - C - G), chorus léger
accords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 261.63, 329.63], [196.0, 246.94, 293.66]]
mesure = beat * 4
nb = int(DUREE / mesure) + 1
for k in range(nb):
    n = int(mesure * SR)
    s = np.zeros(n, np.float32)
    for f in accords[k % 4]:
        for d in (-0.15, 0.15):
            s += saw(f * (1 + d / 100), n)
    s = np.convolve(s, np.ones(24) / 24, "same")  # filtre doux
    ajoute(s * env_adsr(n, 0.4, 0.5), k * mesure, 0.035)

# basse pulsée en croches à partir du drop
DROP = pistes[DROP_LIGNE][0]
k = 0
while DROP + k * beat / 2 < T_PARTI + 1.0:
    t0 = DROP + k * beat / 2
    f = accords[int(t0 / mesure) % 4][0] / 4
    n = int(beat / 2 * SR)
    s = np.sign(np.sin(2 * np.pi * f * np.arange(n) / SR)).astype(np.float32)
    s = np.convolve(s, np.ones(40) / 40, "same")
    ajoute(s * env_adsr(n, 0.005, 0.15), t0, 0.12); k += 1

# kick + snare
kick_n = int(0.35 * SR); kt = np.arange(kick_n) / SR
kick = (np.sin(2 * np.pi * (45 + 110 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 9)).astype(np.float32)
sn_n = int(0.25 * SR); snare = (rng.standard_normal(sn_n) * np.exp(-np.arange(sn_n) / SR * 18)).astype(np.float32)
k = 0
while DROP + k * beat < T_PARTI + 1.0:
    t0 = DROP + k * beat
    ajoute(kick, t0, 0.55)
    if k % 2 == 1: ajoute(snare, t0, 0.12)
    k += 1

# sirène lointaine au moment "les sirènes hurlent"
t_sir = pistes[3][0] - 0.3; n = int(2.6 * SR); st = np.arange(n) / SR
sir = np.sin(2 * np.pi * np.cumsum(700 + 250 * np.sin(2 * np.pi * 0.9 * st)) / SR).astype(np.float32)
# (sirène retirée : intro plus émotion)

# grondement d'intro + whoosh avant GTA 6 + gros impact
n = int(DEBUT_VOIX * 2 * SR)
rum = np.convolve(rng.standard_normal(n).astype(np.float32), np.ones(300) / 300, "same") * 6
ajoute(rum * np.linspace(0, 1, n) * env_adsr(n, 0.01, 0.8), 0, 0.5)
n = int(1.2 * SR)
wh = np.convolve(rng.standard_normal(n).astype(np.float32), np.ones(8) / 8, "same") * np.linspace(0, 1, n) ** 2
ajoute(wh, T_GTA - 1.2, 0.25)
n = int(2.5 * SR); it = np.arange(n) / SR
boom = (np.sin(2 * np.pi * (35 + 60 * np.exp(-it * 8)) * it) * np.exp(-it * 2.2)).astype(np.float32)
ajoute(boom, T_GTA, 0.9); ajoute(boom, T_PARTI + 0.6, 0.7)

# fondu de fin
fade = int(1.5 * SR); mus[-fade:] *= np.linspace(1, 0, fade)

vx = np.zeros(N, np.float32)
for t0, x, _ in pistes:
    i0 = int(t0 * SR); vx[i0:i0 + len(x)] += x[: N - i0]
np.clip(mus, -1, 1, out=mus)
for nom, sig in (("musique", mus), ("voix", vx)):
    with wave.open(f"{TMP}/{nom}.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(sig, -1, 1) * 32767).astype(np.int16).tobytes())
# voix : réverb + ducking de la musique sous la voix
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{TMP}/voix.wav", "-i", f"{TMP}/musique.wav",
                "-filter_complex",
                "[0]aecho=0.8:0.6:70|160:0.22|0.12,asplit[v][sc];"
                "[1][sc]sidechaincompress=threshold=0.05:ratio=4:release=300[m];"
                "[v][m]amix=inputs=2:normalize=0,alimiter=limit=0.95,pan=stereo|c0=c0|c1=c0[a]",
                "-map", "[a]", f"{TMP}/audio.wav"], check=True)

# ---------------------------------------------------------------- visuel
print("> images…")
S = min(W, H) / 1080  # échelle
HOR = int(H * (0.62 if not PAYSAGE else 0.6))  # ligne d'horizon

# ciel dégradé
y = np.linspace(0, 1, HOR)[:, None]
haut, mil, bas = np.array([20, 6, 45]), np.array([150, 30, 120]), np.array([255, 120, 70])
ciel = np.where(y < 0.6, haut + (mil - haut) * (y / 0.6), mil + (bas - mil) * ((y - 0.6) / 0.4))
fond = np.zeros((H, W, 3), np.float32)
fond[:HOR] = ciel[:, None, :]
fond[HOR:] = np.array([12, 4, 28])

# étoiles
for _ in range(int(220 * S)):
    sx, sy = rng.integers(0, W), rng.integers(0, int(HOR * 0.5))
    fond[sy, sx] = 255

# soleil rayé
R = int(330 * S); cx, cy = W // 2, HOR - int(90 * S)
yy, xx = np.mgrid[0:H, 0:W]
disque = ((xx - cx) ** 2 + (yy - cy) ** 2) < R * R
g = np.clip((yy - (cy - R)) / (2 * R), 0, 1)[..., None]
col_sol = np.array([255, 230, 90]) * (1 - g) + np.array([255, 40, 140]) * g
rel = (yy - cy) / R
bandes = ~((rel > 0.05) & (np.mod((rel - 0.05) * 14 * (1 + rel), 1.0) < 0.28 + rel * 0.4))
masque_sol = disque & bandes & (yy < HOR)
fond[masque_sol] = col_sol[masque_sol]

img = Image.fromarray(fond.astype(np.uint8))
# halo du soleil
halo = Image.new("RGB", (W, H)); ImageDraw.Draw(halo).ellipse([cx - R * 1.3, cy - R * 1.3, cx + R * 1.3, cy + R * 1.3], fill=(255, 60, 120))
halo = halo.filter(ImageFilter.GaussianBlur(120 * S))
img = Image.fromarray(np.clip(np.asarray(img, np.float32) + np.asarray(halo, np.float32) * 0.35, 0, 255).astype(np.uint8))

d = ImageDraw.Draw(img)
# skyline
x = 0
while x < W:
    bw = int(rng.integers(40, 110) * S); bh = int(rng.integers(60, 380) * S)
    if abs(x - cx) < R * 0.6: bh = int(bh * 0.5)
    d.rectangle([x, HOR - bh, x + bw, HOR], fill=(18, 5, 34))
    for wy in range(HOR - bh + int(12 * S), HOR - int(10 * S), int(22 * S)):
        for wx in range(x + int(8 * S), x + bw - int(8 * S), int(16 * S)):
            if rng.random() < 0.18:
                d.rectangle([wx, wy, wx + int(5 * S), wy + int(8 * S)], fill=(255, 200, 120) if rng.random() < 0.7 else (80, 220, 255))
    x += bw + int(rng.integers(0, 10) * S)


PALM = Image.new("L", (W, H), 0); pd = ImageDraw.Draw(PALM)


def palmier(px, base, h, sens=1):
    pts = [(px + sens * h * 0.18 * (i / 30) ** 2, base - h * i / 30) for i in range(31)]
    for i in range(30):
        pd.line([pts[i], pts[i + 1]], fill=255, width=int((34 - i * 0.6) * S))
    tx, ty = pts[-1]
    for a in (-170, -140, -110, -75, -40, -10, 15, 200, 235):
        ar = math.radians(a); L = h * 0.42
        prev = None
        for j in range(25):
            u = j / 24
            fx = tx + math.cos(ar) * L * u
            fy = ty + math.sin(ar) * L * u * 0.6 + (L * 0.55) * u * u
            if prev: pd.line([prev, (fx, fy)], fill=255, width=max(3, int(30 * S * (1 - u) + 4 * S)))
            prev = (fx, fy)
    pd.ellipse([tx - 18 * S, ty - 14 * S, tx + 18 * S, ty + 14 * S], fill=255)


palmier(int(W * 0.08), H, int(H * 0.55), 1)
palmier(int(W * 0.93), H, int(H * 0.47), -1)
if PAYSAGE:
    palmier(int(W * 0.2), H, int(H * 0.36), 1)
MASQUE_PALM = np.asarray(PALM) > 128
FOND = np.asarray(img, np.float32)


def grille(t):
    """grille néon qui défile vers le spectateur"""
    gi = Image.new("RGB", (W, H - HOR)); gd = ImageDraw.Draw(gi)
    hh = H - HOR; col = (255, 40, 200)
    for k in range(-14, 15):
        gd.line([(cx + k * 40 * S, 0), (cx + k * 420 * S, hh)], fill=col, width=max(2, int(3 * S)))
    off = (t * 0.9) % 1.0
    for k in range(14):
        z = (k + off) / 14
        yl = int(hh * z ** 2.2)
        gd.line([(0, yl), (W, yl)], fill=col, width=max(2, int(3 * S * (0.4 + z))))
    arr = np.asarray(gi, np.float32)
    glow = np.asarray(gi.filter(ImageFilter.GaussianBlur(6 * S)), np.float32)
    return np.clip(arr * 0.8 + glow * 1.6, 0, 255)


def calque_texte(txt, taille, couleur, lueur, lettrage=0):
    f = ImageFont.truetype(FONT, int(taille))
    l, t_, r, b = f.getbbox(txt)
    tw = r - l + lettrage * len(txt); th = b - t_
    while tw > W * 0.9:
        taille *= 0.92; f = ImageFont.truetype(FONT, int(taille)); l, t_, r, b = f.getbbox(txt)
        tw = r - l + lettrage * len(txt); th = b - t_
    pad = int(taille * 0.5)
    im = Image.new("RGBA", (int(tw) + 2 * pad, th + 2 * pad), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    if lettrage:
        xx_ = pad
        for c in txt:
            dd.text((xx_ - l, pad - t_), c, font=f, fill=couleur); xx_ += f.getlength(c) + lettrage
    else:
        dd.text((pad - l, pad - t_), txt, font=f, fill=couleur)
    a = np.asarray(im, np.float32)
    lg = np.asarray(im.filter(ImageFilter.GaussianBlur(taille * 0.12)), np.float32)
    lum = np.clip(lg[..., 3:4] / 255 * 1.8, 0, 1)
    al0 = a[..., 3:4] / 255
    rgb = a[..., :3] * al0 + np.array(lueur, np.float32) * (1 - al0)
    alpha = np.clip(al0 + lum * 0.95, 0, 1)
    return rgb, alpha


def coller(frame, calque, cxp, cyp, op=1.0, ech=1.0):
    rgb, al = calque
    if ech != 1.0:
        h0, w0 = al.shape[:2]; nw, nh = max(1, int(w0 * ech)), max(1, int(h0 * ech))
        rgb = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((nw, nh)), np.float32)
        al = np.asarray(Image.fromarray((al[..., 0] * 255).astype(np.uint8)).resize((nw, nh)), np.float32)[..., None] / 255
    h0, w0 = al.shape[:2]; x0, y0 = int(cxp - w0 / 2), int(cyp - h0 / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w0), min(H, y0 + h0)
    if xa >= xb or ya >= yb: return
    r = rgb[ya - y0:yb - y0, xa - x0:xb - x0]; a = al[ya - y0:yb - y0, xa - x0:xb - x0] * op
    zone = frame[ya:yb, xa:xb]; zone[:] = zone * (1 - a) + r * a


print("> calques texte…")
ROSE, CYAN, BLANC = (255, 60, 190), (60, 230, 255), (255, 255, 255)
sous_titres = []
for i, (t0, x, aff) in enumerate(pistes):
    if aff:
        lueur = ROSE if i % 2 == 0 else CYAN
        sous_titres.append((t0, t0 + len(x) / SR + 0.35, calque_texte(aff, 130 * S, BLANC, lueur, int(6 * S))))
C_GTA = calque_texte("GTA 6", 430 * S, (255, 245, 250), ROSE, int(10 * S))
C_LIVE = calque_texte("LIVE", 240 * S, (230, 255, 255), CYAN, int(30 * S))
C_PARTI = calque_texte("C'EST MAINTENANT !", 150 * S, (255, 240, 120), (255, 120, 40), int(6 * S))
C_DIRECT = calque_texte("EN DIRECT", 100 * S, BLANC, (255, 30, 60), int(8 * S))

# logo optionnel affiché derrière "GTA 6 / LIVE" : mets ton fichier logo.png (fond transparent) dans generique/
C_LOGO = None
CHEMIN_LOGO = next((os.path.join(ICI, n) for n in ("logo.png", "logo.webp", "logo.jpg") if os.path.exists(os.path.join(ICI, n))), None)
if CHEMIN_LOGO:
    print("> logo :", os.path.basename(CHEMIN_LOGO))
    lg = Image.open(CHEMIN_LOGO).convert("RGBA")
    lg.thumbnail((int(W * 0.9), int(H * 0.45)), Image.LANCZOS)
    la = np.asarray(lg, np.float32)
    lueur_logo = np.asarray(lg.filter(ImageFilter.GaussianBlur(25 * S)), np.float32)[..., 3:4] / 255
    C_LOGO = (la[..., :3], np.clip(la[..., 3:4] / 255 + lueur_logo * 0.0, 0, 1))

Y_TXT = int(H * 0.30) if not PAYSAGE else int(H * 0.28)
Y_GTA = int(H * 0.30) if not PAYSAGE else int(H * 0.30)


def ease(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3


print("> rendu vidéo…")
ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-i", f"{TMP}/audio.wav", "-c:v", "libx264", "-preset", "medium",
                       "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                       "-movflags", "+faststart", SORTIE], stdin=subprocess.PIPE)
nf = int(DUREE * FPS)
scan = (np.sin(np.arange(H) * 2 * np.pi / 4) * 0.5 + 0.5)[:, None, None] * 0.06  # scanlines VHS

# ---- fond perso : mets tes captures (.jpg/.png) ou tes clips (.mp4/.mov/.mkv) dans generique/fonds/
DOSSIER_FONDS = os.path.join(ICI, "fonds")
IMG_EXT, VID_EXT = (".jpg", ".jpeg", ".png", ".webp"), (".mp4", ".mov", ".mkv", ".webm")
medias = sorted(f for f in (os.listdir(DOSSIER_FONDS) if os.path.isdir(DOSSIER_FONDS) else [])
                if f.lower().endswith(IMG_EXT + VID_EXT))
lecteur_fond = None
if medias:
    print(f"> fond perso : {len(medias)} fichier(s) dans fonds/")
    seg = DUREE / len(medias) + 0.1
    entrees, filtres = [], []
    for i, m in enumerate(medias):
        chemin = os.path.join(DOSSIER_FONDS, m)
        if m.lower().endswith(IMG_EXT):
            entrees += ["-loop", "1", "-t", f"{seg:.2f}", "-i", chemin]
            # léger travelling sur les images fixes
            filtres.append(f"[{i}]scale={int(W*1.12)}:{int(H*1.12)}:force_original_aspect_ratio=increase,"
                           f"crop={W}:{H}:x='(iw-{W})*t/{seg:.2f}':y='(ih-{H})/2',fps={FPS},setsar=1,format=rgb24[v{i}]")
        else:
            entrees += ["-t", f"{seg:.2f}", "-i", chemin]
            filtres.append(f"[{i}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                           f"fps={FPS},setsar=1,format=rgb24,tpad=stop_mode=clone:stop_duration={seg:.2f},"
                           f"trim=duration={seg:.2f}[v{i}]")
    filtres.append("".join(f"[v{i}]" for i in range(len(medias))) + f"concat=n={len(medias)}:v=1:a=0[out]")
    lecteur_fond = subprocess.Popen(["ffmpeg", "-loglevel", "error"] + entrees +
                                    ["-filter_complex", ";".join(filtres), "-map", "[out]",
                                     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    # étalonnage néon : assombri, teinte rose en haut / bleue en bas, vignette
    gy = np.linspace(0, 1, H)[:, None, None]
    TEINTE = np.array([255, 40, 170], np.float32) * (1 - gy) + np.array([40, 120, 255], np.float32) * gy
    vx_, vy_ = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
    VIGNETTE = np.clip(1.15 - 0.55 * (vx_ ** 2 + vy_ ** 2), 0.25, 1)[..., None].astype(np.float32)
dernier_fond = None

for fi in range(nf):
    t = fi / FPS
    if lecteur_fond:
        brut = lecteur_fond.stdout.read(W * H * 3)
        if len(brut) == W * H * 3:
            dernier_fond = np.frombuffer(brut, np.uint8).reshape(H, W, 3).astype(np.float32)
        fr = (dernier_fond * 0.78 + TEINTE * 0.08) * VIGNETTE if dernier_fond is not None else np.zeros((H, W, 3), np.float32)
    else:
        fr = FOND.copy()
        g = grille(t); bas = fr[HOR:]
        bas[:] = g
        fr[MASQUE_PALM] = (14, 3, 26)
    # pulsation des néons sur le beat après le drop
    if t > DROP:
        p = math.exp(-((t - DROP) % beat) * 6)
        fr *= 1 + 0.08 * p
    # sous-titres
    for a, b, cal in sous_titres:
        if a - 0.1 <= t <= b:
            op = ease((t - a + 0.1) / 0.25) * (1 - ease((t - b + 0.25) / 0.25))
            coller(fr, cal, W / 2, Y_TXT + (1 - ease((t - a) / 0.4)) * 30 * S, op)
    # GTA 6 / LIVE
    if t >= T_GTA:
        k = (t - T_GTA)
        ech = 1.0 + 0.6 * math.exp(-k * 9)
        flick = 1.0 if k > 0.4 or int(k * 30) % 3 else 0.4
        if C_LOGO:  # logo derrière le texte, apparition douce + léger zoom
            coller(fr, C_LOGO, W / 2, Y_GTA + 200 * S, ease(k / 0.5) * 0.55, 1.12 - 0.08 * ease(k / 3))
        coller(fr, C_GTA, W / 2 + (rng.normal() * 14 * S if k < 0.25 else 0), Y_GTA, ease(k / 0.12) * flick, ech)
        coller(fr, C_LIVE, W / 2, Y_GTA + 400 * S, ease((k - 0.35) / 0.3), 1.0 + 0.3 * math.exp(-max(k - 0.35, 0) * 8))
        if k > 0.7:
            blink = 1.0 if int(t * 2) % 2 == 0 else 0.55
            coller(fr, C_DIRECT, W / 2 + 25 * S, Y_GTA + 610 * S, ease((k - 0.7) / 0.3) * blink)
            rx, ry = W / 2 - 215 * S, Y_GTA + 610 * S
            rr = 22 * S
            m = ((xx - rx) ** 2 + (yy - ry) ** 2) < rr * rr
            if blink == 1.0: fr[m] = (255, 30, 60)
        # flash
        if k < 0.15: fr += (1 - k / 0.15) * 200
    if t >= T_PARTI:
        k = t - T_PARTI
        coller(fr, C_PARTI, W / 2, H * (0.80 if not PAYSAGE else 0.86), ease(k / 0.2), 1.0 + 0.4 * math.exp(-k * 10))
    # fondu ouverture / fermeture + vignette + scanlines
    fr *= 1 - scan
    fr *= min(1.0, ease(t / 1.4)) * min(1.0, (DUREE - t) / 0.8)
    ff.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
    if fi % 60 == 0: print(f"  {fi}/{nf}", flush=True)
ff.stdin.close(); ff.wait()
print("OK ->", SORTIE, f"({DUREE:.1f}s)")
