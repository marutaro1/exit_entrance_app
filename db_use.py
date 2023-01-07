from flask import Flask, request, render_template
import datetime
import MySQLdb
import nfc
import timeout_decorator
import requests
import nfc_reader
import schedule

import switch_app


app = Flask(__name__)

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
	user='root',
	password='password',
	db='entrance_exit_management',
	charset='utf8'
	)
cursor = connection.cursor()

def notification(day,time,name):
    url = "https://slack.com/api/chat.postMessage"
    data = {
    "token":"xoxb-4581004452003-4581017058403-PSlPznYuKQYOilCHEcHzXKZr",
    "channel":"D04H5H9H46Q",
    "text":"%s %s %s様: 外出" % (day,time,name)
    }
    requests.post(url,data=data)

page_value = input('Page go or return:')

def mb():
	try:
		cr = nfc_reader.MyCardReader()
		print(cr.card_data())

		cursor.execute("SELECT * FROM resident WHERE card_id like '%%%s%%'" % (str(cr.idm_data)[11:17]))
		resident = cursor.fetchone()
		print(resident)
		
		if resident[4] == '一人外出可能' or resident[4] == '一人外出可能(一部)':
			if page_value == 'go':
				with nfc.ContactlessFrontend('usb') as clf:
				    now = datetime.datetime.now()
				    day = str(now)[0:11]
				    tim = str(now)[11:19]
				    count = now - start_time
				    lag = datetime.timedelta(hours=0,minutes=0,seconds=40)
				    clf.connect(rdwr={'on-connect': cr.on_connect})
				    response = requests.post('https://api.switch-bot.com/v1.0/devices/FA9364B2BC98/commands',headers=headers,json=json_data)
				    if resident[4] == '一人外出可能(一部)':
				            notification(day,tim,resident[1])
				    cursor.execute(f"insert into door_record (resident_id,exit_day,exit_time,nb) values (%s,%s,%s,%s)",(resident[0],day,tim,resident[4]))
				    #保存
				    connection.commit()
				    
			if page_value == 'return':
				now = datetime.datetime.now()
				day = str(now)[0:11]
				tim = str(now)[11:19]
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
				    exit_day = %s and resident_id = %s ORDER BY exit_time DESC""" % ("'" + day + "'",resident[0])
				    )
				day_record = cursor.fetchone()
				
				if day_record is None or day_record[4] is not None:
					with nfc.ContactlessFrontend('usb') as clf:
						now = datetime.datetime.now()
						day = str(now)[0:11]
						tim = str(now)[11:19]
						count = now - start_time
						lag = datetime.timedelta(hours=0,minutes=0,seconds=40)
						clf.connect(rdwr={'on-connect': cr.on_connect})
						response = requests.post('https://api.switch-bot.com/v1.0/devices/FA9364B2BC98/commands',headers=headers,json=json_data)
						
						cursor.execute(f"insert into door_record (resident_id,entrance_day,entrance_time,nb) values (%s,%s,%s,%s)",(resident[0],day,tim,resident[4]))
						#保存
						connection.commit()
						
				elif day_record[4] is None:
					with nfc.ContactlessFrontend('usb') as clf:
						now = datetime.datetime.now()
						day = str(now)[0:11]
						tim = str(now)[11:19]
						clf.connect(rdwr={'on-connect': cr.on_connect})
						response = requests.post('https://api.switch-bot.com/v1.0/devices/FA9364B2BC98/commands',headers=headers,json=json_data)
						cursor.execute(f"update door_record set entrance_day=%s,entrance_time=%s,nb=%s where exit_day = %s and exit_time <= %s and resident_id = %s",(day,tim,resident[4],day,tim,resident[0]))
						#保存
						connection.commit()
					
						
				

			    
	except MySQLdb.OperationalError:
		#接続を閉じる
		connection.close()

schedule.every(5).seconds.do(mb)

while True:
	schedule.run_pending()


