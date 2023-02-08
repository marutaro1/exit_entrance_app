import os
from dotenv import load_dotenv
import datetime
import MySQLdb
import nfc
import timeout_decorator
import requests
import nfc_reader
import schedule
from transitions import Machine

import switch_app

load_dotenv()

start_time = datetime.datetime.now()
headers = {
    'Authorization': '42b8a2cbc94cd3a845eafffce207a3db789ff1bc1fa92d428a6c2e921bf3fa69428fb37b200195e58c4fbaa9dbf454fa',
    'Content-Type': 'application/json; charset=utf8',
    }

json_data = {
    'command': 'press',
    'parameter': 'default',
    'commandType': 'command',
    }

#db接続
connection = MySQLdb.connect(
	host='localhost',
	user=os.environ['DB_USER'],
	password=os.environ['DB_PASS'],
	db=os.environ['DB_NAME'],
	charset='utf8'
	)
cursor = connection.cursor()

states = ['go', 'return','go_record','return_record','post_go_record','post_return_record']
transitions = [
	{'trigger':'go','source':'go', 'dest':'go_record'},#goの信号を受け取る
	{'trigger':'go_record','source':'go_record','dest':'post_go_record','after':'add_door_record'},#受け取った信号を登録する
	{'trigger':'return','source':'return','dest':'return_record'},#returnの信号を受け取る
	{'trigger':'return_record','source':'return_record','dest':'post_return_record','after':'add_door_record'},#returnの信号を受け取り、updateかpostかを識別し登録する
]

class SwitchDB(object):
	def __init__(self):
	    #self.page_value = input('go or return')
	    self.page_value = 'go'
	    
	#日時、名前、詳細をslackに通知させる
	def notification(day,time,name,nb):
	    url = "https://slack.com/api/chat.postMessage"
	    data = {
	    "token":os.environ['SLACK_TOKEN'],
	    "channel":"exitresident",
	    "text":"%s %s %s様: 外出%s" % (day,time,name,nb)
	    }
	    requests.post(url,data=data)
	
	#日付とresident_idが一致するdoor_recordの最新のデータを一つ呼び出す
	def select_door_record(day,resident_id):
	    cursor.execute("""SELECT
		    resident_id,
		    exit_day,
		    exit_time,
		    entrance_day,
		    entrance_time,
		    nb
		    FROM
		    door_record 
		    WHERE 
		    exit_day = %s and resident_id = %s ORDER BY exit_time DESC
		    """ % (day,resident_id)
		    )
	    return cursor.fetchone()
	
	##goかreturnかの信号を受け取り、door_recordを登録する
	def add_door_record(event):
	    resident_id = event.kwargs.get('resident_id')
	    resident_nb = "'" + event.kwargs.get('resident_nb') + "'"
	    page_value = event.kwargs.get('page_value')
	    day = event.kwargs.get('day')
	    time = event.kwargs.get('time')
	    door_state = ['exit_day','exit_time']
	    if page_value == 'return':
		    door_state = ['entrance_day','entrance_time']
		    day_record = SwitchDB.select_door_record("'" + day + "'",resident_id)
		    print(day_record)
		    if day_record[3] is None:
			    cursor.execute(f"update door_record set entrance_day=%s,entrance_time=%s,nb=%s where exit_day = %s and exit_time <= %s and resident_id = %s order by exit_time desc limit 1",(day,time,resident_nb,day,time,resident_id))
			    connection.commit()
			    return
	    cursor.execute(f"insert into door_record (resident_id,%s,%s,nb) values (%s,%s,%s,%s)" % (door_state[0],door_state[1],resident_id,"'" + day + "'","'" + time + "'",resident_nb))
	    connection.commit()
	     
	def mb(self):
	    try:
		    cr = nfc_reader.MyCardReader()
		    print(cr.card_data())
		    now = datetime.datetime.now()
		    day = str(now)[0:11]
		    time = str(now)[11:19]
		    cursor.execute("SELECT * FROM resident WHERE card_id like '%%%s%%'" % (str(cr.idm_data)[11:17]))
		    resident = cursor.fetchone()
		    machine = Machine(model=SwitchDB, states=states, transitions=transitions, initial=self.page_value,
		    auto_transitions=False, ordered_transitions=False,send_event=True)
		    if resident[4] == '一人外出可能' or resident[4] == '一人外出可能(一部)':
			    with nfc.ContactlessFrontend('usb') as clf:
				    SwitchDB.trigger(self.page_value)
				    SwitchDB.trigger(self.state,resident_id=resident[0],resident_nb=resident[4],page_value=self.page_value,day=day,time=time)
				    SwitchDB.notification(day,time,resident[1],resident[4]) 
				    connection.commit()
					    
	    except MySQLdb.OperationalError:
		    #接続を閉じる
		    connection.close()

switch_db = SwitchDB()
schedule.every(3).seconds.do(switch_db.mb)

while True:
	schedule.run_pending()

