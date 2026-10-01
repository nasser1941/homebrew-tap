# Homebrew tap for lcode

[lcode](https://github.com/nasser1941/lcode) is a local-first terminal coding agent powered by
open-weight models on your own GPU or Mac, via [Ollama](https://ollama.com).

```bash
brew install nasser1941/tap/lcode
```

Then, if you don't have Ollama yet, install it and pick a model for your machine:

```bash
brew install ollama
brew services start ollama
lcode setup
```

Upgrade with `brew upgrade lcode`. Works on macOS (Apple Silicon and Intel) and Linux (Homebrew on
Linux). Documentation: <https://nasser1941.github.io/lcode/>.

## How the formula is updated

A daily workflow ([`bump.yml`](.github/workflows/bump.yml)) looks for lcode releases on
[PyPI](https://pypi.org/project/lcode-cli/) that are at least a day old, regenerates
`Formula/lcode.rb` with [`scripts/update_formula.py`](scripts/update_formula.py) (pinning every
Python dependency to its source release, as Homebrew requires), installs and tests it on macOS and
Linux, and only then commits it. A new lcode release reaches Homebrew within about two days.

Problems installing? Please [open an issue in the lcode repository](https://github.com/nasser1941/lcode/issues).
