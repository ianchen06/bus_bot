from datetime import datetime
import logging
import os
import json

from bs4 import BeautifulSoup
import requests
from flask import Flask, request, g, abort
import redis
import rethinkdb as r
from rethinkdb.errors import RqlRuntimeError, RqlDriverError

from fb_api import send_quick_reply, send_text_msg

app = Flask(__name__)
gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.DEBUG)
bus_ids = json.load(open('./utils/bus_ids.json'))

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
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
        db=REDIS_NO,
        charset="utf-8",
        decode_responses=True)
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

                    """
                    Message
                    """
                    if event.get('message'):
                        app.logger.debug(event)
                        user_id = event.get('sender').get('id')
                        
                        # Get context from Redis
                        context = g.redis.hgetall(user_id) or {"state":"begin"}
                        history = g.redis.zrange('%s_history'%user_id, -6, -1)
                        if context:
                            app.logger.debug('User context found, %s'%context)
                        msg = event.get('message').get('text') or evnt.get('message').get('quick_reply').get('payload')

                        if msg == '再次查詢':
                            msg = history[-1]

                        if msg == '取消':
                            context['state'] = 'begin'
                            g.redis.hmset(user_id, context)
                            g.redis.expire(user_id, 60)
                            send_text_msg(user_id, "請重新輸入")
                            return ''

                        #send_quick_reply(user_id, "請選擇想要推播的站牌id")

                        if context.get('state') == 'begin':
                            
                            """
                            Check if bus_id is valid
                            """
                            if msg not in bus_ids:
                                send_text_msg(user_id, ERROR_MSG)
                                return ''
                                
                            data = get_time_by_route(msg)
                            if data:
                                for k in data:
                                    res = render_res(data[k])
                                    send_text_msg(user_id, res)
                                send_quick_reply(user_id, "請選擇下列快速功能，或輸入其他公車路線")
                                context['bus_no'] = msg
                                g.redis.zadd('%s_history'%user_id, datetime.now().timestamp(), msg)
                                g.redis.zremrangebyrank('%s_history'%user_id, 0, -6)
                                g.redis.hmset(user_id, context)
                                g.redis.expire(user_id, 60)
                            else:
                                send_text_msg(user_id, "查詢系統出現錯誤，請稍後再試")
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
        
        
