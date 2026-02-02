import asyncio
import gzip
import json
import logging
import sys
import os
from contextlib import suppress
# from selenium import webdriver
from seleniumwire import webdriver
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
UPD: Алгопак поменяли сопособ получения token, усложнили. Но выход был найден.

Приведу шаги для Centos7, для Win7 шаги те же, команды почти такие же 
1)  Устанавливаем selenium, seleniumwire и понижаем версию blinker(иначе ошибки)
    python -m pip install --upgrade pip
    python -m pip install selenium selenium-wire
    python -m pip uninstall blinker
    python -m pip install blinker==1.7.0
    На Win7 была ошибка на этапе импорта, ошибка с openSSL:
    from cryptography.hazmat.bindings._rust import x509 as rust_x509
    ImportError: DLL load failed while importing _rust: Не найдена указанная процедура.
    Делаем следующее:
    pip uninstall cryptography
    pip install cryptography==41.0.7
    pip uninstall pyopenssl
    pip install pyopenssl==22.1.0
2)  Узнаем установленную версию Chrome (google-chrome --version)
3)  Скачиваем для своей системы для этой версии драйвер
    Если до версии 115, то https://sites.google.com/chromium.org/driver/downloads
    После 115 версии можно использовать webdriver-manager, но я бы крайне не советовал!
    Основная страница: https://github.com/GoogleChromeLabs/chrome-for-testing
    Нам нужна https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json
    Ищем свою версию под свою систему (chromedriver - linux64 - url), скачиваем, unzip, запоминаем путь path_driver
4)  Тестируем работоспособность. Ответ: "ok:token" или "no:error_mess | step_error"
    Получить токен:
    python moex_token.py 'login' 'password' 'path_driver' 0
    Обновить токен:
    python moex_token.py 'login' 'password' 'path_driver' 1
    Получить токен и посмотреть как это выглядит в браузере на windows:
    python moex_token.py 'login' 'password' 'path_driver' 0 0
5)  Потом можно использовать в проекте, когда токен слетает. Понимаем это, когда начинаются ошибки 
    {"message":"Validation error","http_status_code":401} 
    которые повторяются n-ое количество раз вподряд.
    from moex_token import token_work
    token = await token_work(login, password, path_driver, 1)
    if token["success"]:
        new_token, exp_token = token["message"], token["exp"]
    else:
        error = token["message"]
        step = token["error"]
"""
# endregion
# ----------------------------------------------------------------------------------------------------------------------

# region Константы для парсинга данных
LINK_MOEX = "https://data.moex.com/"
LINK_MOEX_ACC = "https://data.moex.com/personal-account"
TL = 15  # time limit sec
BUTTON_LOGIN_START = (By.CLASS_NAME, 'styles_redBtn__Q4bsx')
INPUT_PHONE = (By.NAME, 'phone')
INPUT_PASSWORD = (By.NAME, 'password')
BUTTON_LOGIN = (By.CLASS_NAME, 'filled')
ERROR_LOGIN = (By.TAG_NAME, "blockquote")
BUTTON_CHOOSE = (By.CLASS_NAME, 'styles_productButton__h7DdA')
BUTTON_API_KEY = (By.CLASS_NAME, 'styles_blackBtn__N8s4F')
DIV_BUTTONS_TOKEN = (By.CLASS_NAME, 'styles_buttonsWrapper__wFP91.flex')
BUTTON_TASK_TOKEN = (By.CLASS_NAME, 'p-button.p-component.p-button-icon-only')
SPAN_TOKEN_COPIED = (By.CLASS_NAME, 'p-toast-summary')
INPUT_API_KEY = (By.ID, "apikey")
EXP_TOKEN = (By.CLASS_NAME, 'styles_nonExpiredBlock__CHbQn')
TEXTAREA_WEBCHAT = (By.CLASS_NAME, 'webchat-icon')
TEXTAREA_I = (By.CLASS_NAME, 'webchat-userinput')
URL_HAVE_TOKEN = '/search'  # _____/moex-datashop-datashopservice/api/subscriptions/v1/search
URL_UPD_TOKEN = '/update-token'  # /moex-datashop-datashopservice/api/subscriptions/v1/12345/update-token
AVA_ACC = (By.CLASS_NAME, "styles_avatar__ldWIN")
A_LINK = (By.CSS_SELECTOR, "a[href='/personal-account']")

BUTTON_UPDATE = (By.CLASS_NAME, '')

logger = logging.getLogger(__name__)
# endregion
# ----------------------------------------------------------------------------------------------------------------------


async def set_res(success: bool, message: str, error: str = "", exp: str = "") -> dict:
    return {"success": success, "message": message, "error": error, "exp": exp}


async def task_subprocess(login: str, password: str, exe_path: str, update_token: int, timeout: float) -> str:
    """
    Выполняем ассинхронный сопроцесс
    :param login:           логин на data.moex
    :param password:        пароль на data.moex
    :param exe_path:        адрес webdrivwer
    :param update_token:    обновляем токен или просто получаем
    :param timeout:         таймаут ожидания
    :return: str
    """
    try:
        # выполнение скрипта как __main__
        code = [sys.executable, os.path.abspath(__file__), login, password, exe_path, str(update_token)]
        # Создаем подпроцесс и перенаправляем стандартный вывод и ввод в канал `PIPE`.
        proc = await asyncio.create_subprocess_exec(*code, stdout=asyncio.subprocess.PIPE, stdin=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.exceptions.TimeoutError:
            logger.error(f"[task_subprocess]: Получаем токен дольше запланированного времени {timeout} cек")
            stdout, stderr = await proc.communicate()  # продлжаем ждать
            await proc.wait()  # ждем завершения
        return stdout.decode('utf8').rstrip()
    except Exception as e:
        return f"no:except_subprocess: {repr(e)}"


async def token_work(login: str, password: str, exe_path: str, update_token: int, headless: int = 1) -> dict:
    """
    Проверяем работоспособность текущих настроек парсинга, получаем токен и меняем его, если update_token
    :param login: логин
    :param password: пароль
    :param exe_path: путь до webdriver Chrome
    :param update_token: если не 0, то обновляем токен, иначе просто получаем текущий
    :param headless: если не 0, то скрытый режим (без графического запуска)
    :return: возвращаем {"succes": bool, "message": str, "error": str, "exp": str} | в error этап, на котором ошибка
    """
    service = Service(executable_path=exe_path)  # log_path=os.devnull
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
    options.add_argument("--window-size=1400,800")
    # Запуск веб-браузера без графического пользовательского интерфейса (GUI)
    if headless:
        options.add_argument('--headless')
    # Отключает изолированную среду (sandbox) Chrome. Позволяет запускать браузер без ошибок в контейнерах и виртуальных
    # машинах.
    options.add_argument("--no-sandbox")
    # Использует /get_data_system вместо /dev/shm (общая память между процессами в Linux) При запуске в контейнерах
    # Docker стандартный /dev/shm имеет ограниченный размер, что может вызывать сбои.
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

        # ищем окна логин и пароль, заполняем, жмем залогиниться
        step_s = "input_phone"
        i_phone = WebDriverWait(driver, TL).until(ec.presence_of_element_located(INPUT_PHONE))
        step_s = "input_password"
        i_password = WebDriverWait(driver, TL).until(ec.presence_of_element_located(INPUT_PASSWORD))
        step_s = "button_login"
        b_login = WebDriverWait(driver, TL).until(ec.presence_of_element_located(BUTTON_LOGIN))
        i_phone.send_keys(login)
        i_password.send_keys(password)
        b_login.click()

        # Ждем загрузки страницы. Ищем окно пароля на странице, если его нет, то всё ОК
        step_s = "login_wait"
        WebDriverWait(driver, TL).until(lambda d: d.execute_script("return document.readyState") == "complete")
        try:
            driver.find_element(*INPUT_PASSWORD)
            err = WebDriverWait(driver, 1).until(ec.presence_of_element_located(ERROR_LOGIN))
            return await set_res(False, err.text)
        except TimeoutException:
            return await set_res(False, "Проблема с входом под текущими логином и паролем")
        except NoSuchElementException:
            pass

        # надо дождаться, пока подгрузит данные - появится кнопка выбора продукта
        step_s = "button_choose_product"
        WebDriverWait(driver, TL).until(ec.presence_of_element_located(BUTTON_CHOOSE))

        # открываем страницу с нашими данными = не всегда срабатывает, поэтому можно так
        # driver.get(LINK_MOEX_ACC)
        # Нажимаем на аватарку аккаунта
        step_s = "div_ava"
        ava_acc = WebDriverWait(driver, TL).until(ec.presence_of_element_located(AVA_ACC))
        ava_acc.click()
        # Нажимаем на Личный кабинет
        step_s = "a_ls"
        a_link = WebDriverWait(driver, TL).until(ec.presence_of_element_located(A_LINK))
        a_link.click()

        # Жмем кнопку API Key
        step_s = "button_api_key"
        b_api_key = WebDriverWait(driver, TL).until(ec.presence_of_element_located(BUTTON_API_KEY))
        b_api_key.click()

        # ищем div, в котором находятся 2 кнопки: копирования и обновляения
        step_s = "div_task_token"
        d_token = WebDriverWait(driver, TL).until(ec.presence_of_element_located(DIV_BUTTONS_TOKEN))

        # получаем список из двух кнопок: 0 - copy, 1 - update
        step_s = "buttons_task_token"
        b_token = d_token.find_elements(*BUTTON_TASK_TOKEN)

        # если нужно обновить токен
        token_s = ""
        if update_token:
            step_s = "button_update_token"
            # сохраняем старый урезанный токен
            i_token = WebDriverWait(driver, TL).until(ec.presence_of_element_located(INPUT_API_KEY))
            old_short_token = i_token.get_property("value")
            # обновляем токен
            b_token[1].click()
            # ждем изменения значения в окне токена
            WebDriverWait(driver, TL).until(lambda d: i_token.get_property("value") != old_short_token)

            step_s = "button_update_token_request"
            for req in driver.requests:
                if req.url.endswith(URL_UPD_TOKEN):
                    json_str = gzip.decompress(req.response.body).decode('utf-8')
                    json_d = json.loads(json_str)
                    token_s = json_d["apiKey"]
                    break
        else:
            step_s = "button_copy_token_request"
            for req in driver.requests:
                if req.url.endswith(URL_HAVE_TOKEN):
                    json_str = gzip.decompress(req.response.body).decode('utf-8')
                    json_d = json.loads(json_str)
                    token_s = json_d["data"]["rows"][0]["apiKey"]
                    break

        # проблема с токеном
        if not token_s:
            return await set_res(False, "Проблема с получением токена")

        # время действия ключа
        with suppress(Exception):
            token_exp_s = ""
            p_exp_token = WebDriverWait(driver, 1).until(ec.presence_of_element_located(EXP_TOKEN))
            token_exp_s = p_exp_token.text

        return await set_res(True, token_s, exp=token_exp_s)

    except TimeoutException:
        # with open('saved_page.html', 'w+', encoding="utf-8") as f:
        #     f.write(driver.page_source)
        return await set_res(False, "Ошибка парсинга", error=step_s)
    except Exception as e:
        return await set_res(False, f"exeption: {repr(e)}", error=step_s)
    finally:
        driver.close()


async def main():
    if len(sys.argv) < 4:
        print("no:Не все параметры переданы. Необходимо: 'login' 'password' 'path_driver' '1 or 0'")
        exit(0)
    res_d = await token_work(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
    print(f'{"ok:" if res_d["success"] else "no:"}{res_d["message"]}{" | " + res_d["error"] if res_d["error"] else ""}')

    # для debug
    # login, password = 'login', 'pass'
    # web_driver_path = r'C:\Program Files (x86)\Google\Chrome\chromedriver.exe'
    # upd = 0
    # res_d = await token_work(login, password, web_driver_path, upd)
    # print(f'{"ok:" if res_d["success"] else "no:"}{res_d["message"]}{" | " + res_d["error"] if res_d["error"] else ""}')


if __name__ == '__main__':
    asyncio.run(main())

# end
