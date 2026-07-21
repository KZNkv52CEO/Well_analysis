# Contributing to Well Analysis

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Getting Started

### Prerequisites
- Python 3.8+
- git

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/KZNkv52CEO/Well_analysis.git
cd Well_analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with dev tools
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### Code Style

This project uses:
- **black** for code formatting
- **flake8** for linting
- **mypy** for type checking

Before committing, run:

```bash
# Format code
black well_analysis.py batch_process.py tests/

# Check linting
flake8 well_analysis.py batch_process.py tests/

# Type checking
mypy well_analysis.py batch_process.py
```

Or use pre-commit hooks (automatic on `git commit`):

```bash
pre-commit run --all-files
```

### Writing Tests

Add tests to `tests/test_well_analysis.py`:

```python
def test_new_feature():
    """Test description."""
    # Arrange
    input_data = ...
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_output
```

Run tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=well_analysis

# Run specific test
pytest tests/test_well_analysis.py::test_name -v
```

## Submitting Changes

1. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes** and add tests

3. **Run tests and linting**:
   ```bash
   pytest
   black --check well_analysis.py
   flake8 well_analysis.py
   ```

4. **Commit with clear message**:
   ```bash
   git commit -m "Add feature: description"
   ```

5. **Push and create pull request**:
   ```bash
   git push origin feature/my-feature
   ```

## Issues & Bug Reports

- Check existing issues before opening a new one
- Include minimal reproducible example
- Specify Python version and OS
- Attach LAS file sample if relevant (sanitized)

## Questions?

Open an issue with the `question` label or email the maintainer.

---

Thank you for contributing! 🎉
