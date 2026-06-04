import os
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


GATEWAY_URL = "https://gateway.rmu.ac.th:1003/login?03773caefb7d1541"
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
CHECK_INTERVAL_SECONDS = 60
DEFAULT_CHECK_URL = "https://www.google.com"
LOG_FILE_PATH = None


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    formatted = f"[{now_text()}] {message}"
    print(formatted)

    if LOG_FILE_PATH:
        log_path = Path(LOG_FILE_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(formatted + "\n")


def check_internet(url: str = DEFAULT_CHECK_URL) -> bool:
    try:
        requests.get(url, timeout=5)
        return True
    except requests.RequestException:
        return False


def login_gateway(username: str, password: str) -> bool:
    driver = None
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--ignore-certificate-errors")

        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        driver.get(GATEWAY_URL)

        driver.find_element(By.NAME, "username").send_keys(username)
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)

        log("Gateway login submitted.")
        return True
    except (WebDriverException, NoSuchElementException, Exception) as err:
        log(f"Gateway login failed: {err}")
        return False
    finally:
        if driver is not None:
            driver.quit()


def load_gateway_credentials() -> tuple[str, str]:
    load_dotenv()
    user = os.getenv("GATEWAY_USER")
    password = os.getenv("GATEWAY_PASS")

    if not user or not password:
        raise ValueError("Missing GATEWAY_USER or GATEWAY_PASS in environment/.env")

    return user, password


def main() -> None:
    global LOG_FILE_PATH

    load_dotenv()
    LOG_FILE_PATH = os.getenv("GATEWAY_LOG_FILE")
    check_url = os.getenv("GATEWAY_CHECK_URL", DEFAULT_CHECK_URL)

    try:
        username, password = load_gateway_credentials()
    except ValueError as err:
        log(str(err))
        return

    log("Gateway monitor started.")

    while True:
        if not check_internet(check_url):
            log("No internet detected. Trying to login gateway...")
            login_gateway(username, password)
        else:
            log("Internet is available.")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
