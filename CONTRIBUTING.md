# Contributing to Tacho Studio

Thank you for your interest in contributing to **Tacho Studio**! Contributions from transport operators, fleet compliance specialists, and Python developers are welcome.

## How You Can Contribute

- **Regulatory Edge Cases:** Report or add test cases for specific EU Regulation (EC) No 561/2006 and AETR rules (e.g., Article 9 ferry/train rest interruptions, multi-manning exceptions, or 12-day coach tour rules).
- **Binary Parsers:** Help expand direct `.DDD` / `.C1B` parsing for Vehicle Units (VU) and Generation 2 Smart Tachograph v2 records.
- **Localization:** Translate UI labels and audit report templates into additional European languages (English, German, Croatian/Serbian/Bosnian, Polish, etc.).
- **Bug Reports:** Open an issue with steps to reproduce, your Python/OS version, and anonymized sample data (never attach real driver card dumps containing personal data).

## Pull Request Workflow

1. Fork the repository and create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Add or update unit tests in `test_compliance.py`.
3. Run the test suite to ensure all checks pass:
   ```bash
   pytest
   ```
4. Commit your changes with a clear message and open a Pull Request.

## Code Style & Privacy Rules

- Follow standard PEP 8 formatting for Python code.
- **Privacy Strictness:** Never commit real driver names, card numbers, license plates, or personal `.DDD` files to the repository. Always use synthetic/anonymized test fixtures.
