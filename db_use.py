import os
from dotenv import load_dotenv
import subprocess
import datetime
import time
import MySQLdb
import nfc
import timeout_decorator
import requests
import nfc_reader

from transitions import Machine
import csv
import switch_app

load_dotenv()

start_time = datetime.datetime.now()
cr = nfc_reader.MyCardReader()
print(cr.card_type)


headers = {
    'Authorization': '42b8a2cbc94cd3a845eafffce207a3db789ff1bc1fa92d428a6c2e921bf3fa69428fb37b200195e58c4fbaa9dbf454fa',
    'Content-Type': 'application/json; charset=utf8',
    }


json_data = {
    'command': 'press',
    'parameter': 'default',
    'commandType': 'command',
    }
    
container_ip = os.environ['CONTAINER_ID']

#db接続
connection = MySQLdb.connect(
	host=container_ip,
	user=os.environ['DB_USER'],
	password=os.environ['DB_PASS'],
	db=os.environ['DB_NAME'],
	charset='utf8'
	)
cursor = connection.cursor()
cursor.execute('set global wait_timeout=86400')

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
	    self.page_value = cr.card_type
	    self.idm = ''
	    self.backup = []
	    self.check_record_time = ''
	    
	#日時、名前、詳細をslackに通知させる
	def notification(day,time,name,nb):
	    if cr.error_judgment == 'error':
		    print('network error')
		    return
	    url = "https://slack.com/api/chat.postMessage"
	    data = {
	    "token":os.environ['SLACK_TOKEN'],
	    "channel":"exitresident",
	    "text":"%s %s %s様: 外出%s" % (day,time,name,nb)
	    }
	    requests.post(url,data=data)
	    
	    
	#idを選択し、card_recordとresidentを合わせて一致する最新のデータを1つ呼び出す
	def select_card_record(self,day,cr):
	    cursor.execute("""SELECT
			     resident.id,
			     resident.name,
			     resident.going_to_alone,
			     card_record.datetime,
			     card_record.type,
			     card_record.idm
			     FROM 
			     resident 
			     INNER JOIN 
			     card_record 
			     ON
			     resident.card_id = card_record.idm
			     WHERE
			     resident.going_to_alone like '%s'
			     AND
			     card_record.datetime like '%s'
			     AND
			     card_record.type = '%s'
			     AND
			     card_record.idm = '%s'
			     ORDER BY card_record.datetime DESC
			     """ % ('一人外出可%',day + '%',self.page_value,cr.idm_data))
	    return cursor.fetchone()
	    
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
	    check_time = event.kwargs.get('check_time')
	    resident_id = event.kwargs.get('resident_id')
	    resident_nb = "'" + event.kwargs.get('resident_nb') + "'"
	    page_value = event.kwargs.get('page_value')
	    day = event.kwargs.get('day')
	    time = event.kwargs.get('time')
	    cursor.execute("SELECT * FROM door_record ORDER BY id DESC")
	    last_data = cursor.fetchone()
	    
	    print(str(last_data[2]) + ' ' + str(last_data[3]))
	    print(check_time)
	    if (str(last_data[2]) + ' ' + str(last_data[3])) != str(check_time):
		    print('log True')
		    door_state = ['exit_day','exit_time']
		    judgment = event.kwargs.get('judgment')
		    if page_value == 'return':
			    door_state = ['entrance_day','entrance_time']
			    day_record = SwitchDB.select_door_record("'" + day + "'",resident_id)
			    print(day_record)
			    if day_record is not None and day_record[3] is None:
				    print('return update')
				    cursor.execute(f"update door_record set entrance_day=%s,entrance_time=%s,nb=%s where exit_day = %s and exit_time <= %s and resident_id = %s order by exit_time desc limit 1",(day,time,resident_nb,day,time,resident_id))
				    connection.commit()
				    return
		    print('puls add')
		    cursor.execute(f"insert into door_record (resident_id,%s,%s,nb,error_judgment) values (%s,%s,%s,%s,'%s')" % (door_state[0],door_state[1],resident_id,"'" + day + "'","'" + time + "'",resident_nb,judgment))
		    connection.commit()
		    SwitchDB.check_record_time = check_time
	     
	def csv_migrate(self):
	     cursor.execute("""
		load data local
		infile'/home/pi/Desktop/exit_entrance_app/backup_file.csv'
		into table
		entrance_exit_management.card_record
		fields
		terminated by ','
	     """)
	     connection.commit()
	
	def del_card_data(self,date):
	    cursor.execute(f"DELETE FROM card_record WHERE type = '%s' AND datetime = '%s'" % (self.page_value, date))
	    connection.commit()
	    
	def mb(self,judgment):
	    
	    try:
		    cr.error_judgment = judgment
		    now = datetime.datetime.now()
		    day = str(now)[0:11]
		    print(cr.card_data())
		    self.idm = cr.idm_data
		    new_record = self.select_card_record(day,cr)
		    print(new_record)
		    if new_record is None:
			    print('pass')
			    return
		    
		    print('switch')
		    #response = requests.post('https://api.switch-bot.com/v1.0/devices/FA9364B2BC98/commands',headers=headers,json=json_data)
		    machine = Machine(model=SwitchDB, states=states, transitions=transitions, initial=self.page_value,
		    auto_transitions=False, ordered_transitions=False,send_event=True)
		    SwitchDB.trigger(self.page_value)
		    SwitchDB.trigger(self.state,check_time=new_record[3],resident_id=new_record[0],resident_nb=new_record[2],page_value=self.page_value,day=str(new_record[3])[0:11],time=str(new_record[3])[11:19],judgment=judgment)
		    SwitchDB.notification(str(new_record[3])[0:11],str(new_record[3])[11:19],new_record[0],new_record[2]) 
		    print('error: ' + cr.error_judgment)
		    connection.commit()
					    
	    except MySQLdb.OperationalError as e:
		    print(e)

switch_db = SwitchDB()
while True:
    try:
	    response = requests.get('http://192.168.0.31')#ネットワーク確認用
	    switch_db.mb('no')
    
    except requests.exceptions.ConnectionError as e:
	    print(e)
	    switch_db.mb('error')
    
