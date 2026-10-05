# Contributing to jev-judge

First off, thank you for considering contributing to `jev-judge`! 🚀

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/00200200/jev-judge.git
   cd jev-judge
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

3. Run the test suite:
   ```bash
   pytest -v
   ```

## Pull Request Guidelines

1. Create a descriptive feature branch (`git checkout -b feat/new-evaluator`).
2. Add unit tests for your changes in `tests/test_jev_judge.py`.
3. Ensure all tests pass.
4. Open a PR with a clear description of the problem and solution.
