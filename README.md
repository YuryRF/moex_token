# moex_token: async
Имеем логин и пароль к https://data.moex.com/. 
Чтоб получить или сменить **token**, приходится использовать **selenium**, т.к.
параметры генерируются **javascript**. Сперва была мысль залогиниться, получить нужные данные, а потом **requests** получать то,
что хотим. Но и там тоже возникает проблема с параметрами. Поэтому, используем **selenium** и всё.

Приведу шаги для Centos7, для WIN шаги те же, команды почти такие же 
- Устанавливаем **selenium** и **pyperclip**:
    ```bash
    python -m pip install selenium pyperclip
    ```
- Узнаем установленную версию Chrome 
    ```bash
    google-chrome --version
    ```
- Скачиваем для своей системы для этой версии драйвер:
    - Если до версии 115, то [WebDriver](https://sites.google.com/chromium.org/driver/downloads) 
    - После 115 версии можно использовать **webdriver-manager**, но я бы крайне не советовал!
    - Основная страница: [Github](https://github.com/GoogleChromeLabs/chrome-for-testing)
    - Нам нужна [github.io](https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json)
    - Ищем свою версию под свою систему ```chromedriver - linux64 - url```, скачиваем, **unzip**, запоминаем путь **path_driver**
- Тестируем работоспособность. Ответ: *ok:token* или *no:error_mess | step_error*
    - Получить токен:
    ```bash
    python moex_token.py 'login' 'password' 'path_driver' 0
    ```
    - Обновить токен:
    ```bash
    python moex_token.py 'login' 'password' 'path_driver' 1
    ```
- Потом можно использовать в проекте, когда токен слетает. Понимаем это, когда начинаются ошибки
    ```json
    {"message":"Validation error","http_status_code":401}
    ```
    которые повторяются n-ое количество раз вподряд.
    ```python
    from moex_token import token_work
    
    token = await token_work(login, password, path_driver, 1)
    if token["success"]:
        new_token, exp_token = token["message"], token["exp"]
    else:
        error = token["message"]
        step = token["error"]
    ```
