# Project Rules

## 1. Zero Trust AI
- **No LLM Math**: The AI model must NEVER be trusted to perform financial math (addition, subtraction, multiplication, XIRR).
- **No Direct DB Access**: The AI model must NEVER have direct SQL access to the database. All data access is mediated through deterministic Python tools.
- **Grounding is Mandatory**: The AI model can only answer questions using the JSON context explicitly provided to it by the tool layer.

## 2. Financial Correctness Invariants
- **Double Counting Rule**: Transfers between internal accounts MUST NOT be counted as expenses or income.
- **Credit Card Rule**: Credit card bill payments (from a checking account to a credit card account) are transfers, NOT expenses. The original credit card swiping transactions are the expenses.
- **Investment Rule**: Buying a stock or mutual fund is an asset transfer (cash to investment), NOT an expense.

## 3. Privacy and Local-First
- **No Cloud Sync**: User financial data (transactions, balances) must remain in the local SQLite database.
- **API Keys**: LLM API keys must be loaded via `.env` and never hardcoded or logged.

## 4. Architecture Constraints
- **Modular Monolith**: Maintain a single codebase with clear bounded contexts (e.g., `services/domain/finance`, `services/domain/portfolio`). No microservices.
- **Async DB**: All database access must use `sqlalchemy.ext.asyncio` with `aiosqlite`.
- **Eager Loading**: All ORM relationships accessed after session closure or in async contexts MUST be eager-loaded using `selectinload()`. Lazy loading will cause `MissingGreenlet` errors.
