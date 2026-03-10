# Contributing to Masker

Thank you for your interest in contributing to Masker! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/kiku-jw/masker.git
cd masker
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download spaCy models:
```bash
python -m spacy download en_core_web_sm
python -m spacy download ru_core_news_sm
```

4. Run the development server:
```bash
uvicorn app.main:app --reload
```

## Code Quality

### Linting

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for linting issues
ruff check app/

# Auto-fix linting issues
ruff check --fix app/

# Check formatting
ruff format --check app/

# Auto-format code
ruff format app/
```

### Type Checking

We use [mypy](https://mypy.readthedocs.io/) for static type checking:

```bash
mypy app/
```

### Testing

Run tests with pytest:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_detect.py -v
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the code style guidelines
4. **Run linting and tests** before committing:
   ```bash
   ruff check app/
   ruff format app/
   pytest
   ```
5. **Commit** with a descriptive message:
   ```bash
   git commit -m "feat: add new PII detection type"
   ```
6. **Push** to your fork and create a Pull Request

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add SSN detection support
fix: correct phone number regex for international formats
docs: update API reference with new endpoint
```

## Project Structure

```
masker/
├── app/
│   ├── api/           # API endpoints
│   │   ├── v1/        # API v1 routes
│   │   └── rapidapi/  # RapidAPI facade
│   ├── core/          # Configuration, logging
│   ├── middleware/    # HTTP middleware
│   ├── models/        # Pydantic schemas
│   ├── services/      # Business logic
│   └── main.py        # Application entry point
├── tests/             # Test files
├── docs/              # Documentation
└── examples/          # Usage examples
```

## Adding New PII Types

To add a new PII detection type:

1. Add regex pattern in `app/services/pii_detector.py`:
   ```python
   PATTERNS = {
       # ... existing patterns
       "SSN": re.compile(r'\d{3}-\d{2}-\d{4}'),
   }
   ```

2. Update `EntityType` in `app/models/schemas.py`:
   ```python
   EntityType = Literal["EMAIL", "PHONE", "CARD", "PERSON", "SSN"]
   ```

3. Add placeholder template in `app/services/redaction.py`:
   ```python
   PLACEHOLDER_TEMPLATES = {
       # ... existing templates
       "SSN": "<SSN>",
   }
   ```

4. Add tests in `tests/test_detect.py`

5. Update documentation

## Questions?

If you have questions, please open an issue on GitHub.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
