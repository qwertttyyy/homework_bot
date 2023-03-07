class HomeworksNotFound(Exception):
    """Не найден список домашних заданий."""


class ResponseError(Exception):
    """Ошибка получения ответа от API."""


class UnexpectedHomeworkStatus(Exception):
    """Неожиданный статус домашнего задания."""


class HomeworkNameNotFound(Exception):
    """Не найдено название домашнего задания."""


class StatusNotFound(Exception):
    """Не найдено статус домашнего задания."""
