import os
import time
import re

from src.logger import logger

# 语言到文件扩展名的映射
# 注意：LeetCode API 返回的 lang 字段可能有不同的大小写形式
FILE_FORMAT = {
    "C++": ".cpp",
    "cpp": ".cpp",
    "Python3": ".py",
    "python3": ".py",
    "Python": ".py",
    "python": ".py",
    "MySQL": ".sql",
    "mysql": ".sql",
    "Go": ".go",
    "golang": ".go",
    "Java": ".java",
    "java": ".java",
    "C": ".c",
    "c": ".c",
    "JavaScript": ".js",
    "javascript": ".js",
    "TypeScript": ".ts",
    "typescript": ".ts",
    "PHP": ".php",
    "php": ".php",
    "C#": ".cs",
    "csharp": ".cs",
    "Ruby": ".rb",
    "ruby": ".rb",
    "Swift": ".swift",
    "swift": ".swift",
    "Scala": ".scl",
    "scala": ".scl",
    "Kotlin": ".kt",
    "kotlin": ".kt",
    "Rust": ".rs",
    "rust": ".rs",
}

# 状态显示名到文件夹名的映射（去除特殊字符，确保是合法的文件夹名）
STATUS_FOLDER_MAP = {
    "Accepted": "Accepted",
    "Wrong Answer": "Wrong_Answer",
    "Time Limit Exceeded": "Time_Limit_Exceeded",
    "Memory Limit Exceeded": "Memory_Limit_Exceeded",
    "Output Limit Exceeded": "Output_Limit_Exceeded",
    "Runtime Error": "Runtime_Error",
    "Compile Error": "Compile_Error",
    "Presentation Error": "Presentation_Error",
}


def get_file_extension(lang):
    """根据语言获取文件扩展名，支持多种大小写形式"""
    if lang in FILE_FORMAT:
        return FILE_FORMAT[lang]
    # 尝试小写
    if lang.lower() in FILE_FORMAT:
        return FILE_FORMAT[lang.lower()]
    # 尝试首字母大写
    capitalized = lang.capitalize()
    if capitalized in FILE_FORMAT:
        return FILE_FORMAT[capitalized]
    # 都没找到，默认用 .txt
    logger.warning(f"Unknown language: {lang}, using .txt as extension")
    return ".txt"


def get_status_folder(status_display):
    """将状态显示名转换为合法的文件夹名"""
    if status_display in STATUS_FOLDER_MAP:
        return STATUS_FOLDER_MAP[status_display]
    # 不在映射中，手动清理特殊字符
    # 替换空格、斜杠等为下划线
    folder_name = re.sub(r'[\\/*?:"<>|\s]+', '_', status_display)
    return folder_name


def sanitize_filename(name):
    """清理文件名中的非法字符"""
    # 替换 Windows 不允许的文件名字符
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    return name


def generatePath(problem_id, problem_title, submission_language, OUTPUT_DIR, status_display=None):
    """
    生成代码文件的完整路径。
    
    Args:
        problem_id: 题目ID（如 "295" 或 "剑指 Offer 27"）
        problem_title: 题目标题
        submission_language: 提交语言
        OUTPUT_DIR: 输出根目录
        status_display: 提交状态（如 "Accepted", "Wrong Answer"），如果为 None 则不分子文件夹
    
    Returns:
        代码文件的完整路径
    """
    # 清理题目标题中的非法字符
    safe_title = sanitize_filename(problem_title)
    
    # 如果题目是传统的数字题号
    if problem_id[0].isdigit():
        problem_id_int = int(problem_id)
        problem_id_str = '{:0=4}'.format(problem_id_int)
        pathname = os.path.join(OUTPUT_DIR, problem_id_str + "." + safe_title)
        filename = problem_id_str + "-" + safe_title
    else:
        # 如果题目是面试题等
        safe_id = sanitize_filename(problem_id)
        pathname = os.path.join(OUTPUT_DIR, safe_id + "." + safe_title)
        filename = safe_id + "-" + safe_title
    
    # 如果有状态，创建状态子文件夹
    if status_display:
        status_folder = get_status_folder(status_display)
        pathname = os.path.join(pathname, status_folder)
    
    # 确保目录存在
    if not os.path.exists(pathname):
        os.makedirs(pathname)
    
    # 添加文件扩展名
    ext = get_file_extension(submission_language)
    filename = filename + ext
    
    return os.path.join(pathname, filename)


def generateProblemMdPath(problem_id, problem_title, OUTPUT_DIR):
    """
    生成题目描述 markdown 文件的路径。
    
    Args:
        problem_id: 题目ID
        problem_title: 题目标题
        OUTPUT_DIR: 输出根目录
    
    Returns:
        problem.md 文件的完整路径
    """
    safe_title = sanitize_filename(problem_title)
    
    if problem_id[0].isdigit():
        problem_id_int = int(problem_id)
        problem_id_str = '{:0=4}'.format(problem_id_int)
        pathname = os.path.join(OUTPUT_DIR, problem_id_str + "." + safe_title)
    else:
        safe_id = sanitize_filename(problem_id)
        pathname = os.path.join(OUTPUT_DIR, safe_id + "." + safe_title)
    
    if not os.path.exists(pathname):
        os.makedirs(pathname)
    
    return os.path.join(pathname, "problem.md")


def gitPush(OUTPUT_DIR):
    today = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    os.chdir(OUTPUT_DIR)
    instructions = ["git add .", "git status",
                    "git commit -m \"" + today + "\"", "git push"]
    try:
        for instruction in instructions:
            os.system(instruction)
            logger.info("~~~~~~~~~~~~~" + instruction + " finished! ~~~~~~~~")
    except Exception:
        logger.warning(
            "Git operations failed, please install git, skip it for now.")
