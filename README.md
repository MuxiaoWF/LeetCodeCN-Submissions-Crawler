# LeetCodeCN-Submissions-Crawler

[English](README-EN.md)

爬取力扣中国 [leetcode.cn](https://leetcode.cn) 上**你自己账号**的个人提交代码。

> ⚠️ 是爬取【你自己的账号】提交的代码，不是爬取他人的代码，更不是爬取官方代码。

## 功能特性

- **Cookie 登录**：通过 `LEETCODE_SESSION` + `CSRF_TOKEN` 认证，无需账号密码
- **多 AC 自动保存**：同一题多次 Accepted 全部保留，文件名含提交时间戳（如 `0001-TwoSum-20260806_190117.py`）
- **按状态过滤**：默认只下载 Accepted，可通过 `-A` 下载全部状态（Wrong Answer、TLE 等）
- **智能限流处理**：GraphQL 限流自动检测 + 指数退避重试，不会因限流丢失数据
- **代理容错**：代理断开自动重建 session，无缝恢复
- **跨运行安全**：时间戳命名保证重复运行不会产生重复文件

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/JiayangWu/LeetCodeCN-Submissions-Crawler.git
cd LeetCodeCN-Submissions-Crawler

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 cookies
cp configuration/config-example.json configuration/config.json
# 编辑 config.json，填入你的 LEETCODE_SESSION 和 CSRF_TOKEN

# 4. 运行
python main.py
```

## 配置说明

### config.json

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `LEETCODE_SESSION` | string | 是 | — | 浏览器 Cookie 中的 LEETCODE_SESSION |
| `CSRF_TOKEN` | string | 是 | — | 浏览器 Cookie 中的 csrftoken |
| `output_dir` | string | 否 | `./leetCode` | 代码输出目录 |
| `day` | number | 否 | `1000` | 爬取最近多少天的提交 |
| `overwrite` | bool | 否 | `false` | 是否覆盖已存在的文件 |
| `only_accepted` | bool | 否 | `true` | 是否只下载 Accepted（`false` = 全部状态） |

### 如何获取 Cookie

1. 浏览器打开 [leetcode.cn](https://leetcode.cn) 并登录
2. 按 F12 打开开发者工具 → Application → Cookies → leetcode.cn
3. 复制 `LEETCODE_SESSION` 和 `csrftoken` 的值

### 命令行参数

```
python main.py [options]

选项:
  -ls, --LEETCODE_SESSION     Cookie 中的 LEETCODE_SESSION
  -ct, --CSRF_TOKEN           Cookie 中的 csrftoken
  -o, --output                输出目录
  -d, --day                   爬取天数
  -O, --overwrite             覆盖已存在的文件
  -A, --all                   下载所有状态（默认只下载 Accepted）
```

命令行参数优先级高于 config.json。示例：

```bash
# 只下载最近 30 天的 Accepted，覆盖已有
python main.py -d 30 -O

# 下载所有状态的提交
python main.py -A

# 指定输出目录
python main.py -o ./my-leetcode-solutions
```

## 输出目录结构

```
leetCode/
├── 0001.Two-Sum/
│   ├── Accepted/
│   │   ├── 0001-Two-Sum-20260806_190117.py   ← 最新 AC
│   │   ├── 0001-Two-Sum-20260805_120000.py   ← 上一次 AC
│   │   └── 0001-Two-Sum-20260804_080000.py   ← 再上一次 AC
│   ├── Wrong_Answer/
│   │   └── 0001-Two-Sum-20260803_150000.py
│   └── problem.md                            ← 题目描述
├── 0015.3Sum/
│   └── ...
```

- 每道题一个文件夹
- 每种状态（Accepted / Wrong_Answer / ...）一个子文件夹
- 文件名包含提交时间戳，同一题多次提交自动保留
- `problem.md` 包含题目描述、难度、标签

## 支持的语言

`C++`, `Python`, `Python3`, `Java`, `JavaScript`, `TypeScript`, `Go`, `C`, `C#`, `Ruby`, `Swift`, `Scala`, `Kotlin`, `Rust`, `PHP`, `MySQL`

## 常见问题

**Q: 运行后提示 "超出访问限制"？**

A: 程序会自动检测限流并使用指数退避等待（15s → 30s → 60s → 120s → 240s），等待结束后自动重试，无需手动干预。如果频繁触发，建议增大 `day` 参数的时间跨度或使用 `-O` 减少重复下载。

**Q: 如何重新下载已保存的提交？**

A: 使用 `-O` 参数覆盖已有文件，或手动删除对应文件后重新运行。

**Q: 为什么只下载了 Accepted？**

A: 默认 `only_accepted: true`。使用 `-A` 参数或在 config.json 中设置 `"only_accepted": false` 即可下载所有状态。

## 致谢

- 原项目作者 [@JiayangWu](https://github.com/JiayangWu)
- [@Bobchenyx](https://github.com/Bobchenyx)
- 登录函数参考 [@fyears](https://gist.github.com/fyears/487fc702ba814f0da367a17a2379e8ba)

## 版本历史

**V4.0** (2026/08/11)
- Cookie 认证替代账号密码登录
- 提交时间戳命名，支持同一题多 AC 自动保存
- GraphQL 限流自动检测 + 指数退避重试
- 代理断连自动恢复
- 新增 `only_accepted` 过滤选项
- 命令行 `-A`/`-O` 参数

**V3.3** (2023/07/09)
- 重构 crawler 代码
- 从 GraphQL 获取 problem frontend id

**V3.2** (2023/07/09)
- GraphQL query 提取到独立文件

**V3.1** (2023/07/08)
- 添加命令行支持

**V3.0** (2023/07/07)
- 代码重构，自动创建完整目录路径

**V2.x 及更早** — 参见 git 历史