from __future__ import annotations

import re
import ast
import operator as op
from typing import Optional

# --- Простой безопасный калькулятор (арифметика) ---

_ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.USub: op.neg,
    ast.Pow: op.pow,  # поддержка степеней (**)
}


def _safe_eval(expr: str) -> float:
    """
    Очень простой и безопасный разбор выражения из чисел и + - * / ** ().
    Никакого exec/eval, только AST.
    """
    def _eval(node):
        if isinstance(node, ast.Num):      # число
            return node.n
        if isinstance(node, ast.UnaryOp):  # унарный минус
            if type(node.op) not in _ALLOWED_OPS:
                raise ValueError("unsupported op")
            return _ALLOWED_OPS[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.BinOp):
            if type(node.op) not in _ALLOWED_OPS:
                raise ValueError("unsupported op")
            return _ALLOWED_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        raise ValueError("unsupported expression")

    node = ast.parse(expr, mode="eval").body
    return _eval(node)


# --- Конвертер единиц (с числом в запросе) ---

_UNIT_ALIASES = {
    "kg": {"кг", "килограмм", "килограмма", "килограммов", "килограмме", "килограммы"},
    "g": {"г", "гр", "грамм", "грамма", "граммов", "граммах"},
    "t": {"т", "тонна", "тонны", "тонн", "тонне"},

    "m": {"м", "метр", "метра", "метров"},
    "cm": {"см", "сантиметр", "сантиметра", "сантиметров"},
    "km": {"км", "километр", "километра", "километров"},

    "h": {"ч", "час", "часа", "часов"},
    "min": {"мин", "минут", "минуты", "минуту"},
    "s": {"сек", "секунд", "секунды", "секунду"},
}

# from_unit, to_unit, factor (to = value * factor)
_CONVERSIONS = [
    ("kg", "g", 1000.0),
    ("kg", "t", 0.001),
    ("t", "kg", 1000.0),
    ("g", "kg", 0.001),

    ("m", "cm", 100.0),
    ("cm", "m", 0.01),
    ("km", "m", 1000.0),
    ("m", "km", 0.001),

    ("h", "min", 60.0),
    ("min", "h", 1.0 / 60.0),
    ("min", "s", 60.0),
    ("s", "min", 1.0 / 60.0),
]


def _normalize_unit(word: str) -> Optional[str]:
    w = word.lower()
    for key, aliases in _UNIT_ALIASES.items():
        if w in aliases:
            return key
    return None


def try_unit_convert(text: str) -> Optional[str]:
    """
    Пробуем понять запрос типа:
    - "переведи 5 кг в граммы"
    - "сколько будет 2.5 тонны в килограммах"
    """
    t = text.lower().replace(",", ".")

    # должны быть явные слова про конвертацию
    if not any(kw in t for kw in ["переведи", "перевести", "сколько будет", "сколько это в", "это в", "в граммы", "в килограммы", "в тонны"]):
        return None

    # Ищем число + исходную единицу
    num_match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zа-яё]+)", t)
    if not num_match:
        return None

    value = float(num_match.group(1))
    src_word = num_match.group(2)
    src_unit = _normalize_unit(src_word)
    if src_unit is None:
        return None

    # Ищем целевую единицу после "в ..."
    dst_match = re.search(r"в\s+([a-zа-яё]+)", t)
    if not dst_match:
        return None

    dst_word = dst_match.group(1)
    dst_unit = _normalize_unit(dst_word)
    if dst_unit is None:
        return None

    # Ищем нужное преобразование
    for from_u, to_u, factor in _CONVERSIONS:
        if src_unit == from_u and dst_unit == to_u:
            result = value * factor
            if abs(result - int(result)) < 1e-9:
                result_str = str(int(result))
            else:
                result_str = f"{result:.4g}"
            return f"{value} {src_word} = {result_str} {dst_word}"

    return None


# --- Простые факты (без явной конвертации) ---

def try_answer_facts(text: str) -> Optional[str]:
    """
    Пытаемся ответить на короткие факт-вопросы без расчёта.
    """
    t = text.lower().strip()

    # тонна / килограммы
    if "тонн" in t or "тонна" in t or "тонну" in t:
        if "кг" in t or "килограмм" in t or "килограм" in t:
            return "В одной тонне 1000 килограммов."

    # сколько дней в неделе
    if "недел" in t and ("сколько" in t or "скольки" in t):
        if "дней" in t or "дня" in t:
            return "В неделе 7 дней."

    # метр / сантиметры
    if "метр" in t and "сантим" in t and "сколько" in t:
        return "В одном метре 100 сантиметров."

    # километр / метры
    if "километр" in t and "метр" in t and "сколько" in t:
        return "В одном километре 1000 метров."

    # килограмм / граммы
    if "килограм" in t and ("грамм" in t or "гр" in t) and "сколько" in t:
        return "В одном килограмме 1000 граммов."

    # час / минуты
    if "час" in t and "минут" in t and "сколько" in t:
        return "В одном часе 60 минут."

    # минута / секунды
    if "минут" in t and ("секунд" in t or "секунды" in t) and "сколько" in t:
        return "В одной минуте 60 секунд."

    return None


# --- Калькулятор (выражения и "умноженное на") ---

def try_calculate(text: str) -> Optional[str]:
    """
    Пробуем вытащить математическое выражение и посчитать.
    Поддерживаем обычную арифметику: числа, + - * / ^ и скобки.
    Учитываем простые фразы типа "5 умноженное на 3" и "деленное на".
    """
    # нормализуем
    t = text.lower().replace(",", ".")

    # переведём простые словесные операции в символы
    replacements = {
        "умножить на": "*",
        "умноженное на": "*",
        "умножённое на": "*",

        "разделить на": "/",
        "поделить на": "/",
        "деленное на": "/",
        "делённое на": "/",

        "плюс": "+",
        "минус": "-",
    }
    for k, v in replacements.items():
        t = t.replace(k, f" {v} ")

    # убираем " и " как связку, чтобы не рвало выражение
    t = t.replace(" и ", " ")

    # выцепляем кандидатов, содержащих только цифры, пробелы и операторы
    candidates = re.findall(r"[0-9\.\+\-\*\/\^\(\)\s]+", t)
    if not candidates:
        return None

    good: list[str] = []
    for c in candidates:
        c = c.strip()
        if not c:
            continue
        if not any(op_char in c for op_char in "+-*/^"):
            continue
        if not any(ch.isdigit() for ch in c):
            continue
        good.append(c)

    if not good:
        return None

    # берём последний осмысленный кандидат (чаще всего — из последнего вопроса)
    expr = good[-1]
    expr = expr.replace("^", "**")
    expr_clean = re.sub(r"\s+", "", expr)

    try:
        value = _safe_eval(expr_clean)
    except Exception:
        return None

    if abs(value - int(value)) < 1e-9:
        return f"{expr_clean} = {int(value)}"
    else:
        return f"{expr_clean} = {value:.4g}"


# --- Главная точка входа для оркестратора ---

def try_handle_tools(text: str) -> Optional[str]:
    """
    Главная точка входа: конвертация → факты → калькулятор.
    Если вернули строку — LLM не трогаем.
    """
    conv = try_unit_convert(text)
    if conv is not None:
        return conv

    fact = try_answer_facts(text)
    if fact is not None:
        return fact

    calc = try_calculate(text)
    if calc is not None:
        return calc

    return None