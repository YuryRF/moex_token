# moex_token
Получаем или обновляем токен для работы с Algopack.
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
