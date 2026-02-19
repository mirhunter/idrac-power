# Contributing to iDRAC Power Monitor

Thank you for your interest in contributing to iDRAC Power Monitor! This document provides guidelines for contributing to the project.

## Project Origins

This project was initially developed collaboratively with GitHub Copilot CLI, an AI pair programming tool. The codebase, architecture, and documentation were created through an interactive development session between the project maintainer and AI assistance.

We welcome contributions from all developers, whether your work is AI-assisted, human-crafted, or a combination of both! What matters is the quality and usefulness of the contribution.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue on GitHub with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior vs actual behavior
- Your environment (OS, Python version, iDRAC firmware version)
- Any relevant error messages or logs

### Suggesting Features

Feature suggestions are welcome! Please open an issue with:
- A clear description of the feature
- The use case and why it would be valuable
- Any implementation ideas (optional)

### Submitting Pull Requests

1. **Fork the repository** and create a new branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines below

3. **Add tests** for new functionality

4. **Run the test suite** to ensure everything passes
   ```bash
   pytest
   ```

5. **Format your code** using the project's tools
   ```bash
   black src/ tests/
   ruff check src/ tests/
   mypy src/
   ```

6. **Commit your changes** with clear, descriptive commit messages
   ```bash
   git commit -m "Add feature: brief description"
   ```

7. **Push to your fork** and submit a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

- Follow [PEP 8](https://pep8.org/) style conventions
- Use type hints for function arguments and return values
- Keep functions focused and single-purpose
- Write docstrings for modules, classes, and functions
- Line length: 100 characters (enforced by Black)
- Use descriptive variable names

### Code Formatting

This project uses:
- **Black** for code formatting
- **Ruff** for linting
- **mypy** for type checking

Run these before submitting:
```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

## Testing

- Write tests for new features and bug fixes
- Ensure all tests pass before submitting
- Aim for good test coverage
- Use descriptive test names that explain what is being tested

Run tests with:
```bash
pytest --cov
```

## Documentation

- Update the README.md if you add new features or change behavior
- Add docstrings to new functions and classes
- Update help text for new CLI options
- Include examples for new functionality

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences
- Show empathy toward other community members

### Unacceptable Behavior

- Harassment, trolling, or inflammatory comments
- Personal attacks or insults
- Publishing others' private information
- Any conduct that would be inappropriate in a professional setting

## Questions?

Feel free to open an issue for any questions about contributing!

## License

By contributing to iDRAC Power Monitor, you agree that your contributions will be licensed under the MIT License.
