# Smart Expense Bot

Telegram-бот для автоматизації обліку особистих витрат. Надсилаєте чек або квитанцію — бот розпізнає суму й магазин та зберігає витрату з категорією. Час від часу показує зведення й діаграми по витратах.

## Що вміє бот

- 🧾 **Обробка чеків та квитанцій** — приймає фотографії (JPEG, PNG) і PDF-файли (квитанції Monobank, Приват24, магазинів).
- 🧠 **Гібридне розпізнавання (OCR + Vision LLM)** — пряме зчитування тексту з цифрових PDF через `pdfplumber` та аналіз фото/сканів через OpenRouter (Vision LLM) з витягом суми й магазину.
- 🛡 **Надійний FSM-сценарій** — збереження контексту, вибір категорії та автоматичний fallback на ручне введення суми, якщо чек нерозбірливий.
- 📊 **Наочна аналітика** — текстові зведення витрат і генерація кругових діаграм (`matplotlib`).
- 🔤 **Нормалізація даних** — чисте збереження категорій у БД (без емодзі) та автозаповнення дат.

## Технологічний стек

| Сфера | Технології |
| --- | --- |
| Мова | Python 3.14 |
| Бот-фреймворк | aiogram 3.x |
| ORM + БД | SQLAlchemy 2.0 Async + PostgreSQL 16 + asyncpg |
| OCR / Vision | pdfplumber, pdf2image, OpenRouter API (Vision LLM), json-repair |
| Аналітика | matplotlib |
| Інфраструктура | Docker, Docker Compose |

## Структура проєкту

```
src/
├── bot/       # Хендлери, клавіатури, FSM-стани та middleware
├── db/        # Моделі SQLAlchemy, сесія та налаштування підключення
├── services/  # Бізнес-логіка: OCR, витрати, аналітика
└── utils/     # Допоміжні функції (нормалізація дат, категорій тощо)
```

- **`bot`** — вся взаємодія з Telegram: команди, обробка чеків, аналітика.
- **`db`** — модель даних і з'єднання з PostgreSQL.
- **`services`** — розпізнавання чеків, збереження витрат, побудова звітів.
- **`utils`** — дрібні утиліти, спільні для кількох шарів.

## Швидкий запуск

**Передумови:** Docker, Python 3.11+.

```bash
# 1. Клонуємо репозиторій
git clone <repo-url> && cd smart-expense-bot

# 2. Створюємо віртуальне середовище та встановлюємо залежності
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Налаштовуємо змінні оточення
cp .env.example .env
#    → заповніть BOT_TOKEN та OPENROUTER_API_KEY у .env

# 4. Запускаємо PostgreSQL
docker compose up -d

# 5. Запускаємо бота
python -m src.main
```

### Змінні оточення (`.env`)

```
BOT_TOKEN=1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
DB_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smart_expense
LOG_LEVEL=INFO
LOCALE=uk
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=smart_expense
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=nvidia/nemotron-3.5-super-vl:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Токен бота отримуєте у **@BotFather**. Ключ OpenRouter — на [openrouter.ai](https://openrouter.ai); без нього розпізнавання фото не працює.

## Чесно про статус

Це **MVP**, зроблений у межах навчального/портфоліо-проєкту. Код працює і виконує основну задачу — облік витрат із розпізнаванням чеків, — але є куди рости.

Що планується далі:

- **Alembic-міграції** — зараз схема створюється через `Base.metadata.create_all`, без версіювання.
- **Redis для FSM** — замінити `MemoryStorage` на персистентне сховище станів.
- **Мультивалютність** — підтримка кількох валют у витратах і зведеннях.

PR і пропозиції — вітаються.
