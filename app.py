import logging
import os
import json

from bs4 import BeautifulSoup
import requests
from flask import Flask, request, g, abort
import redis
import rethinkdb as r
from rethinkdb.errors import RqlRuntimeError, RqlDriverError

app = Flask(__name__)
gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.DEBUG)

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_NO = os.getenv('REDIS_NO')

RDB_HOST =  os.environ.get('RDB_HOST') or 'localhost'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
RDB_DB = 'bus_bot'

ERROR_MSG = '您輸入的公車名稱有誤'

def init_redis():
    db = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_NO)
    return db

@app.before_request
def before_request():
    try:
        g.rdb_conn = r.connect(host=RDB_HOST, port=RDB_PORT, db=RDB_DB)
        g.redis = init_redis()
    except RqlDriverError:
        abort(503, "No database connection could be established.")

@app.teardown_request
def teardown_request(exception):
    try:
        g.rdb_conn.close()
    except AttributeError:
        pass

def get_time_by_route(route_name):
    res = requests.post("http://pda.5284.com.tw/MQS/businfo2.jsp?routename=%s"%route_name)
    if res.status_code != 200 or '查無此路線資料' in res.text:
        app.logger.info(res.text)
        return {}
    soup = BeautifulSoup(res.text, 'html5lib')
    dirs = {'go':  [tr for tr in [tr for tr in soup.select('tr') if tr.get('class')] if 'ttego' in ''.join(tr['class'])],
            'back': [tr for tr in [tr for tr in soup.select('tr') if tr.get('class')] if 'back' in ''.join(tr['class'])]}
    data = {}
    _id = 0
    for k, _dir in dirs.items():
        d = []
        for tr in _dir:
            res = {}
            td = tr.select('td')
            res['id'] = _id
            res['stn'] = td[0].text
            res['status'] = td[1].text
            d.append(res)
            _id += 1
        data[k] = d
    return data

def send_msg(data):
    res = requests.post("https://graph.facebook.com/v2.6/me/messages",
                        params={'access_token': PAGE_ACCESS_TOKEN},
                        json=data)
    if res.status_code == 200:
        app.logger.info("Successfully send msg id %s to user %s"%(res.json().get('message_id'), res.json().get('recipient_id')))
    else:
        app.logger.info(res.text)

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
        "title":"Search",
        "payload":"<POSTBACK_PAYLOAD>",
        "image_url":"http://example.com/img/red.png"
      },
      {
        "content_type":"location"
      },
      {
        "content_type":"text",
        "title":"Something Else",
        "payload":"<POSTBACK_PAYLOAD>"
      }
    ]}
    }
    send_msg(data)

def render_res(data):
    res = ""
    for row in data:
        res = res + "%s: %s -> %s\n"%(row['id'],row['stn'],row['status'])
    return res
        

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    app.logger.debug('webhook incoming')
    if request.method == 'POST':
        data = request.get_json()

        if data.get('object') == 'page':
            app.logger.info('page object')
            for entry in data.get('entry'):
                page_id = entry.get('id')
                time_of_event = entry.get('time')

                for event in entry.get('messaging'):
                    if event.get('message'):
                        app.logger.debug(event)
                        msg = event.get('message').get('text')
                        data = get_time_by_route(msg)
                        if data:
                            for k in data:
                                res = render_res(data[k])
                                send_text_msg(event.get('sender').get('id'), res)
                            send_quick_reply(event.get('sender').get('id'), "請選擇想要推播的站牌id")
                        else:
                            send_text_msg(event.get('sender').get('id'), ERROR_MSG)
                          
                    else:
                        app.logger.debug('Webhook received unknow event: %s'%event)
        return 'ok'



    if request.method == 'GET':
        if (request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') ==  VERIFY_TOKEN):
            app.logger.debug('verifying token')
            return request.args.get('hub.challenge')
        else:
            app.logger.debug('bad token')
            return 'bad', 403
        
        
