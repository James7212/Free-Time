"""
Nineteen Years.

The tide at a harbour is a sum of cosines, each driven by one piece of
the sky. This takes the real constituents, with their exact periods and
amplitudes typical of a semi-diurnal Atlantic port, and plays the sum as
sound, sped up by a factor of about ten million so that the moon's
twice-daily tide becomes a 220 Hz tone. At that speed one lunar nodal
cycle (18.61 years), after which the whole pattern very nearly repeats,
lasts one minute. The piece is exactly one cycle.

What you hear: a low chord of tones a few hertz apart, beating. The
fast beat (about 8 per second) is the fortnightly spring-neap cycle.
The slower swell under it is the moon's monthly approach and retreat.
The octave above, faint, is the shallow-water overtide. The slow
breathing of the whole thing over the minute is the nodal cycle.
"""
import math, wave, struct
import numpy as np
from PIL import Image, ImageDraw

SR = 44100
H = 3600.0

# name, period (hours), amplitude (m), phase (deg), nodal amplitude factor (cos N coefficient)
# Amplitudes are typical of a large semi-diurnal Atlantic tide; phases are arbitrary.
CONSTITUENTS = [
    ("M2",  12.4206012, 3.00,   0, -0.037),   # principal lunar semidiurnal
    ("S2",  12.0000000, 1.00,  40,  0.000),   # principal solar
    ("N2",  12.6583475, 0.60, 340, -0.037),   # lunar elliptic (moon's distance)
    ("K2",  11.9672348, 0.28,  40,  0.286),   # lunisolar declinational
    ("K1",  23.9344697, 0.11, 160,  0.115),   # lunisolar diurnal
    ("O1",  25.8193387, 0.10, 350,  0.187),   # lunar diurnal
    ("P1",  24.0658902, 0.04, 160,  0.000),   # solar diurnal
    ("Q1",  26.8683567, 0.02, 320,  0.187),   # larger lunar elliptic diurnal
    ("M4",   6.2103006, 0.12,  80, -0.074),   # shallow-water overtide (exactly 2 x M2)
    ("MS4",  6.1033393, 0.06, 120, -0.037),   # shallow-water compound
    ("M6",   4.1402004, 0.03, 200, -0.111),   # shallow-water overtide (3 x M2)
]
NODAL_YEARS = 18.6129

TARGET_M2_HZ = 220.0
speedup = TARGET_M2_HZ * 12.4206012 * H          # real seconds per audio second
duration = NODAL_YEARS * 365.25 * 86400 / speedup
print(f"speed-up x{speedup:,.0f}; one nodal cycle = {duration:.2f} s of audio")

n = int(duration * SR)
t_audio = np.arange(n) / SR
t_real = t_audio * speedup                        # seconds of real tide

# nodal cycle: N goes once round over the piece
N = 2 * np.pi * t_real / (NODAL_YEARS * 365.25 * 86400)

def timbre(phase):
    """A sine with a little 2nd and 3rd harmonic: organ pipe, not test tone."""
    return np.sin(phase) + 0.18 * np.sin(2 * phase) + 0.06 * np.sin(3 * phase)

left = np.zeros(n); right = np.zeros(n); tide_m = np.zeros(n)
for name, period, amp, ph, nodal in CONSTITUENTS:
    f_real = 1.0 / (period * H)
    phase = 2 * np.pi * f_real * t_real + math.radians(ph)
    a = amp * (1.0 + nodal * np.cos(N))
    tide_m += a * np.cos(phase)                    # the actual tide height, for the picture
    s = a * timbre(phase)
    # gentle placement: diurnals a little left, overtides a little right, semidiurnals centred
    pan = -0.25 if period > 20 else (0.25 if period < 8 else 0.0)
    left += s * math.sqrt(0.5 * (1 - pan)); right += s * math.sqrt(0.5 * (1 + pan))

# envelope
env = np.ones(n)
fi, fo = int(4 * SR), int(7 * SR)
env[:fi] = np.sin(np.linspace(0, np.pi / 2, fi)) ** 2
env[-fo:] = np.cos(np.linspace(0, np.pi / 2, fo)) ** 2
left *= env; right *= env
peak = max(np.abs(left).max(), np.abs(right).max())
left = left / peak * 0.89; right = right / peak * 0.89   # about -1 dBFS

with wave.open("/home/user/Free-Time/sound/nineteen-years.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    inter = np.empty(2 * n, dtype=np.int16)
    inter[0::2] = (left * 32767).astype(np.int16); inter[1::2] = (right * 32767).astype(np.int16)
    w.writeframes(inter.tobytes())
print("wrote nineteen-years.wav", f"{n/SR:.1f}s")

# A picture of one month of the tide you are hearing, as a line, on paper.
month = 29.53 * 86400
sel = t_real < month
x = t_real[sel]; y = tide_m[sel]
W, Hh = 2400, 800
img = Image.new("RGB", (W, Hh), (246, 242, 232)); d = ImageDraw.Draw(img)
xs = 60 + (x / month) * (W - 120)
ys = Hh / 2 - y / (abs(y).max() * 1.15) * (Hh / 2 - 60)
step = max(1, len(xs) // 20000)
pts = list(zip(xs[::step], ys[::step]))
d.line([(60, Hh / 2), (W - 60, Hh / 2)], fill=(200, 194, 182), width=1)
d.line(pts, fill=(40, 36, 38), width=2)
img.save("/home/user/Free-Time/sound/one-month.png")
print("wrote one-month.png")
