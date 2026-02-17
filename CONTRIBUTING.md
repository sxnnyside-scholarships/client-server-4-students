# Contributing to Client-Server 4 Students (C4SS)

First off — **thank you for wanting to contribute!** This project is developed by **Sxnnyside Scholarships** to help students learn, and every improvement, however small, makes that mission easier.

---

## How Can I Contribute?

### Reporting Bugs

- Open a [GitHub Issue](../../issues) with a clear title.
- Describe what you expected vs. what actually happened.
- Include your OS, Python version, and PyQt6 version.
- Add screenshots if the issue is visual.

### Suggesting Enhancements

We love ideas! Open an issue with the tag **enhancement** and explain:

1. What the feature is.
2. Why it helps students or teachers.
3. A rough description of how it could work.

> **Remember:** This project is intentionally simple. Proposals that add advanced or intimidating features may be politely declined to keep the learning curve smooth.

### Submitting Code

1. **Fork** the repository.
2. Create a branch: `git checkout -b my-feature`.
3. Make your changes following the coding guidelines below.
4. Test your changes manually (start the server, connect the client, transfer a file).
5. Commit with a clear message: `git commit -m "Add: description of change"`.
6. Push to your fork and open a **Pull Request**.

---

## Coding Guidelines

| Guideline | Details |
|---|---|
| **Language** | Python 3.12+ |
| **Style** | Follow PEP 8. Use type hints where reasonable. |
| **Comments** | Write for students — be clear, avoid jargon. |
| **Dependencies** | Do not add new libraries without discussion. |
| **Locale strings** | Never hardcode UI text. Add keys to both `en.json` and `es.json`. |
| **Themes** | Any new widget must look correct in both QSS themes. |

### Commit Message Prefixes

| Prefix | Use |
|---|---|
| `Add:` | New feature or file |
| `Fix:` | Bug fix |
| `Docs:` | Documentation only |
| `Style:` | Code formatting, no logic change |
| `Refactor:` | Code restructure, no behaviour change |
| `i18n:` | Localization changes |

---

## Adding a New Language

1. Copy `src/localization/en.json` to a new file (e.g. `fr.json`).
2. Translate every value (keep the keys identical).
3. Register the new code in `LocaleManager.SUPPORTED_LOCALES`.
4. Open a PR!

---

## Code of Conduct

All participants are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md). Be respectful, inclusive, and constructive.

---

## Questions?

If you're not sure whether something is worth contributing, open an issue and ask — we'd rather help you get started than miss a good idea.

**Contact:** [support.sxnnyside@sxnnysideproject.com](mailto:support.sxnnyside@sxnnysideproject.com)

**Website:** [https://www.sxnnysideproject.com](https://www.sxnnysideproject.com)

Happy coding!
