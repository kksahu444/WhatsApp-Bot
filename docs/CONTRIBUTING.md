# Contributing to WhatsApp Seller Bot

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions. We're building something together!

## Getting Started

### Development Setup

1. **Fork and clone:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/whatsapp-seller-bot.git
   cd whatsapp-seller-bot
   ```

2. **Set up Python environment:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Set up Node.js environment:**
   ```bash
   cd bot
   npm install
   ```

4. **Copy environment files:**
   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp bot/.env.example bot/.env
   ```

5. **Start services:**
   ```bash
   docker compose up redis -d
   cd backend && uvicorn main:app --reload
   ```

## Development Workflow

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Adding tests

Example: `feature/add-payment-gateway`

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(cart): add quantity update functionality
fix(search): handle empty query gracefully
docs(api): update endpoint documentation
```

### Pull Requests

1. Create a branch from `main`
2. Make your changes
3. Add tests if applicable
4. Update documentation
5. Run linting and tests
6. Submit PR with description

## Code Standards

### Python (Backend)

- Follow PEP 8
- Use type hints
- Maximum line length: 100
- Use docstrings for functions/classes

```python
async def search_products(
    query: str,
    limit: int = 5
) -> list[Product]:
    """
    Search products by query.
    
    Args:
        query: Search query string
        limit: Maximum results to return
        
    Returns:
        List of matching products
    """
    # Implementation
```

### JavaScript (Bot)

- Use ESLint with provided config
- Prefer `const` over `let`
- Use JSDoc for documentation

```javascript
/**
 * Send a message to a WhatsApp user.
 * @param {string} phone - Phone number
 * @param {string} message - Message content
 * @returns {Promise<void>}
 */
async function sendMessage(phone, message) {
  // Implementation
}
```

### Testing

**Python:**
```bash
cd backend
pytest tests/ -v
pytest tests/ --cov=.
```

**JavaScript:**
```bash
cd bot
npm test
```

## Project Structure

```
whatsapp-seller-bot/
├── backend/           # Python FastAPI backend
│   ├── handlers/      # Request handlers
│   ├── services/      # Business logic
│   ├── models/        # Pydantic models
│   ├── database/      # Database clients
│   ├── rag/           # RAG pipeline
│   └── tests/         # Backend tests
├── bot/               # Node.js WhatsApp bot
│   └── src/
│       ├── adapters/  # WhatsApp clients
│       ├── handlers/  # Message handlers
│       └── utils/     # Utilities
├── dashboard/         # Streamlit dashboard
│   ├── pages/         # Dashboard pages
│   └── components/    # UI components
├── infra/             # Infrastructure configs
└── docs/              # Documentation
```

## Adding Features

### Adding a New Intent Handler

1. Create handler in `backend/handlers/`:
   ```python
   # backend/handlers/new_handler.py
   from fastapi import APIRouter
   
   router = APIRouter(prefix="/new", tags=["new"])
   
   @router.post("/action")
   async def handle_action(request: ActionRequest):
       # Implementation
   ```

2. Register in `message_router.py`:
   ```python
   intents["new_intent"] = new_handler.router
   ```

3. Add tests in `tests/handlers/test_new_handler.py`

### Adding a New Dashboard Page

1. Create page in `dashboard/pages/`:
   ```python
   # dashboard/pages/6_📈_NewPage.py
   import streamlit as st
   
   def show():
       st.title("New Page")
       # Implementation
   
   if __name__ == "__main__":
       show()
   ```

## Documentation

- Update API docs for endpoint changes
- Add docstrings to new functions
- Update README if adding features
- Add examples for new functionality

## Review Process

1. All PRs require at least one review
2. CI must pass (linting, tests)
3. Documentation must be updated
4. No merge conflicts

## Getting Help

- Open an issue for bugs
- Start a discussion for questions
- Tag maintainers for urgent issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
