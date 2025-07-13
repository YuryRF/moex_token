import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ----------------------------------------------------------------------------------------------------------------------

# region Описание. Использование.
"""
Имеем логин и пароль к https://data.moex.com/. Чтоб получить или сменить token, приходится использовать selenium, т.к.
параметры генерируются javascript. Сперва была мысль залогиниться, получить нужные данные, а потом requests получать то,
что хотим. Но и там тоже возникает проблема с параметрами. Поэтому, используем selenium и всё.

Приведу шаги для Centos7, для WIN шаги те же, команды другие 
0)  Устанавливаем selenium (python -m pip install selenium)
1)  Узнаем установленную версию Chrome (google-chrome --version)
2)  Скачиваем для своей системы для этой версии драйвер
    Если до версии 115, то https://sites.google.com/chromium.org/driver/downloads
    После 115 версии можно использовать webdriver-manager, но я бы крайне не советовал!
    Основная страница: https://github.com/GoogleChromeLabs/chrome-for-testing
    Нам нужна https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json
    Ищем свою версию под свою систему (chromedriver - linux64 - url), скачиваем, unzip, запоминаем путь path_driver
3)  Тестируем работоспособность
    python moex_token.py 'login' 'password' 'path_driver'
4)  Потом можно использовать в проекте, когда токен слетает. Понимаем это, когда начинаются ошибки 
    которые повторяются n-ое количество раз вподряд.
    from moex_token import token_work
    token = token_work(login, password, path_driver, True)
    if token["success"]:
        new_token = token["message"]
    else:
        error = token["message"]
        step = token["error"]
"""
# endregion
# ----------------------------------------------------------------------------------------------------------------------

# region Константы для парсинга данных
LINK_MOEX = "https://data.moex.com/"
LINK_MOEX_ACC = "https://data.moex.com/personal-account"
TL = 10  # time limit sec
BUTTON_LOGIN_START = (By.CLASS_NAME, 'styles_redBtn__Q4bsx')
INPUT_PHONE = (By.NAME, 'phone')
INPUT_PASSWORD = (By.NAME, 'password')
BUTTON_LOGIN = (By.CLASS_NAME, 'filled')
ERROR_LOGIN = (By.TAG_NAME, "blockquote")
BUTTON_CHOOSE = (By.CLASS_NAME, 'styles_productButton__h7DdA')
BUTTON_API_KEY = (By.CLASS_NAME, 'styles_blackBtn__N8s4F')
API_KEY = (By.ID, "apikey")
BUTTON_UPDATE = (By.CLASS_NAME, 'styles_whiteBtn__aidwt')

# endregion
# ----------------------------------------------------------------------------------------------------------------------


def token_work(login: str, password: str, exe_path: str, change_token: bool) -> dict:
    """
    Проверяем работоспособность текущих настроек парсинга, получаем токен и меняем его, если change_token
    :param login: логин
    :param password: пароль
    :param exe_path: путь до webdriver Chrome
    :param change_token: если True, то обновляем токен, иначе просто получаем текущий
    :return: возвращаем словарь типа {"success": bool, "message": str, error: str} | в error этап, на котором происходит
    ошибка парсинга
    """
    def set_res(success: bool, message: str, error: str = "") -> dict:
        return {"success": success, "message": message, "error": error}

    service = Service(executable_path=exe_path)
    options = webdriver.ChromeOptions()
    # Отключает флаг enable-automation, который указывает, что браузер запущен через Selenium.
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # Отключаем изображения (нам они не нужны)
    options.add_experimental_option("prefs", {"profile.default_content_setting_values": {"images": 2, }})
    # Отключает автоматическое расширение Selenium Automation Extension, которое браузер добавляет при запуске.
    options.add_experimental_option("useAutomationExtension", False)
    # Отключает специальную функцию Blink (рендеринг-движок Chrome), которая помечает браузер как управляемый
    # автоматизированными инструментами.
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Отключает WebRTC, который может раскрыть реальный IP-адрес пользователя.
    options.add_argument("--disable-webrtc")
    # Устанавливаем размер экрана, чтоб все кнопки влезли
    options.add_argument("--window-size=1400,600")
    # Запуск веб-браузера без графического пользовательского интерфейса (GUI)
    options.add_argument('--headless')
    # Отключает изолированную среду (sandbox) Chrome. Позволяет запускать браузер без ошибок в контейнерах и виртуальных
    # машинах.
    options.add_argument("--no-sandbox")
    # Использует /tmp вместо /dev/shm (общая память между процессами в Linux) При запуске в контейнерах Docker
    # стандартный /dev/shm имеет ограниченный размер, что может вызывать сбои.
    options.add_argument("--disable-dev-shm-usage")
    # Отключает аппаратное ускорение через GPU. (Полезно при запуске в headless-режиме, так как без GPU могут возникать
    # ошибки рендеринга.)
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options, service=service)
    step_s = ""
    try:
        # открываем стартовую страницу
        driver.get(LINK_MOEX)

        # нажимаем на Вход
        step_s = "button_login_start"
        b_login_start = WebDriverWait(driver, TL).until(ec.presence_of_element_located(BUTTON_LOGIN_START))
        b_login_start.click()

        # ищем необходимые окна, заполняем, жмем логин
        step_s = "input_phone"
        i_phone = WebDriverWait(driver, TL).until(ec.presence_of_element_located(INPUT_PHONE))
        step_s = "input_password"
        i_password = WebDriverWait(driver, TL).until(ec.presence_of_element_located(INPUT_PASSWORD))
        step_s = "button_login"
        b_login = WebDriverWait(driver, TL).until(ec.presence_of_element_located(BUTTON_LOGIN))
        i_phone.send_keys(login)
        i_password.send_keys(password)
        b_login.click()

        # Ждем загрузки страницы
        step_s = "login_wait"
        WebDriverWait(driver, TL).until(lambda d: d.execute_script("return document.readyState") == "complete")
        try:
            driver.find_element(*INPUT_PHONE)
            err = WebDriverWait(driver, 1).until(ec.presence_of_element_located(ERROR_LOGIN))
            return set_res(False, err.text)
        except TimeoutException:
            return set_res(False, "Проблема с входом под текущими логином и паролем")
        except NoSuchElementException:
            pass

        # надо дождаться, пока подгрузит данные - появится кнопка выбора продукта
        step_s = "button_choose_product"
        WebDriverWait(driver, TL).until(ec.presence_of_element_located(BUTTON_CHOOSE))

        # открываем страницу с нашими данными
        driver.get(LINK_MOEX_ACC)

        step_s = "button_api_key"
        b_api_key = WebDriverWait(driver, TL).until(ec.presence_of_element_located(BUTTON_API_KEY))
        b_api_key.click()

        step_s = "get_token"
        token_element = WebDriverWait(driver, TL).until(ec.presence_of_element_located(API_KEY))
        token_s = token_element.get_property('value')

        step_s = "button_update"
        try:
            b_update = driver.find_element(*BUTTON_UPDATE)
        except NoSuchElementException:
            return set_res(True, token_s, step_s)

        # только получаем токен
        if not change_token:
            return set_res(True, token_s)

        # меняем токен
        b_update.click()

        # Ждем изменения значения в окне токена
        step_s = "update_token_wait"
        WebDriverWait(driver, TL).until(lambda d: d.find_element(*API_KEY).get_attribute("value") != token_s)

        return set_res(True, token_element.get_property('value'))

    except TimeoutException:
        return set_res(False, "Ошибка парсинга", step_s)
    except Exception as e:
        return set_res(False, f"exeption: {repr(e)}", step_s)
    finally:
        driver.close()


if __name__ == '__main__':
    if len(sys.argv) > 3:
        print("Проверяем работоспособность текущих настроек парсинга")
        print(f"login:       {sys.argv[1]}")
        print(f"password:    {sys.argv[2]}")
        print(f"path_driver: {sys.argv[3]}")
        print("wait...")
        print(f"result: {token_work(sys.argv[1], sys.argv[2], sys.argv[3], False)}")
    else:
        print("Не все параметры переданы")
