# LeetCodeCN-Submissions-Crawler

[中文](README.md)

Crawl your **personal** code submissions from LeetCode China ([leetcode.cn](https://leetcode.cn)).

> ⚠️ This crawler fetches YOUR OWN submissions, not others' code or official solutions.

## Features

- **Cookie-based auth**: Login via `LEETCODE_SESSION` + `CSRF_TOKEN`, no password needed
- **Multi-AC preservation**: Every Accepted submission is saved with timestamp in filename (e.g. `0001-TwoSum-20260806_190117.py`)
- **Status filter**: Download only Accepted by default, or all statuses with `-A` flag
- **Smart rate-limiting**: Auto-detects GraphQL rate limits with exponential backoff retry
- **Proxy resilience**: Auto-rebuilds session on proxy disconnection, seamless recovery
- **Duplicate-safe**: Timestamp-based naming ensures zero duplicate files across runs

## Quick Start

```bash
# 1. Clone
git clone https://github.com/JiayangWu/LeetCodeCN-Submissions-Crawler.git
cd LeetCodeCN-Submissions-Crawler

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure cookies
cp configuration/config-example.json configuration/config.json
# Edit config.json with your LEETCODE_SESSION and CSRF_TOKEN

# 4. Run
python main.py
```

## Configuration

### config.json

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `LEETCODE_SESSION` | string | Yes | — | LEETCODE_SESSION cookie from browser |
| `CSRF_TOKEN` | string | Yes | — | csrftoken cookie from browser |
| `output_dir` | string | No | `./leetCode` | Output directory for code files |
| `day` | number | No | `1000` | How many days of submissions to fetch |
| `overwrite` | bool | No | `false` | Overwrite existing files |
| `only_accepted` | bool | No | `true` | Only download Accepted submissions |

### Getting Cookies

1. Open [leetcode.cn](https://leetcode.cn) in browser and log in
2. Press F12 → Application → Cookies → leetcode.cn
3. Copy `LEETCODE_SESSION` and `csrftoken` values

### CLI Arguments

```
python main.py [options]

Options:
  -ls, --LEETCODE_SESSION     LEETCODE_SESSION cookie value
  -ct, --CSRF_TOKEN           CSRF token cookie value
  -o, --output                Output directory
  -d, --day                   Days of submissions to fetch
  -O, --overwrite             Overwrite existing files
  -A, --all                   Download all statuses (default: Accepted only)
```

CLI arguments override config.json. Examples:

```bash
# Last 30 days, Accepted only, overwrite
python main.py -d 30 -O

# All statuses
python main.py -A

# Custom output directory
python main.py -o ./my-leetcode-solutions
```

## Output Structure

```
leetCode/
├── 0001.Two-Sum/
│   ├── Accepted/
│   │   ├── 0001-Two-Sum-20260806_190117.py   ← latest AC
│   │   ├── 0001-Two-Sum-20260805_120000.py   ← previous AC
│   │   └── 0001-Two-Sum-20260804_080000.py   ← even earlier AC
│   ├── Wrong_Answer/
│   │   └── 0001-Two-Sum-20260803_150000.py
│   └── problem.md                            ← problem description
├── 0015.3Sum/
│   └── ...
```

- One folder per problem
- One subfolder per submission status
- Timestamp in filename ensures all submissions are preserved
- `problem.md` contains description, difficulty, and tags

## Supported Languages

`C++`, `Python`, `Python3`, `Java`, `JavaScript`, `TypeScript`, `Go`, `C`, `C#`, `Ruby`, `Swift`, `Scala`, `Kotlin`, `Rust`, `PHP`, `MySQL`

## FAQ

**Q: I got "超出访问限制" (rate limited)?**

A: The crawler auto-detects rate limits and waits with exponential backoff (15s → 30s → 60s → 120s → 240s), then retries automatically. No manual intervention needed.

**Q: How to re-download saved submissions?**

A: Use `-O` to overwrite, or manually delete the files and re-run.

**Q: Why only Accepted submissions are downloaded?**

A: Default is `only_accepted: true`. Use `-A` flag or set `"only_accepted": false` in config.

## Credits

- Original author [@JiayangWu](https://github.com/JiayangWu)
- [@Bobchenyx](https://github.com/Bobchenyx)
- Login function adapted from [@fyears](https://gist.github.com/fyears/487fc702ba814f0da367a17a2379e8ba)

## Changelog

**V4.0** (2026/08/11)
- Cookie-based auth (no passwords)
- Timestamp-based file naming for multi-AC preservation
- GraphQL rate-limit detection with exponential backoff
- Proxy disconnection auto-recovery
- New `only_accepted` filter
- `-A` / `-O` CLI flags

**V3.3** (2023/07/09)
- Refactored crawler, GraphQL-based problem ID lookup

See [README.md](README.md) for full history.