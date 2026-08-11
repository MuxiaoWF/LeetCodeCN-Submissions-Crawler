import json
import time

import requests


class LeetcodeClient:
    LOGIN_PATH = 'accounts/login/'
    GRAPHQL_PATH = 'graphql/'

    def __init__(
            self,
            LEETCODE_SESSION,
            CSRF_TOKEN,
            sleep_time=5,
            base_url='https://leetcode.cn/',
            logger=None) -> None:
        self.sleep_time = sleep_time
        self.endpoint = base_url
        self.logger = logger

        self.client = requests.session()

        # 设置 cookies
        self.client.cookies.set('LEETCODE_SESSION', LEETCODE_SESSION)
        self.client.cookies.set('csrftoken', CSRF_TOKEN)

        self.client.encoding = "utf-8"

        self.headers = {
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'X-CSRFToken': CSRF_TOKEN,  
            'Referer': base_url
        }

    def login(self) -> None:
        """验证硬编码的 cookies 是否有效"""
        ATTEMPT = 3

        for try_cnt in range(ATTEMPT):
            try:
                test_url = self.endpoint + "api/submissions/?offset=0&limit=1"

                self.logger.info(f"Testing authentication with: {test_url}")
                result = self.client.get(test_url, headers=self.headers)

                self.logger.info(f"Auth test response status: {result.status_code}")

                if result.ok:
                    try:
                        data = result.json()
                        self.logger.info("Authentication successful - cookies are valid!")
                        self.logger.info(f"Response has submissions_dump: {'submissions_dump' in data}")
                        return
                    except json.JSONDecodeError:
                        self.logger.error(f"Failed to parse response: {result.text[:500]}")
                else:
                    self.logger.warning(f"Request failed with status: {result.status_code}")
                    self.logger.warning(f"Response: {result.text[:500]}")

                    if result.status_code == 403:
                        self.logger.error("403 Forbidden - CSRF token may be invalid")
                        self.logger.error("Please get a fresh CSRF token from browser")
                    elif result.status_code == 401:
                        self.logger.error("401 Unauthorized - Session cookie may be expired")
                        self.logger.error("Please get a fresh LEETCODE_SESSION from browser")

            except Exception as e:
                self.logger.error(f"Login verification failed with error: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

            if try_cnt != ATTEMPT - 1:
                self.logger.info(f"Retrying in {self.sleep_time} seconds...")
                time.sleep(self.sleep_time)

        self.logger.error("All login attempts failed!")
        raise Exception("LoginError: Cookie validation failed! Please update your LEETCODE_SESSION and CSRF token.")

    def _is_connection_error(self, e):
        """检测是否为代理/连接类错误（需要重建 session 的错误）"""
        import requests as req_lib
        if isinstance(e, req_lib.exceptions.ProxyError):
            return True
        if isinstance(e, req_lib.exceptions.ConnectionError):
            return True
        if isinstance(e, req_lib.exceptions.Timeout):
            return True
        # 检查链式异常
        cause = e.__cause__ if e.__cause__ else e.__context__
        while cause:
            if isinstance(cause, req_lib.exceptions.ProxyError):
                return True
            if isinstance(cause, req_lib.exceptions.ConnectionError):
                return True
            cause = cause.__cause__ if cause.__cause__ else cause.__context__
        return False

    def downloadCode(self, submission) -> dict:
        """获取提交详情，包括代码、状态、运行时间、内存和题目信息"""
        with open('query/query_download_submission', 'r') as f:
            query_string = f.read()

        data = {
            'query': query_string,
            'operationName': "mySubmissionDetail",
            "variables": {
                "id": str(submission["id"])
            }
        }

        max_retries = 5
        base_wait = self.sleep_time * 3  # 基础等待 15 秒（sleep_time 默认 5）
        conn_error_count = 0  # 连续连接错误计数
        for retry in range(max_retries):
            try:
                response = self.client.post(
                    self.endpoint + self.GRAPHQL_PATH,
                    json=data,
                    headers=self.headers,
                    timeout=30)  # 30s 超时，避免代理长时间挂起

                if response.status_code == 429:
                    conn_error_count = 0
                    wait_time = base_wait * (2 ** retry)  # 指数退避
                    self.logger.warning(f"HTTP 429 rate limited for submission {submission['id']}, "
                                        f"waiting {wait_time}s... (attempt {retry+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue

                if not response.ok:
                    conn_error_count = 0
                    self.logger.warning(f"downloadCode request failed with status {response.status_code}")
                    if retry < max_retries - 1:
                        wait_time = self.sleep_time * (retry + 1)
                        time.sleep(wait_time)
                        continue
                    return None

                result = response.json()

                if 'errors' in result:
                    conn_error_count = 0
                    error_msgs = [e.get('message', '') for e in result['errors']]
                    # 检测 GraphQL 层面的限流错误
                    is_rate_limit = any(
                        '访问限制' in msg or '超出' in msg or
                        'exceeded' in msg.lower() or 'rate limit' in msg.lower()
                        for msg in error_msgs
                    )

                    if is_rate_limit:
                        wait_time = base_wait * (2 ** retry)  # 指数退避
                        self.logger.warning(
                            f"GraphQL rate limited for submission {submission['id']}: "
                            f"{json.dumps(result['errors'], ensure_ascii=False)}, "
                            f"waiting {wait_time}s... (attempt {retry+1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        # 非限流错误，记录后重试
                        self.logger.error(f"GraphQL errors: {json.dumps(result['errors'], ensure_ascii=False)}")
                        if retry < max_retries - 1:
                            wait_time = self.sleep_time * (retry + 1)
                            time.sleep(wait_time)
                            continue
                        return None

                submission_details = result.get("data", {}).get("submissionDetail")
                if submission_details is None:
                    conn_error_count = 0
                    self.logger.warning(f"submissionDetail is null for submission {submission['id']}")
                    if retry < max_retries - 1:
                        time.sleep(self.sleep_time)
                        continue
                    return None

                conn_error_count = 0
                return submission_details

            except requests.exceptions.Timeout:
                conn_error_count += 1
                wait_time = base_wait * (2 ** retry)
                self.logger.warning(
                    f"Request timeout for submission {submission['id']}, "
                    f"connection errors: {conn_error_count}, "
                    f"waiting {wait_time}s... (attempt {retry+1}/{max_retries})"
                )
                if conn_error_count >= 2:
                    self._rebuild_session()
                    conn_error_count = 0
                time.sleep(wait_time)
                continue

            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
                conn_error_count += 1
                wait_time = base_wait * (2 ** retry)
                self.logger.warning(
                    f"Proxy/Connection error for submission {submission['id']}: {e}, "
                    f"connection errors: {conn_error_count}, "
                    f"waiting {wait_time}s... (attempt {retry+1}/{max_retries})"
                )
                # 连接错误后重建 session（代理可能在等待期间断开了连接）
                if conn_error_count >= 1:
                    self._rebuild_session()
                    conn_error_count = 0
                time.sleep(wait_time)
                continue

            except Exception as e:
                conn_error_count = 0
                self.logger.error(f"downloadCode error: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                if retry < max_retries - 1:
                    wait_time = self.sleep_time * (retry + 1)
                    time.sleep(wait_time)
                    continue
                return None

        return None

    def _rebuild_session(self):
        """重建 requests session，解决代理/连接断开问题"""
        LEETCODE_SESSION = self.client.cookies.get('LEETCODE_SESSION', '')
        CSRF_TOKEN = self.client.cookies.get('csrftoken', '')
        self.logger.info("Rebuilding HTTP session due to connection errors...")
        try:
            self.client.close()
        except Exception:
            pass
        self.client = requests.session()
        self.client.encoding = "utf-8"
        self.client.cookies.set('LEETCODE_SESSION', LEETCODE_SESSION)
        self.client.cookies.set('csrftoken', CSRF_TOKEN)

    def getSubmissionList(self, page_num):
        limit = 10
        offset = page_num * limit

        self.logger.info(
            f'Now scraping submissions list for page:{page_num} (offset={offset}, limit={limit})'
        )

        submissions_url = f"{self.endpoint}api/submissions/?offset={offset}&limit={limit}"

        max_retries = 3
        conn_error_count = 0
        for retry in range(max_retries):
            try:
                response = self.client.get(submissions_url, headers=self.headers, timeout=30)

                if not response.ok:
                    self.logger.warning(f"Request failed with status {response.status_code}")
                    self.logger.warning(f"Response: {response.text[:500]}")

                    if response.status_code == 429:
                        wait_time = (retry + 1) * self.sleep_time
                        self.logger.info(f"Rate limited, waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue

                result = response.json()

                if "detail" in result:
                    error_detail = result.get("detail", "Unknown error")
                    self.logger.error(f"API error: {error_detail}")

                    return {"submissions_dump": [], "has_next": False}


                if "submissions_dump" not in result:
                    self.logger.error(f"Unexpected response structure: {list(result.keys())}")
                    self.logger.debug(f"Full response: {json.dumps(result, ensure_ascii=False)[:500]}")
                    return {"submissions_dump": [], "has_next": False}


                submission_count = len(result.get("submissions_dump", []))
                self.logger.info(f"Successfully fetched {submission_count} submissions")

                return result

            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                self.logger.error(f"Response text: {response.text[:500]}")

                if retry < max_retries - 1:
                    time.sleep(self.sleep_time)
                    continue

            except requests.exceptions.Timeout:
                wait_time = self.sleep_time * (retry + 1)
                self.logger.warning(f"Request timeout, waiting {wait_time}s... (attempt {retry+1}/{max_retries})")
                time.sleep(wait_time)
                continue

            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
                conn_error_count += 1
                wait_time = self.sleep_time * (retry + 1) * 2
                self.logger.warning(
                    f"Proxy/Connection error: {e}, "
                    f"waiting {wait_time}s... (attempt {retry+1}/{max_retries})"
                )
                if conn_error_count >= 1:
                    self._rebuild_session()
                    conn_error_count = 0
                time.sleep(wait_time)
                continue

            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

                if retry < max_retries - 1:
                    time.sleep(self.sleep_time)
                    continue

        self.logger.error("All attempts to fetch submissions failed")
        return {"submissions_dump": [], "has_next": False}