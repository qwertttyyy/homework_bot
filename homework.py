import os
import sys
import time
import logging

import requests
import telegram
from dotenv import load_dotenv

from exeptions import *

load_dotenv()

PRACTICUM_TOKEN = os.getenv('API_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {
    'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s  %(levelname)s  %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка токенов."""

    variables = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }

    for var in variables:
        if variables[var] is None:
            logger.critical(f'Отсутствует обязательная переменная '
                            f'окружения: "{var}" '
                            f'Программа принудительно остановлена.')

            raise EnvironmentVariableNotFound(
                f'Отсутствует обязательная {var}!')


def send_message(bot, message):
    """Отправка сообщения."""

    try:
        logger.debug(f'Бот отправил сообщение "{message}"')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """Получение ответа API."""

    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.RequestException:
        homework_statuses = 404
    if homework_statuses.status_code != 200:
        raise ResponseError(f'Эндпоинт {ENDPOINT} недоступен. '
                            f'Код ответа: {homework_statuses.status_code}')

    return homework_statuses.json()


def check_response(response):
    """Проверка ответа API."""

    if 'homeworks' not in response or 'current_date' not in response:
        raise TypeError(f'Неверный формат ответа. Ответ: {response}')
    if not response['homeworks']:
        raise EmptyHomework('Список домашних работ пуст.')
    if not isinstance(response, dict):
        raise TypeError(f'Получен {type(response)}, а ожидался словарь.')
    if not isinstance(response['homeworks'], list):
        raise TypeError(f'Получен {type(response)}, а ожидался список.')


def parse_status(homework):
    """Извлечение статуса домашней работы."""

    if "homework_name" not in homework:
        raise HomeworkNameNotFound('Не найдено название работы.')
    homework_name = homework['homework_name']
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise UnexpectedHomeworkStatus(f'Неожиданный статус домашней работы.')
    verdict = HOMEWORK_VERDICTS[homework['status']]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_status = None
    last_response_is_error = False

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response['homeworks'][0]

            if homework['status'] != last_status:
                send_message(bot, parse_status(homework))
            else:
                logger.debug('Статус проверки работы не изменен.')
            last_response_is_error = False
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if not last_response_is_error:
                send_message(bot, message)
                last_response_is_error = True

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
