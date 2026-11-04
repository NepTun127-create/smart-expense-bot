# Smart Expense Bot — технічний опис

Стислий огляд технічної складової: стек, архітектура, модель даних і тестові набори.

---

## 1. Технологічний стек

| Сфера | Технології |
| --- | --- |
| Мова | Python 3.14 |
| Telegram-бот | aiogram 3.x (async, FSM, роутери, middleware) |
| БД та ORM | PostgreSQL 16 · SQLAlchemy 2.0 Async · asyncpg |
| Розпізнавання | pdfplumber · pdf2image · Pillow · OpenRouter API (Vision LLM) · json-repair |
| Аналітика | matplotlib |
| Конфігурація | pydantic-settings · python-dotenv |
| Інфраструктура | Docker · Docker Compose · Git |

---

## 2. Архітектура

Шарувата модель: презентація → бізнес-логіка → дані.

```
Користувач
   │  фото / PDF / команда
Telegram API
   │  long-polling
aiogram Dispatcher (src/bot)
   │
   ├─► OCR/Vision (services/ocr_service.py)
   │     pdfplumber (текст) · pdf2image + Vision LLM (фото)
   │     └─► нормалізація: сума, магазин, категорія
   │
   └─► FSM: вибір категорії / ручне введення суми
         └─► ExpenseService (services)
               └─► SQLAlchemy async ──► PostgreSQL
                     └─► AnalyticsService + matplotlib
                           └─► звіт ──► Telegram API ──► Користувач
```

**Рішення:**

- **Гібридне розпізнавання** — текст зі цифрових PDF читається напряму (`pdfplumber`), фото та скани обробляє Vision-LLM. У разі помилки — fallback.
- **FSM-fallback** — стани `ReceiptFSM` зберігають контекст; якщо суму не розпізнано, користувач переходить у ручне введення.
- **Middleware** — `DbSessionMiddleware` інжектує async-сесію в кожен хендлер.

### Структура коду

```
src/
├── bot/       # хендлери, клавіатури, FSM, middleware
├── db/        # ORM-моделі, сесія, двигун
├── services/  # OCR, витрати, аналітика
└── utils/     # парсинг сум, нормалізація
```

---

## 3. База даних

**СУБД:** PostgreSQL 16 · **зв'язки:** `ON DELETE CASCADE` · **категорії:** фіксований словник, зберігаються рядком.

```
users 1──∞ receipts 1──∞ expenses
```

| Таблиця | Поле | Тип | Примітка |
| --- | --- | --- | --- |
| **users** | `telegram_id` | BIGINT PK | id у Telegram |
| | `username` | VARCHAR(32) NULL | |
| | `full_name` | VARCHAR(128) | |
| | `created_at` | TIMESTAMPTZ | UTC |
| **receipts** | `id` | BIGINT PK | |
| | `user_id` | BIGINT FK | → `users.telegram_id` |
| | `file_id` | VARCHAR(256) | id файлу в Telegram |
| | `file_name` | VARCHAR(256) NULL | для PDF |
| | `created_at` | TIMESTAMPTZ | |
| **expenses** | `id` | BIGINT PK | |
| | `receipt_id` | BIGINT FK | → `receipts.id` |
| | `amount` | NUMERIC(12,2) | точність до копійок |
| | `category` | VARCHAR(64) | без емодзі |
| | `expense_date` | DATE | автозаповнення |
| | `description` | VARCHAR(512) NULL | напр. магазин |
| | `created_at` | TIMESTAMPTZ | |

`amount` — `NUMERIC`, а не `FLOAT`, щоб уникнути похибок округлення грошей.

---

## 4. Набори даних

**Фотографії чеків**
- рівномірне освітлення (еталон) · слабке/штучне світло
- кут / перспектива · розмитий або пошкоджений текст
- кілька позицій і складний формат суми

**PDF-квитанції**
- Monobank (текстовий шар) · Приват24 (виписка)
- фіскальний чек магазину · сканований PDF без тексту (`pdf2image`)

**Перевірки:** витяг суми (роздільник, копійки) · магазин і категорія · fallback (некоректний формат, без API-ключа, битий JSON).
