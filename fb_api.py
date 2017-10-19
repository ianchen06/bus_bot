import os

import requests

PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')

def send_msg(data):
    res = requests.post("https://graph.facebook.com/v2.6/me/messages",
                        params={'access_token': PAGE_ACCESS_TOKEN},
                        json=data)
    if res.status_code == 200:
        pass
        #app.logger.info("Successfully send msg id %s to user %s"%(res.json().get('message_id'), res.json().get('recipient_id')))
    else:
        #app.logger.info(res.text)
        pass

def send_text_msg(recipient_id, message_text):
    chunk_size = 640
    r = ''
    dd = []
    for row in message_text.split('\n'):
        if len(r+row+'\n') > chunk_size:
            dd.append(r)
            r = ''
        r = r+row+'\n'
    dd.append(r)
    for chunk in dd:
        data = {
            "recipient": {"id": recipient_id},
            "message": {"text": chunk}
        }
        send_msg(data)

def send_quick_reply(recipient_id, message_text):
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text,"quick_replies":[
      {
        "content_type":"text",
        "title":"再次查詢",
        "payload":"requery",
        "image_url":"https://cdn4.iconfinder.com/data/icons/ionicons/512/icon-refresh-128.png"
      },
      {
        "content_type":"text",
        "title":"到站提醒",
        "payload":"subscription",
        "image_url":"https://d30y9cdsu7xlg0.cloudfront.net/png/31771-200.png"
      },
      {
        "content_type":"text",
        "title":"加到常用公車",
        "payload":"add_to_favorites",
        "image_url":"https://cdn4.iconfinder.com/data/icons/small-n-flat/24/star-128.png"
      },
      {
        "content_type":"text",
        "title":"取消",
        "payload":"reset"
      },
      #{
      #  "content_type":"location"
      #}
    ]}
    }
    send_msg(data)
