import os
from flask import Flask, request, render_template
from dotenv import load_dotenv
import datetime
import MySQLdb
import nfc
import timeout_decorator
import requests
import nfc_reader
import schedule

import switch_app


app = Flask(__name__)

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

class SwitchDB(object):
	def __init__(self):
		self.page_value = input('Page go or return:')
	

	def notification(day,time,name,nb):
	    print('slak')
	    url = "https://slack.com/api/chat.postMessage"
	    data = {
	    "token":os.environ['SLACK_TOKEN'],
	    "channel":"exitresident",
	    "text":"%s %s %s様: 外出%s" % (day,time,name,nb)
	    }
	    requests.post(url,data=data)
	    
	def switch_response(cr,clf,door_mode,resident):
	    now = datetime.datetime.now()
	    day = str(now)[0:11]
	    time = str(now)[11:19]
	    clf.connect(rdwr={'on-connect': cr.on_connect})
	    response = requests.post('https://api.switch-bot.com/v1.0/devices/FA9364B2BC98/commands',headers=headers,json=json_data)
	    if door_mode == 'go':
		    cursor.execute(f"insert into door_record (resident_id,exit_day,exit_time,nb) values (%s,%s,%s,%s)",(resident[0],day,time,resident[4]))
	    elif door_mode == 'new_return':
		    cursor.execute(f"insert into door_record (resident_id,entrance_day,entrance_time,nb) values (%s,%s,%s,%s)",(resident[0],day,time,resident[4]))
	    elif door_mode == 'return':
		    cursor.execute(f"update door_record set entrance_day=%s,entrance_time=%s,nb=%s where exit_day = %s and exit_time <= %s and resident_id = %s order by exit_time desc limit 1",(day,time,resident[4],day,time,resident[0]))
		
	def serect_door_record(day,resident_id):
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

	def mb(self):
		try:
			cr = nfc_reader.MyCardReader()
			print(cr.card_data())
			now = datetime.datetime.now()
			day = str(now)[0:11]
			tim = str(now)[11:19]
			cursor.execute("SELECT * FROM resident WHERE card_id like '%%%s%%'" % (str(cr.idm_data)[11:17]))
			resident = cursor.fetchone()
			print(resident)
			if resident[4] == '一人外出可能' or resident[4] == '一人外出可能(一部)':
				if self.page_value == 'go':
					with nfc.ContactlessFrontend('usb') as clf:
					    SwitchDB.switch_response(cr,clf,'go',resident)
					    if resident[4] == '一人外出可能(一部)':
						    SwitchDB.notification(day,tim,resident[1],'(テラスまで)')
					    elif resident[4] == '一人外出可能':
						    SwitchDB.notification(day,tim,resident[1],'')
					    connection.commit()
					    
				if self.page_value == 'return':
					day_record = SwitchDB.serect_door_record("'" + day + "'",resident[0])
					if day_record is None or day_record[4] is not None:
						with nfc.ContactlessFrontend('usb') as clf:
							SwitchDB.switch_response(cr,clf,'new_return',resident)
							#保存
							connection.commit()
							
					elif day_record[4] is None:
						with nfc.ContactlessFrontend('usb') as clf:
							SwitchDB.switch_response(cr,clf,'return',resident)
							#保存
							connection.commit()
						
							
					

				    
		except MySQLdb.OperationalError:
			#接続を閉じる
			connection.close()
switch_db = SwitchDB()
schedule.every(3).seconds.do(switch_db.mb)

while True:
	schedule.run_pending()


