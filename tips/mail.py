from decouple import config

import sendgrid
from sendgrid.helpers.mail import To, From, Mail

from .config import DEBUG

FROM_EMAIL = config('FROM_EMAIL')  # notification email
ADMIN_EMAIL = config('ADMIN_EMAIL')  # admin email
ME = 'me'
ALL = 'all'
PYBITES = 'PyBites'

sg = sendgrid.SendGridAPIClient(api_key=config('SENDGRID_API_KEY'))


def send_email(to_email, subject, body,
               from_email=FROM_EMAIL,
               display_name=PYBITES,
               html=True):

    # newlines get wrapped in email, use html
    body = body.replace('\n', '<br>')

    # if local no emails
    if DEBUG:
        print('local env - no email, only print send_email args:')
        print('to_email: {}'.format(to_email))
        print('subject: {}'.format(subject))
        print('body: {}'.format(body))
        print('from_email: {}'.format(from_email))
        print('html: {}'.format(html))
        print()
        return

    from_email = From(email=from_email, name=display_name)

    to_email = ADMIN_EMAIL if to_email == 'me' else to_email
    to_email = To(to_email)

    # https://github.com/sendgrid/sendgrid-python/blob/master/sendgrid/helpers/mail/mail.py
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body if not html else None,
        html_content=body if html else None
    )

    response = sg.send(message)

    if str(response.status_code)[0] != '2':
        print(f'ERROR sending message, status_code {response.status_code}')

    return response


if __name__ == '__main__':
    subject = 'new user (test message)'
    body = '''test message with <a href='https://codechalleng.es/'>link</a>.'''
    response = send_email('me', subject, body)
    print(response.status_code)
    print(response.body)
    print(response.headers)
