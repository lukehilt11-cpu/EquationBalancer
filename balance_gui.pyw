"""balance_gui.pyw — standalone tkinter chemical equation balancer.
No other files needed.
"""
import math
import re
import tkinter as tk
from fractions import Fraction


# ── Balancer (returns results, never prints) ───────────────────────────────

def parse_compound(formula):
    """'Ca(OH)2' -> {'Ca': 1, 'O': 2, 'H': 2}"""
    def _parse(s, pos=0):
        counts = {}
        while pos < len(s):
            ch = s[pos]
            if ch == '(':
                sub, pos = _parse(s, pos + 1)
                num = ''
                while pos < len(s) and s[pos].isdigit():
                    num += s[pos]; pos += 1
                mul = int(num) if num else 1
                for el, c in sub.items():
                    counts[el] = counts.get(el, 0) + c * mul
            elif ch == ')':
                return counts, pos + 1
            elif ch.isupper():
                el = ch; pos += 1
                while pos < len(s) and s[pos].islower():
                    el += s[pos]; pos += 1
                num = ''
                while pos < len(s) and s[pos].isdigit():
                    num += s[pos]; pos += 1
                counts[el] = counts.get(el, 0) + (int(num) if num else 1)
            else:
                pos += 1
        return counts, pos
    return _parse(formula)[0]


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


def balance(equation):
    """Returns (balanced_string, coefficients, verification_lines).
    Raises ValueError with a readable message on failure."""
    parts = re.split(r'-+>|→|=+>?', equation.strip(), maxsplit=1)
    if len(parts) != 2:
        raise ValueError("Use '->' (or '=' or '→') between reactants and products.")

    split = lambda s: [c.strip() for c in re.split(r'\s*\+\s*', s) if c.strip()]
    reactants, products = split(parts[0]), split(parts[1])
    if not reactants or not products:
        raise ValueError("Need at least one reactant and one product.")

    compounds = reactants + products
    parsed = [parse_compound(c) for c in compounds]
    elements = sorted({el for p in parsed for el in p})
    if not elements:
        raise ValueError("No elements found — check formula syntax.")

    nr, n = len(reactants), len(compounds)
    matrix = [[(-p.get(el, 0) if i >= nr else p.get(el, 0))
               for i, p in enumerate(parsed)] for el in elements]

    R, pivots = rref(matrix)
    free = [c for c in range(n) if c not in pivots]
    if not free:
        raise ValueError("No solution — equation can't be balanced.")

    sol = [Fraction(0)] * n
    sol[free[0]] = Fraction(1)
    for i, pc in enumerate(pivots):
        sol[pc] = -R[i][free[0]]
    if any(s < 0 for s in sol):
        sol = [-s for s in sol]

    scale = 1
    for s in sol:
        if s != 0:
            scale = scale * s.denominator // math.gcd(scale, s.denominator)
    coeffs = [int(s * scale) for s in sol]
    if any(c <= 0 for c in coeffs):
        raise ValueError("Couldn't find positive integer coefficients.")

    term = lambda c, f: f if c == 1 else f"{c}{f}"
    lhs = " + ".join(term(coeffs[i], reactants[i]) for i in range(nr))
    rhs = " + ".join(term(coeffs[nr + i], products[i]) for i in range(len(products)))

    check = []
    for el in elements:
        l = sum(coeffs[i] * parsed[i].get(el, 0) for i in range(nr))
        r = sum(coeffs[i] * parsed[i].get(el, 0) for i in range(nr, n))
        check.append(f"  {el}: {l} = {r}  {'✓' if l == r else '✗'}")

    return f"{lhs} → {rhs}", coeffs, check


# ── GUI ────────────────────────────────────────────────────────────────────

def run(event=None):
    eq = entry.get().strip()
    if not eq:
        return
    try:
        balanced, coeffs, check = balance(eq)
        text = (f"Balanced: {balanced}\n"
                f"Coefficients: {' : '.join(map(str, coeffs))}\n\n"
                "Verification:\n" + "\n".join(check))
    except ValueError as e:
        text = f"Error: {e}"
    out.config(state="normal")
    out.delete("1.0", "end")
    out.insert("1.0", text)
    out.config(state="disabled")


root = tk.Tk()
root.title("Equation Balancer")
root.geometry("520x360")

tk.Label(root, text="Enter an equation (e.g. Fe + O2 -> Fe2O3):").pack(pady=(10, 2))
entry = tk.Entry(root, font=("Consolas", 14), width=40)
entry.pack(padx=10, pady=4)
entry.insert(0, "Al + O2 -> Al2O3")
entry.bind("<Return>", run)
entry.focus()

tk.Button(root, text="Balance", command=run).pack(pady=4)

out = tk.Text(root, font=("Consolas", 11), state="disabled", height=12)
out.pack(fill="both", expand=True, padx=10, pady=10)

run()
root.mainloop()
