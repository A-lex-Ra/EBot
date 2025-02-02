import json
import mimetypes
import os
import tempfile
import googleapiclient.http
import httplib2

import database as db
from json import JSONDecodeError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client import clientsecrets
from oauth2client.client import OAuth2WebServerFlow, Credentials
from properties import const
from telebot.types import Message


def get_drive_service(bot, message):
    db.create_table_if_not_exists()
    user = db.create_user_if_not_exists_and_fetch_if_needed(message.from_user.id, do_fetch=True)
    try:
        credentials = Credentials.new_from_json(user.google_disk_credentials)
    except JSONDecodeError as err:
        bot.send_message(message.chat.id, const("botUserInvalidCredentialsError") % str(err))
        return
    http = httplib2.Http()
    credentials.authorize(http)
    return build('drive', 'v3', http=http)


# noinspection PyProtectedMember
def get_flow(bot, message, client_secrets, scope) -> OAuth2WebServerFlow | None:
    try:
        cs = json.loads(client_secrets)
    except JSONDecodeError as err:
        bot.send_message(message.chat.id, const("botGDClientSecretsInvalidErrorMsg") % str(err))
        return
    try:
        cs_type, cs_info = clientsecrets._validate_clientsecrets(cs)
        if cs_type in (clientsecrets.TYPE_WEB,
                       clientsecrets.TYPE_INSTALLED):
            constructor_kwargs = {
                'redirect_uri': None,
                'auth_uri': cs_info['auth_uri'],
                'token_uri': cs_info['token_uri'],
                'login_hint': None,
            }
            revoke_uri = cs_info.get('revoke_uri')
            optional = (
                'revoke_uri',
                'device_uri',
                'pkce',
                'code_verifier',
                'prompt'
            )
            for param in optional:
                try:
                    if locals()[param] is not None:
                        constructor_kwargs[param] = locals()[param]
                except KeyError:
                    pass

            return OAuth2WebServerFlow(
                cs_info['client_id'], cs_info['client_secret'],
                scope, **constructor_kwargs)
    except clientsecrets.InvalidClientSecretsError as err:
        bot.send_message(message.chat.id, const("botGDClientSecretsInvalidErrorMsg") % str(err))
    else:
        bot.send_message(message.chat.id, const("googleOAuth2UnsupportedFlowErr") + ' ' + cs_type)
    return None


def upload_from_message(bot, message: Message, **kwargs):
    """ Uploads content from message to Google Drive.
    bot: the bot
    message: message with photo or document
    **kwargs: custom filename or description for file
    Returns: id of the uploaded file
    """
    if message.content_type in ['document', 'audio', 'voice', 'video', 'photo']:
        file = message.__getattribute__(message.content_type)
    else:
        return
    if message.content_type == "photo":
        file = file[-1]

    file_info = bot.get_file(file.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    tmp = tempfile.NamedTemporaryFile(dir=const("tempFilesPath"), delete=False)
    tmp.seek(0)
    tmp.write(downloaded_file)
    tmp.close()
    uploaded_id = upload_file(bot, message, tmp.name, **kwargs)
    os.unlink(tmp.name)
    return uploaded_id


def upload_file(bot, message, filepath, filename='Important', description='Uploaded by EmailBot'):
    db.create_table_if_not_exists()
    bot_folder_id = db.create_user_if_not_exists_and_fetch_if_needed(message.from_user.id, do_fetch=True)\
        .google_disk_folder_id

    if (service := get_drive_service(bot, message)) is None:
        # TODO send_message
        return

    media_body = googleapiclient.http.MediaFileUpload(
        filename=filepath,
        mimetype=mimetypes.guess_type(filepath)[0],
        resumable=True
    )
    body = {
        'name': filename,
        'description': description,
        'parents': [bot_folder_id]
    }

    try:
        new_file = service.files().create(
            uploadType="resumable",
            body=body,
            media_body=media_body
        ).execute()
        file_title = new_file.get('name')
        service.close()
        if file_title == filename:
            bot.send_message(message.chat.id, const("GDFileUploadSuccess"))
            return new_file.get('id')
        else:
            bot.send_message(message.chat.id, const("GDFileUploadMaybeError") + f" {file_title} ~:~ {filename}")
    except HttpError as err:
        # TODO(developer) - Handle errors from drive API.
        bot.send_message(message.chat.id, const("GDFileUploadCreateError") + ' ' + str(err))
