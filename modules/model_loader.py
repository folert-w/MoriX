from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import re

# ---- Настройки модели ----

MODEL_NAME = "openai/gpt-oss-20b"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,  # Используем BF16
    device_map="cpu",  # Распределение на GPU
    offload_folder=None  # Отключение offloading
)
model.eval()

# ---- Вспомогательные функции ----

def _is_code_request(user_text: str) -> bool:
    """
    Понимаем по запросу пользователя, что он хочет именно КОД,
    а не обычное объяснение.
    Смотрим только на текст вопроса, без истории.
    """
    if not user_text:
        return False

    t = user_text.lower()

    # Явные триггеры
    if "```" in user_text:
        return True

    keywords = [
        "код", "скрипт", "функци", "программу",
        "пример кода", "покажи код", "написать код",
        "напиши функцию", "напиши класс",

        "на python", "на пайтон",
        "на javascript", "на js", "на typescript",
        "на c++", "на c#", "на java",
    ]
    if any(k in t for k in keywords):
        return True

    # если пользователь уже сам пишет что-то похожее на код
    if any(ch in user_text for ch in ["{", "}", ";"]):
        return True

    return False


def _extract_last_user_question(text: str) -> str:
    """
    Из строки вида:
    'Краткая история...\n...MoriX ответил: ...\n\nНовый вопрос пользователя:\nXXX'
    достаём только XXX.
    Если маркера нет — возвращаем текст как есть.
    """
    if not text:
        return ""
    marker = "\nНовый вопрос пользователя:\n"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text.strip()

def _looks_like_code(text: str) -> bool:
    """
    Понимаем по ответу модели, что это, скорее всего, код.
    """
    if not text:
        return False

    if "```" in text:
        return True

    code_keywords = [
        "def ", "class ", "function ", "console.log",
        "#include", "public static", "using System",
        "async ", "await ", "import ", "from ",
    ]
    if any(k in text for k in code_keywords):
        return True

    lines = text.splitlines()
    score = 0
    for line in lines:
        ls = line.lstrip()
        if ls.startswith(("//", "#", "def ", "class ", "import ")):
            score += 1
        if "{" in line or "}" in line:
            score += 1

    return score >= 3

# ---- Основная функция ----

def generate_reply(user_text: str) -> str:
    """
    MoriX-ответ:
    - если запрос про КОД → отдаём кодовый блок ```lang ...```;
    - иначе — обычный короткий ответ.
    """

    user_text = (user_text or "").strip()
    if not user_text:
        return "Сформулируй вопрос, и я отвечу."

    # --- Системный промпт ---
    system_content = (
        "Ты MoriX — локальный оффлайн-ассистент, который работает на компьютере пользователя. "
        "Отвечай по-русски, по делу, простым человеческим языком. "
        "Обращайся к пользователю на «ты». "
        "Не говори, что ты искусственный интеллект, модель, Assistant или продукт компании. "
        "Не придумывай «хозяев», серверы, компании и разработчиков — это не важно для пользователя. "
        "Если спрашивают, кто ты, отвечай коротко: что ты MoriX и помогаешь по задачам. "
        "Если не уверен в фактах или числах — лучше скажи, что можешь ошибаться."
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_text},
    ]

    # Преобразуем сообщения в список строк
    messages_content = [msg["content"] for msg in messages]
    # Теперь messages_content — это список строк, которые мы можем передать в tokenizer

    # Формируем prompt и генерируем
    inputs = tokenizer(messages_content, return_tensors="pt", padding=True, truncation=True).to(model.device)

    with torch.no_grad():
        output_ids = model.generate(
            inputs["input_ids"],
            max_new_tokens=256,  # Достаточно для кода и текста
            do_sample=False,
            temperature=0.3,
            repetition_penalty=1.15,
            pad_token_id=tokenizer.eos_token_id,
        )

    gen_ids = output_ids[0, inputs["input_ids"].shape[-1]:]
    raw = tokenizer.decode(gen_ids, skip_special_tokens=True).strip()

    return raw
