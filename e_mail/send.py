import smtplib

from telebot.types import Message
from telebot import TeleBot
from convert_time_from_unix import convert
from properties import const
from .send_raw import send_raw


def send(bot: TeleBot, message: Message, email: str, caption: str) -> bool:
    chat, sender = _get_chat_and_sender(message)
    body = f"""
        <html><head></head><body>
        <b>ВАЖНОЕ - Вы отметили данное сообщение</b>
        <p><b>Чат:</b> <i>{chat}</i></p>
        <p><b>Отправитель:</b> <i>{sender}</i></p>
        <p><b>Время написания:</b> <i>{convert(message.forward_date)}</i></p>
        <b>Оригинальное сообщение:</b>
        <br>
        <i>{caption}</i>
        </body></html>
        """
    try:
        # TODO: `send_raw` returns a dict with possible errors. Deal with it
        send_raw(const("botEmail"), const("botEmailPassword"), email, body)
        return True
    except smtplib.SMTPRecipientsRefused as err:
        code, msg = err.recipients[email]
        if code == 501:
            key = const("botLetterSendInvalidEmailErrorMsg") % email
        else:
            key = msg.decode("utf-8")
        bot.send_message(message.chat.id, const("botLetterSendPreamble") + ' ' + key)
        return False


def _get_chat_and_sender(message: Message) -> tuple[str, str]:
    if message.forward_from:
        # Chat
        return message.chat.first_name, message.forward_from.first_name + f' (@{message.forward_from.username})'
    elif message.forward_from_chat:
        # Channel
        return message.forward_from_chat.title, message.forward_signature or "Аноним 🦹"
    elif message.forward_sender_name:
        # IDK wtf is that but this pops up sometimes
        return "Неизвестный чат", message.forward_sender_name
    else:
        # Unknown
        return "", ""
