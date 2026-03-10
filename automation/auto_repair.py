from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import requests
from monitoring.logger import system_log

def api_retry_policy():
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, ConnectionError)),
        before_sleep=lambda retry_state: system_log.warning(
            f"API Timeout/Error detected. Auto-repair attempt {retry_state.attempt_number}..."
        )
    )
