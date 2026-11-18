"""balance_gui.pyw — standalone tkinter chemical equation balancer.
No other files needed.

Understands: nested ()/[]/{} groups, hydrates (CuSO4·5H2O or CuSO4.5H2O),
ions (Fe^3+, SO4^2-, MnO4^-), electrons (e-), state symbols ((s) (l) (g) (aq)),
Unicode subscripts/superscripts (H₂O, Fe³⁺), and equations that already
have coefficients (they're ignored and re-balanced from scratch).
Arrows: ->  -->  =>  =  →  ⇌  <->
"""
import math
import re
import sys
import tkinter as tk
from fractions import Fraction
from tkinter import font as tkfont
from tkinter import ttk

# ── Data ───────────────────────────────────────────────────────────────────

ELEMENTS = set(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni "
    "Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I "
    "Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt "
    "Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr "
    "Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
)

_SUB_IN = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUP_IN = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻", "0123456789+-")
_SUB_OUT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUP_OUT = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")

ARROW = re.compile(r"<?[-=]+>|→|⟶|⇒|⇌|↔|=")
CHARGE = re.compile(r"\^\s*(?:(\d+)([+-])|([+-])(\d+)?)$")
STATE = re.compile(r"\((?:s|l|g|aq)\)$")
CLOSERS = {")": "(", "]": "[", "}": "{"}


# ── Parsing ────────────────────────────────────────────────────────────────

def normalize(s):
    """Turn pasted textbook notation into plain ASCII-ish input."""
    s = s.translate(_SUB_IN)
    s = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+", lambda m: "^" + m.group().translate(_SUP_IN), s)
    s = re.sub(r"[−–—]", "-", s)
    return s.replace("\u00a0", " ").replace("\u2009", " ")


def split_terms(side):
    """Split on '+', except a '+' that is a charge sign (Fe^3+, Fe^+2)."""
    terms, cur = [], ""
    for ch in side:
        if ch == "+" and not re.search(r"\^\d*$", cur):
            terms.append(cur)
            cur = ""
        else:
            cur += ch
    terms.append(cur)
    return [t.strip() for t in terms if t.strip()]


def parse_group(s):
    """Parse a formula with nested brackets into {element: count}."""
    stack, opens = [{}], []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch in "([{":
            stack.append({})
            opens.append(ch)
            i += 1
        elif ch in ")]}":
            if not opens or opens[-1] != CLOSERS[ch]:
                raise ValueError(f"Mismatched bracket '{ch}' in '{s}'")
            opens.pop()
            group = stack.pop()
            i += 1
            j = i
            while j < n and s[j] in "0123456789":
                j += 1
            mul = int(s[i:j]) if j > i else 1
            i = j
            for el, c in group.items():
                stack[-1][el] = stack[-1].get(el, 0) + c * mul
        elif ch.isupper():
            j = i + 1
            while j < n and s[j].islower():
                j += 1
            el = s[i:j]
            if el not in ELEMENTS:
                raise ValueError(f"Unknown element '{el}' in '{s}' (check capitalization)")
            k = j
            while k < n and s[k] in "0123456789":
                k += 1
            stack[-1][el] = stack[-1].get(el, 0) + (int(s[j:k]) if k > j else 1)
            i = k
        elif ch == " ":
            i += 1
        elif ch.islower():
            raise ValueError(f"Element symbols start with a capital letter: '{ch}' in '{s}'")
        else:
            raise ValueError(f"Unexpected character '{ch}' in '{s}'")
    if opens:
        raise ValueError(f"Unclosed bracket '{opens[-1]}' in '{s}'")
    return stack[0]


def parse_formula(f):
    """Formula (with optional hydrate parts) -> {element: count}."""
    total = {}
    for part in re.split(r"[·•∙*.]", f):
        part = part.strip()
        m = re.match(r"(\d+)\s*", part)
        mult = 1
        if m:
            mult = int(m.group(1))
            part = part[m.end():]
        if not part:
            raise ValueError(f"Empty hydrate/formula part in '{f}'")
        for el, c in parse_group(part).items():
            total[el] = total.get(el, 0) + c * mult
    return total


def parse_term(term):
    """One compound -> (label, {element: count}, charge)."""
    # drop any coefficient the user already wrote
    t = re.sub(r"^\s*\d+(?:\.\d+)?\s*(?=[A-Z(\[{e])", "", term.strip())
    if not t:
        raise ValueError(f"Nothing left of '{term.strip()}' after removing its coefficient")
    label = t

    if re.fullmatch(r"e\^?-", t):                      # electron
        return "e^-", {}, -1

    t = STATE.sub("", t).strip()
    t, charge = split_charge(t)
    return label, parse_formula(t), charge


def split_charge(t):
    m = CHARGE.search(t)
    if not m:
        return t, 0
    if m.group(1):
        q, sign = int(m.group(1)), m.group(2)
    else:
        q, sign = int(m.group(4) or 1), m.group(3)
    return t[:m.start()], (q if sign == "+" else -q)


# ── Linear algebra (exact) ─────────────────────────────────────────────────

def rref(matrix):
    M = [[Fraction(x) for x in row] for row in matrix]
    rows, cols = len(M), len(M[0])
    pr, pivots = 0, []
    for c in range(cols):
        found = next((r for r in range(pr, rows) if M[r][c] != 0), -1)
        if found == -1:
            continue
        M[pr], M[found] = M[found], M[pr]
        pivots.append(c)
        s = M[pr][c]
        M[pr] = [x / s for x in M[pr]]
        for r in range(rows):
            if r != pr and M[r][c] != 0:
                f = M[r][c]
                M[r] = [M[r][k] - f * M[pr][k] for k in range(cols)]
        pr += 1
    return M, pivots


# ── Balancer (returns results, never prints) ───────────────────────────────

def pretty(label):
    base, sep, chg = label.partition("^")
    base = re.sub(r"(?<=[A-Za-z)\]}])(\d+)", lambda m: m.group().translate(_SUB_OUT), base)
    return base + (chg.translate(_SUP_OUT) if sep else "")


def balance(equation):
    """Returns (balanced_string, coefficients, verification_lines).
    Raises ValueError with a readable message on failure."""
    eq = normalize(equation).strip()
    parts = ARROW.split(eq)
    if len(parts) != 2:
        raise ValueError("Use exactly one arrow (->, =, →, ⇌) between reactants and products.")

    lhs_terms, rhs_terms = split_terms(parts[0]), split_terms(parts[1])
    if not lhs_terms or not rhs_terms:
        raise ValueError("Need at least one reactant and one product.")

    parsed = [parse_term(t) for t in lhs_terms + rhs_terms]
    labels = [p[0] for p in parsed]
    counts = [p[1] for p in parsed]
    charges = [p[2] for p in parsed]
    nr, n = len(lhs_terms), len(parsed)

    elements = sorted({el for c in counts for el in c})
    if not elements:
        raise ValueError("No elements found — check formula syntax.")

    has_charge = any(charges)
    rows = [[(-c.get(el, 0) if i >= nr else c.get(el, 0)) for i, c in enumerate(counts)]
            for el in elements]
    if has_charge:
        rows.append([(-q if i >= nr else q) for i, q in enumerate(charges)])

    R, pivots = rref(rows)
    free = [c for c in range(n) if c not in pivots]
    if not free:
        raise ValueError("This equation can't be balanced — check the formulas "
                         "(a species may be missing or misspelled).")
    if len(free) > 1:
        raise ValueError(
            f"This equation has {len(free)} independent solutions — it mixes "
            f"{len(free)} separate reactions. Remove species that aren't part of "
            "the same reaction.")

    f = free[0]
    sol = [Fraction(0)] * n
    sol[f] = Fraction(1)
    for i, pc in enumerate(pivots):
        sol[pc] = -R[i][f]

    if all(s <= 0 for s in sol):
        sol = [-s for s in sol]
    if any(s < 0 for s in sol):
        raise ValueError("No all-positive solution — a species is probably on the wrong "
                         "side of the arrow.")
    zero = [pretty(labels[i]) for i, s in enumerate(sol) if s == 0]
    if zero:
        raise ValueError("These species don't take part in a balanced reaction: "
                         + ", ".join(zero))

    scale = 1
    for s in sol:
        scale = scale * s.denominator // math.gcd(scale, s.denominator)
    coeffs = [int(s * scale) for s in sol]
    g = 0
    for c in coeffs:
        g = math.gcd(g, c)
    coeffs = [c // g for c in coeffs]

    term = lambda c, lab: pretty(lab) if c == 1 else f"{c}{pretty(lab)}"
    lhs = " + ".join(term(coeffs[i], labels[i]) for i in range(nr))
    rhs = " + ".join(term(coeffs[i], labels[i]) for i in range(nr, n))

    check = []
    for el in elements:
        l = sum(coeffs[i] * counts[i].get(el, 0) for i in range(nr))
        r = sum(coeffs[i] * counts[i].get(el, 0) for i in range(nr, n))
        check.append(f"  {el}: {l} = {r}  {'✓' if l == r else '✗'}")
    if has_charge:
        l = sum(coeffs[i] * charges[i] for i in range(nr))
        r = sum(coeffs[i] * charges[i] for i in range(nr, n))
        check.append(f"  charge: {l} = {r}  {'✓' if l == r else '✗'}")

    return f"{lhs} → {rhs}", coeffs, check


# ── GUI ────────────────────────────────────────────────────────────────────

if sys.platform == "win32":
    UI_FONT, MONO_FONT = "Segoe UI", "Consolas"
    try:                                    # crisp text on high-DPI displays
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
elif sys.platform == "darwin":
    UI_FONT, MONO_FONT = "Helvetica Neue", "Menlo"
else:
    UI_FONT, MONO_FONT = "DejaVu Sans", "DejaVu Sans Mono"

THEMES = {
    "dark": dict(bg="#0f141b", card="#182030", border="#27324a", text="#e6ebf4",
                 muted="#8c97ab", accent="#5aa2ff", accent_hover="#7bb6ff",
                 accent_fg="#0b1220", good="#4cd6a0", bad="#ff7a85",
                 chip="#222c40", chip_hover="#2d3a55"),
    "light": dict(bg="#f3f6fb", card="#ffffff", border="#dbe2ee", text="#18202e",
                  muted="#66728a", accent="#2563eb", accent_hover="#1d4fd0",
                  accent_fg="#ffffff", good="#0f9d6b", bad="#d6334a",
                  chip="#e8eef9", chip_hover="#d6e1f4"),
}

EXAMPLES = [
    ("Combustion", "C3H8 + O2 -> CO2 + H2O"),
    ("Redox ions", "MnO4^- + Fe^2+ + H^+ -> Mn^2+ + Fe^3+ + H2O"),
    ("Hydrate", "CuSO4·5H2O -> CuSO4 + H2O"),
    ("Monster", "[Cr(N2H4CO)6]4[Cr(CN)6]3 + KMnO4 + H2SO4 -> "
                "K2Cr2O7 + MnSO4 + CO2 + KNO3 + K2SO4 + H2O"),
]


def rr_points(x1, y1, x2, y2, r):
    """Points for a rounded rectangle (draw with smooth=True)."""
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


class Card(tk.Canvas):
    """Rounded panel. Put widgets in .inner"""

    def __init__(self, parent, T, fit=True, pad=16, radius=14):
        super().__init__(parent, bg=T["bg"], highlightthickness=0, bd=0)
        self.T, self.fit, self.pad, self.radius = T, fit, pad, radius
        self.border = T["border"]
        self.inner = tk.Frame(self, bg=T["card"])
        self.win = self.create_window(pad, pad, anchor="nw", window=self.inner)
        self.bind("<Configure>", self._redraw)
        if fit:
            self.inner.bind(
                "<Configure>",
                lambda e: self.configure(height=self.inner.winfo_reqheight() + 2 * self.pad))

    def set_border(self, color):
        self.border = color
        self._redraw()

    def _redraw(self, event=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("bg")
        self.create_polygon(rr_points(1, 1, w - 1, h - 1, self.radius), smooth=True,
                            fill=self.T["card"], outline=self.border, width=1.5, tags="bg")
        self.tag_lower("bg")
        opts = {"width": w - 2 * self.pad}
        if not self.fit:
            opts["height"] = h - 2 * self.pad
        self.itemconfigure(self.win, **opts)


class Btn(tk.Canvas):
    """Rounded button with hover. kind: 'accent' or 'ghost'."""

    def __init__(self, parent, T, text, command, kind="accent", size=11,
                 padx=22, pady=10):
        if kind == "accent":
            self.c_fill, self.c_hover, self.c_fg = T["accent"], T["accent_hover"], T["accent_fg"]
        else:
            self.c_fill, self.c_hover, self.c_fg = T["chip"], T["chip_hover"], T["text"]
        f = tkfont.Font(family=UI_FONT, size=size, weight="bold")
        w = f.measure(text) + 2 * padx
        h = f.metrics("linespace") + 2 * pady
        super().__init__(parent, width=w, height=h, bg=T["bg"],
                         highlightthickness=0, bd=0, cursor="hand2")
        self.shape = self.create_polygon(rr_points(1, 1, w - 1, h - 1, 10), smooth=True,
                                         fill=self.c_fill, outline=self.c_fill)
        self.label = self.create_text(w / 2, h / 2, text=text, fill=self.c_fg, font=f)
        self.bind("<Enter>", lambda e: self._paint(self.c_hover))
        self.bind("<Leave>", lambda e: self._paint(self.c_fill))
        self.bind("<Button-1>", lambda e: command())

    def _paint(self, color):
        self.itemconfigure(self.shape, fill=color, outline=color)

    def set_text(self, text):
        self.itemconfigure(self.label, text=text)


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Equation Balancer")
        self.root.geometry("800x680")
        self.root.minsize(560, 520)
        self.theme = "dark"
        self.eq_text = "Al + O2 -> Al2O3"
        self.result = None          # ("ok", balanced, coeffs, checks) | ("err", message)
        self.build()
        self.balance()
        self.root.mainloop()

    # ── layout ──
    def build(self):
        for w in self.root.winfo_children():
            w.destroy()
        T = self.T = THEMES[self.theme]
        bg = T["bg"]
        self.root.configure(bg=bg)

        st = ttk.Style()
        st.theme_use("clam")
        st.configure("Card.Vertical.TScrollbar", background=T["chip"], troughcolor=T["card"],
                     bordercolor=T["card"], lightcolor=T["chip"], darkcolor=T["chip"],
                     arrowcolor=T["muted"], relief="flat", gripcount=0)
        st.map("Card.Vertical.TScrollbar", background=[("active", T["chip_hover"])])

        wrap = tk.Frame(self.root, bg=bg)
        wrap.pack(fill="both", expand=True, padx=30, pady=24)

        head = tk.Frame(wrap, bg=bg)
        head.pack(fill="x")
        tk.Label(head, text="Equation Balancer", font=(UI_FONT, 22, "bold"),
                 bg=bg, fg=T["text"]).pack(side="left")
        toggle = tk.Label(head, text="☀" if self.theme == "dark" else "☾",
                          font=(UI_FONT, 17), bg=bg, fg=T["muted"], cursor="hand2")
        toggle.pack(side="right")
        toggle.bind("<Button-1>", lambda e: self.root.after(0, self.toggle_theme))
        tk.Label(wrap, text="Type a reaction, get the smallest whole-number coefficients.",
                 font=(UI_FONT, 10), bg=bg, fg=T["muted"], anchor="w").pack(fill="x", pady=(2, 16))

        # input
        card = Card(wrap, T)
        card.pack(fill="x")
        self.entry = tk.Entry(card.inner, font=(MONO_FONT, 14), bg=T["card"], fg=T["text"],
                              insertbackground=T["text"], relief="flat", bd=0,
                              highlightthickness=0, selectbackground=T["accent"],
                              selectforeground=T["accent_fg"])
        self.entry.pack(fill="x", ipady=6)
        self.entry.insert(0, self.eq_text)
        self.entry.bind("<Return>", lambda e: self.balance())
        self.entry.bind("<FocusIn>", lambda e: card.set_border(T["accent"]))
        self.entry.bind("<FocusOut>", lambda e: card.set_border(T["border"]))
        self.entry.focus_set()

        # buttons
        row = tk.Frame(wrap, bg=bg)
        row.pack(fill="x", pady=(14, 0))
        Btn(row, T, "Balance", self.balance).pack(side="left")
        self.copy_btn = Btn(row, T, "Copy result", self.copy, kind="ghost")
        self.copy_btn.pack(side="left", padx=(10, 0))

        # examples
        ex = tk.Frame(wrap, bg=bg)
        ex.pack(fill="x", pady=(14, 0))
        tk.Label(ex, text="Try:", font=(UI_FONT, 10), bg=bg, fg=T["muted"]).pack(side="left", padx=(0, 8))
        for name, eq in EXAMPLES:
            Btn(ex, T, name, lambda eq=eq: self.load(eq), kind="ghost",
                size=9, padx=12, pady=5).pack(side="left", padx=(0, 6))

        # result
        self.card = Card(wrap, T, fit=False, pad=20)
        self.card.pack(fill="both", expand=True, pady=(18, 0))
        self.out = tk.Text(self.card.inner, bg=T["card"], fg=T["text"], relief="flat", bd=0,
                           highlightthickness=0, wrap="word", padx=0, pady=0,
                           font=(UI_FONT, 11), state="disabled",
                           selectbackground=T["accent"], selectforeground=T["accent_fg"])
        sb = ttk.Scrollbar(self.card.inner, orient="vertical", command=self.out.yview,
                           style="Card.Vertical.TScrollbar")
        self.out.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(8, 0))
        self.out.pack(side="left", fill="both", expand=True)

        o = self.out
        o.tag_configure("label", font=(UI_FONT, 8, "bold"), foreground=T["muted"], spacing3=6)
        o.tag_configure("eq", font=(UI_FONT, 17), foreground=T["text"], spacing2=8)
        o.tag_configure("coef", font=(UI_FONT, 17, "bold"), foreground=T["accent"])
        o.tag_configure("plus", font=(UI_FONT, 17), foreground=T["muted"])
        o.tag_configure("arrow", font=(UI_FONT, 17, "bold"), foreground=T["accent"])
        o.tag_configure("mono", font=(MONO_FONT, 12), foreground=T["text"], spacing2=4)
        o.tag_configure("chip", font=(MONO_FONT, 10), background=T["chip"], foreground=T["text"])
        o.tag_configure("chipbad", font=(MONO_FONT, 10), background=T["chip"], foreground=T["bad"])
        o.tag_configure("chips", spacing1=4, spacing2=10, spacing3=4)
        o.tag_configure("gap", font=(UI_FONT, 8))
        o.tag_configure("bad", font=(UI_FONT, 8, "bold"), foreground=T["bad"], spacing3=6)
        o.tag_configure("err", font=(UI_FONT, 12), foreground=T["text"], spacing2=4)
        o.tag_configure("hint", font=(UI_FONT, 11), foreground=T["muted"])

        self.render()

    # ── behaviour ──
    def balance(self):
        eq = self.entry.get().strip()
        self.eq_text = eq
        if not eq:
            self.result = None
        else:
            try:
                balanced, coeffs, checks = balance(eq)
                self.result = ("ok", balanced, coeffs, checks)
            except ValueError as e:
                self.result = ("err", str(e))
            except Exception as e:                      # never crash the window
                self.result = ("err", f"Unexpected problem: {e}")
        self.render()

    def render(self):
        o = self.out
        o.configure(state="normal")
        o.delete("1.0", "end")

        def ins(text, *tags):
            o.insert("end", text, tags)

        r = self.result
        if r is None:
            ins("Type an equation above and press Enter.", "hint")
        elif r[0] == "err":
            ins("COULDN'T BALANCE\n", "bad")
            ins(r[1], "err")
        else:
            _, balanced, coeffs, checks = r
            ins("BALANCED\n", "label")
            for seg in re.split(r"( \+ | → )", balanced):
                if seg == " + ":
                    ins(seg, "plus")
                elif seg == " → ":
                    ins(seg, "arrow")
                else:
                    m = re.match(r"(\d+)(.*)", seg, re.S)
                    if m:
                        ins(m.group(1), "coef")
                        ins(m.group(2), "eq")
                    else:
                        ins(seg, "eq")
            ins("\n\n", "gap")
            ins("COEFFICIENTS\n", "label")
            ins("  :  ".join(map(str, coeffs)) + "\n", "mono")
            ins("\n", "gap")
            ins("ATOM & CHARGE CHECK\n", "label")
            for line in checks:
                key, rest = line.strip().split(":", 1)
                ins(f" {key}  {rest.strip()} ", "chipbad" if "✗" in rest else "chip", "chips")
                ins("  ", "chips")
        o.configure(state="disabled")

    def load(self, eq):
        self.entry.delete(0, "end")
        self.entry.insert(0, eq)
        self.balance()

    def copy(self):
        if self.result and self.result[0] == "ok":
            self.root.clipboard_clear()
            self.root.clipboard_append(self.result[1])
            self.copy_btn.set_text("Copied ✓")
            self.root.after(1300, self._reset_copy)

    def _reset_copy(self):
        try:
            self.copy_btn.set_text("Copy result")
        except tk.TclError:
            pass

    def toggle_theme(self):
        self.eq_text = self.entry.get()
        self.theme = "light" if self.theme == "dark" else "dark"
        self.build()


if __name__ == "__main__":
    App()
