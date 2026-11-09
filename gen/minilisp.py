"""Small strict AutoLISP subset interpreter.

Purpose: run lisp/KIT.lsp outside a CAD program, so that
  1. the file is proven to parse and every code path can be executed, and
  2. the static sample blocks in the DXF come from the same code the user runs.

It is strict on purpose: an unknown function, a wrong group-code type in
entmake, or an unset variable used as a number raises an error. It keeps the
AutoLISP integer/real distinction (integer division truncates).
"""
from __future__ import annotations

import math
import re


class LispError(Exception):
    pass


class Sym(str):
    """Symbol. AutoLISP symbols are case-insensitive; stored upper-case."""

    def __new__(cls, name):
        return super().__new__(cls, name.upper())

    def __repr__(self):
        return f"Sym({str(self)})"


class Dot:
    """Dotted pair (a . b)."""

    def __init__(self, car, cdr):
        self.car, self.cdr = car, cdr

    def __repr__(self):
        return f"({self.car!r} . {self.cdr!r})"


class Lambda:
    def __init__(self, params, locals_, body):
        self.params, self.locals, self.body = params, locals_, body


T = Sym("T")
TOKEN = re.compile(r"""\s*(;[^\n]*|"(?:\\.|[^"\\])*"|[()']|[^\s()';"]+)""")


def tokenize(src):
    pos, out = 0, []
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m:
            if src[pos:].strip() == "":
                break
            raise LispError(f"bad token at {pos}: {src[pos:pos + 30]!r}")
        pos = m.end()
        tok = m.group(1)
        if not tok.startswith(";"):
            out.append(tok)
    return out


def atom(tok):
    if tok.startswith('"'):
        body = tok[1:-1]
        return (body.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\"))
    if re.fullmatch(r"[-+]?\d+", tok):
        return int(tok)
    if re.fullmatch(r"[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?", tok):
        return float(tok)
    return Sym(tok)


def parse(tokens):
    """Returns a list of top-level forms. Raises on unbalanced parentheses."""
    forms, i = [], 0

    def read(i):
        if i >= len(tokens):
            raise LispError("unexpected end of file: missing ')'")
        tok = tokens[i]
        if tok == "(":
            lst, i = [], i + 1
            while True:
                if i >= len(tokens):
                    raise LispError("unexpected end of file: missing ')'")
                if tokens[i] == ")":
                    return lst, i + 1
                if tokens[i] == ".":
                    cdr, i = read(i + 1)
                    if tokens[i] != ")" or len(lst) != 1:
                        raise LispError("bad dotted pair")
                    return Dot(lst[0], cdr), i + 1
                item, i = read(i)
                lst.append(item)
        if tok == ")":
            raise LispError("unexpected ')'")
        if tok == "'":
            item, i = read(i + 1)
            return [Sym("QUOTE"), item], i
        return atom(tok), i + 1

    while i < len(tokens):
        form, i = read(i)
        forms.append(form)
    return forms


def truthy(v):
    return not (v is None or v == [])


def norm(v):
    return None if v == [] else v


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# DXF group code -> required python type for entmake
def code_type(code):
    if code in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 100, 102, 410):
        return str
    if 10 <= code <= 18 or code == 210:
        return "point"
    if 38 <= code <= 59 or 140 <= code <= 149:
        return float
    if 60 <= code <= 99 or 170 <= code <= 179 or 270 <= code <= 289 or 370 <= code <= 389 or 420 <= code <= 429:
        return int
    raise LispError(f"entmake: group code {code} not known to the checker")


class Interp:
    def __init__(self):
        self.globals: dict[str, object] = {"T": T, "PI": math.pi}
        self.stack: list[dict[str, object]] = []
        self.entities: list[dict] = []      # everything entmake accepted
        self.tables: dict[str, set[str]] = {"LTYPE": {"BYLAYER", "BYBLOCK", "CONTINUOUS"},
                                            "BLOCK": set(), "LAYER": {"0"}}
        self.ucs_angle = 0.0                # rotation of the UCS about Z, radians
        self.fail_blocks = False            # True: the CAD rejects every block definition
        self.inputs: list[object] = []      # queued answers for get* functions
        self.output: list[str] = []
        self.prompts: list[str] = []        # every message shown by a get* function
        self.calls: set[str] = set()
        self.open_block: str | None = None

    # ------------------------------------------------------------ variables
    def lookup(self, name):
        for frame in reversed(self.stack):
            if name in frame:
                return frame[name]
        return self.globals.get(name)

    def assign(self, name, value):
        for frame in reversed(self.stack):
            if name in frame:
                frame[name] = value
                return
        self.globals[name] = value

    # ------------------------------------------------------------ evaluation
    def run(self, src):
        result = None
        for form in parse(tokenize(src)):
            result = self.eval(form)
        return result

    def eval(self, x):
        if isinstance(x, Sym):
            return self.lookup(x)
        if not isinstance(x, list):
            return x
        if not x:
            return None
        head = x[0]
        if isinstance(head, Sym):
            special = getattr(self, "sf_" + head.lower().replace("-", "_"), None)
            if special:
                return special(x)
            fn = self.lookup(head)
            if isinstance(fn, Lambda):
                return self.call(fn, [self.eval(a) for a in x[1:]], head)
            builtin = BUILTINS.get(head)
            if builtin is None:
                raise LispError(f"unknown function: {head}")
            self.calls.add(head)
            return norm(builtin(self, *[self.eval(a) for a in x[1:]]))
        if isinstance(head, list) and head and head[0] == "LAMBDA":
            return self.call(self.sf_lambda(head), [self.eval(a) for a in x[1:]], "lambda")
        raise LispError(f"cannot call {head!r}")

    def call(self, fn, args, name="?"):
        if len(args) != len(fn.params):
            raise LispError(f"{name}: expected {len(fn.params)} arguments, got {len(args)}")
        frame = {p: a for p, a in zip(fn.params, args)}
        frame.update({l: None for l in fn.locals})
        self.stack.append(frame)
        try:
            result = None
            for form in fn.body:
                result = self.eval(form)
            return result
        finally:
            self.stack.pop()

    def apply(self, f, args):
        if isinstance(f, Lambda):
            return self.call(f, args)
        if isinstance(f, Sym):
            return self.eval([f] + [[Sym("QUOTE"), a] for a in args])
        if isinstance(f, list) and f and f[0] == "LAMBDA":
            return self.call(self.sf_lambda(f), args)
        raise LispError(f"cannot apply {f!r}")

    # ------------------------------------------------------------ special forms
    def sf_quote(self, x):
        return norm(x[1])

    def sf_setq(self, x):
        if len(x) % 2 != 1:
            raise LispError("setq: odd number of arguments")
        value = None
        for i in range(1, len(x), 2):
            if not isinstance(x[i], Sym):
                raise LispError(f"setq: not a symbol: {x[i]!r}")
            value = self.eval(x[i + 1])
            self.assign(x[i], value)
        return value

    def _split_params(self, spec):
        params, locals_, seen_slash = [], [], False
        for s in spec or []:
            if s == "/":
                seen_slash = True
            elif seen_slash:
                locals_.append(s)
            else:
                params.append(s)
        return params, locals_

    def sf_defun(self, x):
        params, locals_ = self._split_params(x[2])
        self.globals[x[1]] = Lambda(params, locals_, x[3:])
        return x[1]

    def sf_lambda(self, x):
        params, locals_ = self._split_params(x[1])
        return Lambda(params, locals_, x[2:])

    def sf_if(self, x):
        if len(x) not in (3, 4):
            raise LispError(f"if: needs 2 or 3 arguments, got {len(x) - 1}")
        if truthy(self.eval(x[1])):
            return self.eval(x[2])
        return self.eval(x[3]) if len(x) == 4 else None

    def sf_cond(self, x):
        for clause in x[1:]:
            test = self.eval(clause[0])
            if truthy(test):
                result = test
                for form in clause[1:]:
                    result = self.eval(form)
                return result
        return None

    def sf_progn(self, x):
        result = None
        for form in x[1:]:
            result = self.eval(form)
        return result

    def sf_while(self, x):
        result, guard = None, 0
        while truthy(self.eval(x[1])):
            guard += 1
            if guard > 100000:
                raise LispError("while: more than 100000 iterations")
            for form in x[2:]:
                result = self.eval(form)
        return result

    def sf_repeat(self, x):
        result = None
        for _ in range(self.eval(x[1])):
            for form in x[2:]:
                result = self.eval(form)
        return result

    def sf_foreach(self, x):
        result = None
        self.stack.append({x[1]: None})
        try:
            for item in self.eval(x[2]) or []:
                self.stack[-1][x[1]] = item
                for form in x[3:]:
                    result = self.eval(form)
        finally:
            self.stack.pop()
        return result

    def sf_and(self, x):
        for form in x[1:]:
            if not truthy(self.eval(form)):
                return None
        return T

    def sf_or(self, x):
        for form in x[1:]:
            if truthy(self.eval(form)):
                return T
        return None

    def sf_function(self, x):
        return x[1]

    # ------------------------------------------------------------ CAD side
    def entmake(self, data):
        if not isinstance(data, list) or not data:
            raise LispError("entmake: needs a list")
        ent: dict[str, object] = {"codes": []}
        for item in data:
            if isinstance(item, Dot):
                code, value = item.car, item.cdr
            elif isinstance(item, list) and item:
                code, value = item[0], item[1:]
            else:
                raise LispError(f"entmake: bad item {item!r}")
            if not isinstance(code, int):
                raise LispError(f"entmake: group code must be an integer: {code!r}")
            want = code_type(code)
            if want == "point":
                if not (isinstance(value, list) and len(value) in (2, 3) and all(isinstance(c, float) for c in value)):
                    raise LispError(f"entmake: code {code} needs a point of reals, got {value!r}")
            elif want is float:
                if not isinstance(value, float):
                    raise LispError(f"entmake: code {code} needs a real, got {value!r}")
            elif not isinstance(value, want) or isinstance(value, bool):
                raise LispError(f"entmake: code {code} needs {want.__name__}, got {value!r}")
            ent["codes"].append((code, value))
        if ent["codes"][0][0] != 0:
            raise LispError("entmake: first item must be group 0")
        kind = ent["codes"][0][1]
        ent["type"] = kind
        first = {}
        for code, value in ent["codes"]:
            first.setdefault(code, value)
        if kind == "LTYPE":
            self.tables["LTYPE"].add(first[2].upper())
            self.entities.append(ent)
            return first[2]
        if kind == "BLOCK":
            if self.open_block:
                raise LispError("entmake: BLOCK inside an open BLOCK")
            self.open_block = first[2]
            ent["block"] = None
            self.entities.append(ent)
            return first[2]
        if kind == "ENDBLK":
            if not self.open_block:
                raise LispError("entmake: ENDBLK without BLOCK")
            name, self.open_block = self.open_block, None
            if self.fail_blocks:
                return None
            self.tables["BLOCK"].add(name.upper())
            return name
        if kind not in ("LINE", "LWPOLYLINE", "CIRCLE", "ARC", "SOLID", "INSERT"):
            raise LispError(f"entmake: entity type {kind} not known to the checker")
        if kind == "LWPOLYLINE":
            n = sum(1 for c, _ in ent["codes"] if c == 10)
            if first.get(90) != n:
                raise LispError(f"LWPOLYLINE: code 90 says {first.get(90)} vertices, list has {n}")
            if [v for c, v in ent["codes"] if c == 100] != ["AcDbEntity", "AcDbPolyline"]:
                raise LispError("LWPOLYLINE: needs the two subclass markers")
        if kind == "INSERT":
            if first[2].upper() not in self.tables["BLOCK"]:
                raise LispError(f"INSERT: block {first[2]} is not defined")
            if self.open_block:
                raise LispError("INSERT inside an open BLOCK")
        ltype = first.get(6)
        if ltype and ltype.upper() not in self.tables["LTYPE"]:
            raise LispError(f"{kind}: linetype {ltype} is not defined")
        ent["block"] = self.open_block
        self.entities.append(ent)
        return ent

    def next_input(self, what, args=()):
        self.prompts += [a for a in args if isinstance(a, str)]
        if not self.inputs:
            raise LispError(f"{what}: no queued input")
        return self.inputs.pop(0)


def _num(v, name):
    if not is_num(v):
        raise LispError(f"{name}: not a number: {v!r}")
    return v


def b_add(i, *a):
    return sum(_num(v, "+") for v in a)


def b_sub(i, *a):
    for v in a:
        _num(v, "-")
    if len(a) == 1:
        return -a[0]
    out = a[0]
    for v in a[1:]:
        out -= v
    return out


def b_mul(i, *a):
    out = 1
    for v in a:
        out *= _num(v, "*")
    return out


def b_div(i, *a):
    out = _num(a[0], "/")
    for v in a[1:]:
        _num(v, "/")
        if isinstance(out, int) and isinstance(v, int):
            out = int(out / v)          # AutoLISP integer division truncates
        else:
            out = out / v
    return out


def b_rem(i, a, b):
    if isinstance(a, int) and isinstance(b, int):
        return int(math.fmod(a, b))
    return math.fmod(a, b)


def _cmp(op):
    def f(i, *a):
        for v in a:
            if not (is_num(v) or isinstance(v, str)):
                raise LispError(f"comparison of non-number: {v!r}")
        return T if all(op(a[k], a[k + 1]) for k in range(len(a) - 1)) else None
    return f


def b_eq(i, *a):
    return T if all(a[k] == a[k + 1] for k in range(len(a) - 1)) else None


def b_cons(i, a, b):
    if b is None:
        return [a]
    if isinstance(b, list):
        return [a] + b
    return Dot(a, b)


def b_car(i, v):
    if v is None:
        return None
    return v.car if isinstance(v, Dot) else v[0]


def b_cdr(i, v):
    if v is None:
        return None
    return v.cdr if isinstance(v, Dot) else v[1:]


def b_nth(i, n, lst):
    return lst[n] if lst and n < len(lst) else None


def b_append(i, *lists):
    out = []
    for l in lists:
        if l is not None and not isinstance(l, list):
            raise LispError(f"append: not a list: {l!r}")
        out += l or []
    return out


def _pt(p, name):
    if not (isinstance(p, list) and len(p) in (2, 3) and all(is_num(c) for c in p)):
        raise LispError(f"{name}: not a point: {p!r}")
    return p


def b_distance(i, a, b):
    _pt(a, "distance"), _pt(b, "distance")
    return math.dist(a[:2], b[:2]) if len(a) == 2 or len(b) == 2 else math.dist(a, b)


def b_angle(i, a, b):
    _pt(a, "angle"), _pt(b, "angle")
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    return ang + 2 * math.pi if ang < 0 else ang


def b_polar(i, p, ang, d):
    _pt(p, "polar")
    return [p[0] + d * math.cos(ang), p[1] + d * math.sin(ang)] + list(p[2:])


def b_trans(i, p, src, dst):
    """Only UCS (1) -> WCS (0), for a UCS rotated about Z."""
    _pt(p, "trans")
    if (src, dst) != (1, 0):
        raise LispError(f"trans: only 1 -> 0 is modelled, got {src} -> {dst}")
    c, s = math.cos(i.ucs_angle), math.sin(i.ucs_angle)
    return [p[0] * c - p[1] * s, p[0] * s + p[1] * c] + list(p[2:])


def b_rtos(i, v, mode=2, prec=4):
    return f"{_num(v, 'rtos'):.{prec}f}"


def b_itoa(i, v):
    if not isinstance(v, int):
        raise LispError(f"itoa: not an integer: {v!r}")
    return str(v)


def b_strcat(i, *a):
    for v in a:
        if not isinstance(v, str) or isinstance(v, Sym):
            raise LispError(f"strcat: not a string: {v!r}")
    return "".join(a)


def b_fix(i, v):
    return int(_num(v, "fix"))


def b_princ(i, *a):
    if a:
        i.output.append(str(a[0]))
        return a[0]
    return None


def b_tblsearch(i, table, name):
    return [Dot(2, name)] if name.upper() in i.tables.get(table.upper(), set()) else None


def b_getpoint(i, *a):
    v = i.next_input("getpoint", a)
    return None if v is None else [float(c) for c in v]


def b_getnum(kind):
    def f(i, *a):
        v = i.next_input(kind, a)
        if v is None:
            return None
        return int(v) if kind == "getint" else float(v)
    return f


def b_getkword(i, *a):
    return i.next_input("getkword", a)


def b_mapcar(i, f, *lists):
    return [i.apply(f, list(items)) for items in zip(*[l or [] for l in lists])]


BUILTINS = {
    "+": b_add, "-": b_sub, "*": b_mul, "/": b_div, "REM": b_rem,
    "1+": lambda i, v: _num(v, "1+") + 1, "1-": lambda i, v: _num(v, "1-") - 1,
    "ABS": lambda i, v: abs(_num(v, "abs")), "FIX": b_fix,
    "FLOAT": lambda i, v: float(_num(v, "float")),
    "SQRT": lambda i, v: math.sqrt(v), "SIN": lambda i, v: math.sin(v),
    "COS": lambda i, v: math.cos(v), "ATAN": lambda i, a, b=None: math.atan2(a, b) if b is not None else math.atan(a),
    "MIN": lambda i, *a: min(a), "MAX": lambda i, *a: max(a),
    "=": b_eq, "/=": lambda i, a, b: T if a != b else None,
    "<": _cmp(lambda a, b: a < b), ">": _cmp(lambda a, b: a > b),
    "<=": _cmp(lambda a, b: a <= b), ">=": _cmp(lambda a, b: a >= b),
    "NOT": lambda i, v: None if truthy(v) else T, "NULL": lambda i, v: None if truthy(v) else T,
    "LIST": lambda i, *a: list(a), "CONS": b_cons, "CAR": b_car, "CDR": b_cdr,
    "CADR": lambda i, v: b_car(i, b_cdr(i, v)), "CADDR": lambda i, v: b_car(i, b_cdr(i, b_cdr(i, v))),
    "NTH": b_nth, "APPEND": b_append, "LENGTH": lambda i, v: len(v or []),
    "REVERSE": lambda i, v: list(reversed(v or [])), "LAST": lambda i, v: (v or [None])[-1],
    "MAPCAR": b_mapcar, "APPLY": lambda i, f, args: i.apply(f, args or []),
    "EVAL": lambda i, v: i.eval(v),
    "STRCAT": b_strcat, "ITOA": b_itoa, "RTOS": b_rtos, "STRCASE": lambda i, s, lower=None: s.lower() if lower else s.upper(),
    "ATOI": lambda i, s: int(float(s or 0)), "ATOF": lambda i, s: float(s or 0),
    "DISTANCE": b_distance, "ANGLE": b_angle, "POLAR": b_polar,
    "TRANS": b_trans,
    "TBLSEARCH": b_tblsearch, "ENTMAKE": lambda i, data: i.entmake(data),
    "GETPOINT": b_getpoint, "GETDIST": b_getnum("getdist"), "GETREAL": b_getnum("getreal"),
    "GETINT": b_getnum("getint"), "GETKWORD": b_getkword, "INITGET": lambda i, *a: None,
    "PRINC": b_princ, "PROMPT": b_princ, "TERPRI": lambda i: None,
}

# functions that exist in every target CAD (AutoCAD / LT 2024+ / BricsCAD / ZWCAD)
SAFE_CORE = set(BUILTINS)
