import os
import sys
import time
import logging

import requests
import telegram
from dotenv import load_dotenv

from exeptions import (
    HomeworksNotFound,
    ResponseError,
    UnexpectedHomeworkStatus,
    HomeworkNameNotFound,
    StatusNotFound
)


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
file_handler = logging.FileHandler(filename='bot_logs.log', encoding='utf-8')
file_handler.setFormatter(formatter)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)


def check_tokens():
    """Проверка токенов."""
    variables = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }

    token_availability = True
    for var in variables:
        if variables[var] is None:
            logger.critical(f'Отсутствует обязательная переменная '
                            f'окружения: "{var}" '
                            f'Программа принудительно остановлена.')

            token_availability = False

    return token_availability


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        logger.debug(f'Бот отправил сообщение "{message}"')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        return True
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка отправки сообщения: {error}')
        return False


def get_api_answer(timestamp):
    """Получение ответа API."""
    params = {'from_date': timestamp}
    try:
        homework_response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.RequestException:
        status_code = 404
        raise ResponseError(f'Эндпоинт {ENDPOINT} недоступен. '
                            f'Код ответа: {status_code}')
    if homework_response.status_code != 200:
        raise ResponseError(f'Эндпоинт {ENDPOINT} недоступен. '
                            f'Код ответа: {homework_response.status_code}')

    return homework_response.json()


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError(f'Получен {type(response)}, а ожидался словарь.')
    if 'homeworks' not in response or 'current_date' not in response:
        raise HomeworksNotFound(
            f'Не найден список домашних заданий. Ответ: {response}'
        )
    if not isinstance(response['homeworks'], list):
        raise TypeError(f'Получен {type(response)}, а ожидался список.')


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    if "homework_name" not in homework:
        raise HomeworkNameNotFound('Не найдено название работы.')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise StatusNotFound('Ключ "status" не найден.')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise UnexpectedHomeworkStatus('Неожиданный статус домашней работы.')
    verdict = HOMEWORK_VERDICTS[homework['status']]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Отсутствует обязательные переменные окружения.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response['homeworks']:
                homework = response['homeworks'][0]
                message = parse_status(homework)
                if message != last_message:
                    was_sent = send_message(bot, message)
                    if was_sent:
                        last_message = message
                        timestamp = response['current_date']
                else:
                    logger.debug('Статус проверки работы не изменен.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_message:
                was_sent = send_message(bot, message)
                if was_sent:
                    last_message = message

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
