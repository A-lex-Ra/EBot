import database as db
from commands import handle_unknown_command
from e_mail.send import send
from google_drive.upload_from_message import upload_from_message
from properties import const


def listener(cb):
    def inner(bot, message):
        if message.forward_from or message.forward_from_chat or message.forward_sender_name:
            cb(bot, message)
        else:
            if message.content_type == "text":
                message.text = message.text.strip()
                if message.text.startswith("/"):
                    handle_unknown_command(bot, message)
                    return
            bot.send_message(message.from_user.id, const("botNotForwardedMessageLis"))
    return inner


def attachment_listener(name: str):
    @listener
    def inner(bot, message):
        if (file_id := upload_from_message(bot, message)) is None:
            return
        caption = message.caption if message.caption else ""
        text = caption + '<br>' + const(name) + ' ' + const("googleDiskFilePrefix") + file_id
        if send(bot, message, db.fetch_user(message.from_user.id).email, text):
            bot.send_message(message.from_user.id, const("botMessageSentToEmailLis"))
    return inner
