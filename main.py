import os

from postmarker.core import PostmarkClient
from mistralai import Mistral

try:
    import dotenv
except ImportError:
    dotenv.load_dotenv()

RECEIVER_MAIL = os.getenv("RECEIVER_MAIL")
# TODO: Implement mail sending: https://postmarkapp.com/send-email/python
POSTMARK_SERVER_API_TOKEN = os.getenv("POSTMARK_SERVER_API_TOKEN")
postmark = PostmarkClient(server_token=os.getenv("POSTMARK_SERVER_API_TOKEN"))

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL")
mistral = Mistral(api_key=MISTRAL_API_KEY)



def main():
    chat_response = mistral.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {
                "role": "user",
                "content": "What is the meaning of life?"
            }
        ]
    )
    print(chat_response.choices[0].message.content)


if __name__ == "__main__":
    main()
