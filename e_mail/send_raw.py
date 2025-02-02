import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_raw(sender: str, sender_password: str, receiver: str, body: str):
    message = MIMEMultipart('alternative')
    message['Subject'] = "Link"
    message['From'] = sender
    message['To'] = receiver

    message.attach(MIMEText("Важное", 'plain'))
    message.attach(MIMEText(body, 'html'))

    mail = smtplib.SMTP('smtp.yandex.ru', 587)
    mail.ehlo()
    mail.starttls()
    mail.ehlo()
    mail.login(sender, sender_password)

    errors = mail.sendmail(sender, receiver, message.as_string())
    mail.quit()
    return errors
