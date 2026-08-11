import json
import os
import time

from src.leetcode_client import LeetcodeClient
from src.logger import logger
from src.utils import generatePath, generateProblemMdPath

TEMP_FILE_PATH = "./temp_problemset.txt"
CONFIG_PATH = "./configuration/config.json"
PAGE_TIME = 5
START_PAGE = 0


class Crawler:
    def __init__(self, args) -> None:
        with open(CONFIG_PATH, "r") as f:
            config = json.loads(f.read())
            self.LEETCODE_SESSION = args.LEETCODE_SESSION if args.LEETCODE_SESSION else config['LEETCODE_SESSION']
            self.CSRF_TOKEN = args.CSRF_TOKEN if args.CSRF_TOKEN else config['CSRF_TOKEN']
            self.OUTPUT_DIR = args.output if args.output else config['output_dir']
            self.TIME_CONTROL = 3600 * 24 * \
                (args.day if args.day else config['day'])
            # overwrite: CLI > config > 默认 False
            cli_overwrite = hasattr(args, 'overwrite') and args.overwrite
            self.OVERWRITE = cli_overwrite if cli_overwrite else config.get('overwrite', False)
            # only_accepted: CLI --all 反转, config.only_accepted, 默认 True
            cli_download_all = hasattr(args, 'download_all') and args.download_all
            if cli_download_all:
                self.ONLY_ACCEPTED = False
            else:
                self.ONLY_ACCEPTED = config.get('only_accepted', True)
        self.c = 0
        # visited: key = problem_frontendId + "|" + lang + "|" + status, value = True（内存去重）
        self.visited = {}
        # 已保存题目描述的题目ID集合
        self.saved_problems = set()
        self.problems_to_be_reprocessed = []

        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR)

        self.lc = LeetcodeClient(
            self.LEETCODE_SESSION,
            self.CSRF_TOKEN,
            logger=logger
        )

    def isExpired(self, submission):
        cur_time = time.time()
        return cur_time - submission['timestamp'] > self.TIME_CONTROL

    def process_submissions(self, submissions):
        fail_count = 0
        for i, submission in enumerate(submissions):
            if self.isExpired(submission):
                return True

            # 如果配置为只下载 Accepted，跳过其他状态（零 API 消耗）
            if self.ONLY_ACCEPTED and submission.get('status_display', '') != 'Accepted':
                logger.info(f"Skip non-accepted: #{submission['id']} [{submission.get('status_display')}] {submission.get('title', '')}")
                continue

            try:
                made_api_call = self.process_submission(submission)
            except FileNotFoundError as e:
                logger.error(
                    "FileNotFoundError: Output directory doesn't exist!")
                made_api_call = False
            except TypeError as e:
                if fail_count == 2:
                    logger.warning(
                        "Code continually getting None. It may caused by service banning, wait minutes to continue.")
                    break
                fail_count += 1
                logger.warning("Code is None. Skip. Re-login")
                self.lc.login()
                time.sleep(PAGE_TIME * 2)
                made_api_call = True
            except Exception as e:
                logger.error(
                    "Unknown bug happened, please raise an issue with your log to the writer.")
                logger.error(type(e))
                logger.error(e)
                import traceback
                traceback.print_exc()
                made_api_call = False

            # 仅在实际调用了 API 后才延迟，避免对已跳过的提交空等
            if made_api_call and i < len(submissions) - 1:
                time.sleep(2)

        return False

    def process_submission(self, submission):
        """处理单个提交。返回 True 表示调用了 API（需要限流延迟），False 表示直接跳过。"""
        submission_id = str(submission['id'])

        # 下载提交详情，支持重试
        max_retries = 5
        base_wait = PAGE_TIME * 3  # 15s
        submission_details = None
        for retry in range(max_retries):
            submission_details = self.lc.downloadCode(submission)
            if submission_details is not None:
                break
            wait_time = base_wait * (2 ** retry)  # 指数退避
            logger.warning(
                f"Failed to get submission detail for id={submission_id}, "
                f"retry {retry+1}/{max_retries} in {wait_time}s..."
            )
            time.sleep(wait_time)

        # 如果获取详情失败，记录后跳过
        if submission_details is None:
            logger.warning(f"Failed to get submission detail for id={submission_id} after {max_retries} retries, skip.")
            return True  # 调用了 API（虽然失败），需要延迟

        # 检查 code 是否存在
        if not submission_details.get("code"):
            logger.warning(f"Submission {submission_id} has no code, skip.")
            return True

        question = submission_details.get("question", {})
        problem_frontendId = question.get("questionFrontendId", "")
        problem_title = question.get("translatedTitle", "")
        submission_lang = submission.get("lang", "")
        status_display = submission_details.get("statusDisplay", submission.get("status_display", "Unknown"))

        # 基本信息校验
        if not problem_frontendId or not problem_title or not submission_lang:
            logger.warning(f"Submission {submission_id} missing required fields, skip.")
            return True

        # 用提交时间戳命名，确保每条提交的文件名唯一且跨运行稳定
        # 格式: 0001-TwoSum-20260806_190117.py
        from datetime import datetime
        submission_timestamp = submission.get('timestamp', 0)
        if submission_timestamp:
            dt = datetime.fromtimestamp(submission_timestamp)
            time_suffix = dt.strftime('%Y%m%d_%H%M%S')
        else:
            # fallback: 用提交 ID 保证唯一性
            time_suffix = submission_id

        full_path = generatePath(
            problem_frontendId, problem_title, submission_lang,
            self.OUTPUT_DIR, status_display
        )
        base_no_ext, ext = os.path.splitext(full_path)
        full_path = f"{base_no_ext}-{time_suffix}{ext}"

        if not self.OVERWRITE and os.path.exists(full_path):
            logger.info(f"File already exists, skip: {full_path}")
        else:
            self.save_code(
                submission_details["code"],
                problem_frontendId,
                problem_title,
                submission_lang,
                status_display,
                submission_details.get("runtime", ""),
                submission_details.get("memory", ""),
                full_path
            )

        # 保存题目描述（每道题只保存一次）
        if problem_frontendId not in self.saved_problems:
            self.saved_problems.add(problem_frontendId)
            md_path = generateProblemMdPath(
                problem_frontendId, problem_title, self.OUTPUT_DIR
            )
            if not self.OVERWRITE and os.path.exists(md_path):
                logger.info(f"Problem md already exists, skip: {md_path}")
            else:
                self.save_problem_md(question, md_path)

        return True  # 调用了 API

    def save_code(self, code, problem_frontendId, problem_title, 
                  submission_lang, status_display, runtime, memory, full_path):
        """保存代码文件，在头部添加状态、运行时间等信息的注释"""
        # 根据语言生成注释前缀
        comment_prefix = self.get_comment_prefix(submission_lang)
        
        # 构建头部注释
        header_lines = []
        if comment_prefix:
            header_lines.append(f"{comment_prefix} 题目: {problem_frontendId}. {problem_title}")
            header_lines.append(f"{comment_prefix} 状态: {status_display}")
            if runtime:
                header_lines.append(f"{comment_prefix} 运行时间: {runtime}")
            if memory:
                header_lines.append(f"{comment_prefix} 内存消耗: {memory}")
            header_lines.append(f"{comment_prefix} 语言: {submission_lang}")
            header_lines.append("")
        
        header = "\n".join(header_lines)
        full_code = header + code if header else code
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(full_code)
            logger.info(f"Writing ends! [{status_display}] {full_path}")
            
            if self.is_temporary_problem(problem_frontendId):
                self.problems_to_be_reprocessed.append(
                    (full_path, problem_title, submission_lang))

    def get_comment_prefix(self, lang):
        """根据语言获取单行注释前缀"""
        lang_lower = lang.lower()
        # C 风格注释的语言
        c_style = ["c", "c++", "cpp", "java", "csharp", "go", "javascript", 
                   "typescript", "php", "swift", "scala", "kotlin", "rust"]
        # # 注释的语言
        hash_style = ["python", "python3", "ruby"]
        # -- 注释的语言
        sql_style = ["mysql"]
        
        if lang_lower in [l.lower() for l in c_style]:
            return "//"
        elif lang_lower in [l.lower() for l in hash_style]:
            return "#"
        elif lang_lower in [l.lower() for l in sql_style]:
            return "--"
        else:
            return ""

    def save_problem_md(self, question, md_path):
        """保存题目描述为 markdown 文件"""
        problem_id = question.get("questionFrontendId", "")
        title = question.get("translatedTitle", "")
        difficulty = question.get("difficulty", "")
        content = question.get("translatedContent", "")
        topic_tags = question.get("topicTags", [])
        
        # 构建 markdown 内容
        md_content = []
        md_content.append(f"# {problem_id}. {title}")
        md_content.append("")
        
        if difficulty:
            difficulty_emoji = {
                "Easy": "🟢",
                "Medium": "🟡",
                "Hard": "🔴"
            }.get(difficulty, "")
            md_content.append(f"**难度：** {difficulty_emoji} {difficulty}")
            md_content.append("")
        
        if topic_tags:
            tag_names = [tag.get("translatedName", tag.get("name", "")) for tag in topic_tags]
            tag_str = "、".join([t for t in tag_names if t])
            if tag_str:
                md_content.append(f"**标签：** {tag_str}")
                md_content.append("")
        
        md_content.append("---")
        md_content.append("")
        md_content.append("## 题目描述")
        md_content.append("")
        
        if content:
            # content 是 HTML，直接保留（markdown 支持 HTML）
            md_content.append(content)
        else:
            md_content.append("*暂无题目描述*")

        full_md = "\n".join(md_content)
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(full_md)
            logger.info(f"Problem md saved! {md_path}")

    def is_temporary_problem(self, problem_frontendId):
        if problem_frontendId[0].isdigit():
            format_name = '{:0>4}'.format(
                problem_frontendId)
            if format_name[0] >= "6":
                return True
        return False

    def process_temporary_problems(self):
        if os.path.exists(TEMP_FILE_PATH):
            with open(TEMP_FILE_PATH, "r") as f:
                for line in f.readlines():
                    try:
                        path, title, lang = line.rstrip().split(" ", 1)
                    except ValueError:
                        logger.warning("Your " + TEMP_FILE_PATH +
                                       " is in old format, delete all temp code.")
                        _, path = line.rstrip().split(" ", 1)
                        os.remove(path)
                    token = title + lang
                    if token in self.visited:
                        if not self.is_temporary_problem(self.visited[token]):
                            logger.info(
                                path + " is no longer a temporary problem, delete temp code.")
                            os.remove(path)
                        else:
                            self.problems_to_be_reprocessed.append(
                                (path, title, lang))

    def write_temorary_file(self):
        if self.problems_to_be_reprocessed:
            with open(TEMP_FILE_PATH, "w") as f:
                for full_path, problem_title, submission_lang in self.problems_to_be_reprocessed:
                    f.write(full_path + " " + problem_title +
                            " " + submission_lang + "\n")
                    logger.info("Record temporary code: " + full_path)

    def scraping(self):
        page_num = START_PAGE
        while True:
            submission_list = self.lc.getSubmissionList(page_num)
            expired = self.process_submissions(
                submission_list["submissions_dump"])
            if not submission_list.get("has_next") or expired:
                logger.info("No more submissions!")
                break
            page_num += 1
            time.sleep(PAGE_TIME)
        self.process_temporary_problems()
        self.write_temorary_file()

    def execute(self):
        # logger.info('Login')
        # self.lc.login()
        logger.info('Start scrapping')
        self.scraping()
        logger.info('End scrapping \n')
        # gitPush(self.OUTPUT_DIR)


if __name__ == '__main__':
    c = Crawler()
    c.execute()