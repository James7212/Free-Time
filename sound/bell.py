"""
The Bell.

After a great earthquake the whole Earth rings. Its free oscillations
are a set of pure tones with periods of minutes to an hour, each dying
away at its own rate. This plays them, transposed up by one fixed
factor so that the gravest mode becomes a low A, with each mode decaying
exactly as fast, in transposed time, as it does in the ground.

The frequencies and quality factors are the Earth's (see MODES and the
provenance notes). The relative loudness of the modes is my one choice.
"""
import math, numpy as np, wave, json
from scipy.signal import stft
from PIL import Image, ImageDraw, ImageFont

SR = 44100
FONT = "/mnt/skills/examples/canvas-design/canvas-fonts/CrimsonPro-Regular.ttf"

# name, frequency (mHz), Q, excitation (relative), singlets (list of frequency offsets in uHz) or None
MODES = []   # filled in by build_table()


def build_table(table):
    MODES.clear(); MODES.extend(table)


def synth(target_hz_for_gravest, seconds=None, floor_db=-70, seed=0):
    f0 = min(m["f_mHz"] for m in MODES)
    k = target_hz_for_gravest / (f0 * 1e-3)              # transposition factor
    # how long until the slowest-decaying mode has fallen to floor_db
    def tau(m): return m["Q"] / (math.pi * m["f_mHz"] * 1e-3 * k)
    longest = max(tau(m) for m in MODES) * (-floor_db / 20) * math.log(10)
    seconds = seconds or math.ceil(longest) + 2
    n = int(seconds * SR); t = np.arange(n) / SR
    L = np.zeros(n); R = np.zeros(n); rng = np.random.default_rng(seed)
    log = []
    for m in MODES:
        comps = m.get("singlets") or [0.0]
        for off in comps:
            f = (m["f_mHz"] + off * 1e-3) * 1e-3 * k           # Hz, transposed
            env = np.exp(-math.pi * f * t / m["Q"])
            ph = rng.uniform(0, 2 * np.pi)
            s = m["amp"] / len(comps) * np.sin(2 * np.pi * f * t + ph) * env
            pan = 0.5 + 0.35 * math.tanh(off / 3.0) if off else 0.5   # singlets spread across the field
            L += s * math.sqrt(1 - pan); R += s * math.sqrt(pan)
        log.append((m["name"], m["f_mHz"], round((m["f_mHz"] * 1e-3) * k, 2), m["Q"], round(tau(m), 2)))
    a = int(0.004 * SR); L[:a] *= np.linspace(0, 1, a); R[:a] *= np.linspace(0, 1, a)
    return L, R, k, log


def write_wav(path, L, R, peak=0.89):
    m = max(np.abs(L).max(), np.abs(R).max()) + 1e-12
    Li = (L / m * peak * 32767).astype(np.int16); Ri = (R / m * peak * 32767).astype(np.int16)
    inter = np.empty(2 * len(Li), dtype=np.int16); inter[0::2] = Li; inter[1::2] = Ri
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(inter.tobytes())


def spectrogram_png(sig, path, fmax=400, title=""):
    f, t, Z = stft(sig, fs=SR, nperseg=16384, noverlap=16384 * 7 // 8)
    S = 20 * np.log10(np.abs(Z) + 1e-9); S = S[f <= fmax]
    S = np.clip((S - S.max() + 80) / 80, 0, 1)
    im = Image.fromarray((S[::-1] * 255).astype(np.uint8)).resize((2000, 700), Image.BILINEAR).convert("RGB")
    d = ImageDraw.Draw(im); fnt = ImageFont.truetype(FONT, 30)
    d.text((16, 10), f"{title}   0-{fmax} Hz, {t[-1]:.0f} s", font=fnt, fill=(255, 225, 140))
    im.save(path)


# ------------------------------------------------------------------ the table
# Provenance: V = frequency verified from a published PREM table or observation
# found during this session; M = from memory of the PREM catalogue, about three
# significant figures; Q marked (v) verified, (r) a published range or an early
# measurement applied across the range, (m) from memory.
TABLE = [
    dict(name="0S2", f_mHz=0.30927, Q=500,  amp=1.00, prov="f V (PREM 3233.45 s); Q v (~500 observed)", singlets=[-9.2, -4.6, 0.0, 4.6, 9.2]),
    dict(name="0T2", f_mHz=0.37887, Q=250,  amp=0.55, prov="f V (PREM 2639.40 s); Q m"),
    dict(name="2S1", f_mHz=0.4040,  Q=380,  amp=0.35, prov="f M; Q m"),
    dict(name="0S3", f_mHz=0.46851, Q=400,  amp=0.85, prov="f V (PREM 2134.44 s); Q r (360-450 observed)", singlets=[-8.7, -5.8, -2.9, 0.0, 2.9, 5.8, 8.7]),
    dict(name="0T3", f_mHz=0.586,   Q=240,  amp=0.45, prov="f V (observed 0.586 mHz); Q m"),
    dict(name="0S4", f_mHz=0.647,   Q=370,  amp=0.75, prov="f M; Q r (early measurement, constant 0S2-0S9)"),
    dict(name="1S2", f_mHz=0.67986, Q=310,  amp=0.40, prov="f V (PREM 1470.9 s); Q m"),
    dict(name="0S0", f_mHz=0.81431, Q=5319, amp=0.45, prov="f V (PREM 0.81431 mHz); Q v (PREM 5319; 5506 observed)"),
    dict(name="0S5", f_mHz=0.840,   Q=370,  amp=0.65, prov="f M; Q r"),
    dict(name="0S6", f_mHz=1.038,   Q=370,  amp=0.55, prov="f M; Q r"),
    dict(name="0S7", f_mHz=1.232,   Q=370,  amp=0.45, prov="f M; Q r"),
    dict(name="0S8", f_mHz=1.413,   Q=370,  amp=0.38, prov="f M; Q r"),
    dict(name="4S2", f_mHz=1.7224,  Q=300,  amp=0.25, prov="f V (PREM 580.59 s); Q m"),
]

if __name__ == "__main__":
    build_table(TABLE)
    L, R, k, log = synth(55.0)
    write_wav("the-bell.wav", L, R)
    print(f"transposition x{k:,.0f}: one second of audio is {k/86400:.2f} days; piece is {len(L)/SR:.1f} s = {len(L)/SR*k/86400:.0f} days of ringing")
    print(f"{'mode':5s} {'mHz':>8s} {'Hz':>7s} {'Q':>5s} {'tau s':>6s}")
    for name, f, hz, Q, tau in log: print(f"{name:5s} {f:8.5f} {hz:7.2f} {Q:5d} {tau:6.2f}")
    spectrogram_png(L, "the-bell-spectrogram.png", fmax=340, title="The Bell: the Earth's free oscillations, transposed")
    json.dump(TABLE, open("the-bell-modes.json", "w"), indent=1)
    # envelope: RMS in 0.5 s windows, dB, to show the shape of the decay
    mono = (L + R) / 2; win = int(0.5 * SR); n = len(mono) // win
    env = 20 * np.log10(np.sqrt((mono[: n * win].reshape(n, win) ** 2).mean(1)) + 1e-9)
    print("envelope dB at 0,5,10,20,30,45,60,80 s:", [round(float(env[int(s / 0.5)]), 1) for s in [0, 5, 10, 20, 30, 45, 60, 80] if s / 0.5 < n])
