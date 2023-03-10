import os
from flask import Flask, request, render_template
from flask_paginate import Pagination, get_page_parameter
from dotenv import load_dotenv
import datetime

import nfc
import requests
import MySQLdb
import schedule
import nfc_reader
from transitions import Machine


app = Flask(__name__)

load_dotenv()

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
	charset='utf8',
)
cursor = connection.cursor()

states = ['go', 'return','go_record','return_record','post_go_record','post_return_record']
transitions = [
	{'trigger':'go','source':'go', 'dest':'go_record'},#goの信号を受け取る
	{'trigger':'go_record','source':'go_record', 'dest':'post_go_record','after':'insert_door'},#受け取った信号を登録する
	{'trigger':'return','source':'return', 'dest':'return_record'},#returnの信号を受け取る
	{'trigger':'return_record','source':'return_record', 'dest':'post_return_record','after':'insert_door'},#returnの信号を受け取り、updateかpostかを識別し登録する
	]


class SwitchView(object):
	def __init__(self):
	    self.select_state = ''
	    self.return_post_method = ''
	
	#residentの文字列をidとgoing_to_aloneに分ける
	def select_resident_nb_value(resident):
	    print(resident[:-10])
	    resident_value = []
	    while resident_value == []:
		    
		    if resident.endswith('出可能'):
			    resident_value = [resident[:-6],resident[-6:]]
		    elif resident.endswith(')'):
			    resident_value = [resident[:-10],resident[-10:]]
		    if resident_value == []:
			    print(resident)
			    print(resident_value)
			    continue
	    return resident_value

	#residentから一人外出可能な人だけを取り出す
	def residents_value():
	    cursor.execute("""SELECT
			*
			FROM
			resident
			WHERE 
			going_to_alone = '一人外出可能' OR going_to_alone = '一人外出可能(一部)'
			""")
	    residents = cursor.fetchall()
	    return residents
	
	#日付を選択し、その日の記録を取り出す
	def today_value(day):
	    cursor.execute("""SELECT
			    resident.name,
			    exit_day,
			    exit_time,
			    entrance_day,
			    entrance_time,
			    nb
			    FROM
			    door_record
			    INNER JOIN
			    resident
			    ON
			    door_record.resident_id = resident.id
			    WHERE 
			    exit_day = %s OR entrance_day = %s ORDER BY exit_time DESC""" % ("'" + day + "'","'" + day + "'")
			    )
	    today = cursor.fetchall()
	    
	    return today
	
	#すべてのdoor_recordか、entrance_dayにデータが入っている物のみか、entrance_dayがNullの物かを選択し、呼び出す
	def serch_today_value(day,resident_id,return_check):
	    select_value = 1
	    if int(resident_id) != -1:
		    select_value = 0
	    if return_check == 'all_record':
		    cursor.execute("""SELECT
			    resident.name,
			    exit_day,
			    exit_time,
			    entrance_day,
			    entrance_time,
			    nb
			    FROM
			    door_record
			    INNER JOIN
			    resident
			    ON
			    door_record.resident_id = resident.id
			    WHERE
			    exit_day = %s
			    AND
			    CASE 
			    WHEN resident_id = %s THEN TRUE ELSE %s END
			    OR
			    exit_day is Null
			    AND
			    entrance_day = %s
			    AND
			    CASE 
			    WHEN resident_id = %s THEN TRUE ELSE %s END
			    ORDER BY exit_time DESC
			    """
			    % ("'" + day + "'",resident_id,select_value,
			    "'" + day + "'",resident_id,select_value)
			    )
			    
	    elif return_check == 'no_return':
		    cursor.execute("""SELECT
			    resident.name,
			    exit_day,
			    exit_time,
			    entrance_day,
			    entrance_time,
			    nb
			    FROM
			    door_record
			    INNER JOIN
			    resident
			    ON
			    door_record.resident_id = resident.id
			    WHERE
			    exit_day = %s
			    AND
			    entrance_day is Null
			    AND
			    CASE 
			    WHEN resident_id = %s THEN TRUE ELSE %s END
			    ORDER BY exit_time DESC
			    """
			    % ("'" + day + "'",resident_id,select_value)
			    )
	    elif return_check == 'return':
		    cursor.execute("""SELECT
			    resident.name,
			    exit_day,
			    exit_time,
			    entrance_day,
			    entrance_time,
			    nb
			    FROM
			    door_record
			    INNER JOIN
			    resident
			    ON
			    door_record.resident_id = resident.id
			    WHERE
			    entrance_day = %s
			    AND
			    CASE 
			    WHEN resident_id = %s THEN TRUE ELSE %s END
			    ORDER BY exit_time DESC
			    """
			    % ("'" + day + "'",resident_id,select_value)
			    )
	    today = cursor.fetchall()
	    return today

	#exitかentranceか選択し、新たにdoor_recordを登録する
	def post_door_record(identify_day,identify_time,resident_id,day,time,nb):
	     cursor.execute("""
		 INSERT INTO door_record(resident_id,%s,%s,nb)
		 VALUES (%s,%s,%s,%s)
		 """ % (identify_day,identify_time,resident_id,"'" + day + "'","'" + time + "'","'" + nb + "'")
	     )

	#resident_idを選択し、entranceがNullの状態の最新のdoor_recordに、選択した日時をentranceのday,timeとして登録
	def update_door_record(day,time,resident_id):
	    cursor.execute("""
		UPDATE door_record
		SET entrance_day = %s, entrance_time = %s
		WHERE exit_time <= %s AND resident_id = %s AND entrance_time is Null ORDER BY id DESC LIMIT 1
		""" % ("'" + day + "'","'" + time + "'","'" + time + "'",resident_id)
	    )
	    connection.commit()
	
	#選択した日付と一致するexit_dayを持つdoor_recordを呼び出す
	def door_record_value(day):
	    cursor.execute("SELECT * FROM door_record WHERE exit_day = %s ORDER BY exit_time DESC" % ("'" + day + "'"))
	    door_record = cursor.fetchone()
	    return door_record

	#resident_idとexitかentranceの日付に一致したdoor_recordを呼び出す
	def return_door_record(resident_id,day,time):
	    cursor.execute("""
		SELECT * FROM door_record 
		WHERE resident_id = %s and exit_day = %s and exit_time <= %s and entrance_day is Null
		""" % (resident_id,"'" + day + "'","'" + time + "'")
	    )
	    door_record = cursor.fetchone()
	    return door_record
	
	#goかreturnかの信号を受け取り、door_recordを登録する
	def insert_door(event):
	    request = event.kwargs.get('data')
	    page_value = event.kwargs.get('page')
	    print(event.kwargs.get('resident_nb'))
	    print(SwitchView.select_resident_nb_value(event.kwargs.get('resident_nb')))
	    resident_nb = SwitchView.select_resident_nb_value(event.kwargs.get('resident_nb'))
	    door_time = event.kwargs.get('door_time')
	    print(resident_nb)
	    day = 'exit_day'
	    time = 'exit_time'
	    return_value = ''
	    if request == 'return':
		    day = 'entrance_day'
		    time = 'entrance_time'
		    return_value = SwitchView.return_door_record(resident_nb[0],page_value,door_time)
		    if return_value != None:
			    SwitchView.update_door_record(page_value,door_time,resident_nb[0])
		    elif return_value == None:
			    SwitchView.post_door_record(day,time,resident_nb[0],page_value,door_time,resident_nb[1])
		    return
	    print(resident_nb)
	    SwitchView.post_door_record(day,time,resident_nb[0],page_value,door_time,resident_nb[1])
	    
	
	@app.route('/<string:page_value>/<string:resident_id>/<string:return_check>', methods=['GET','POST'])
	def return_view(page_value,resident_id,return_check):
	    try:
		    now = datetime.datetime.now()
		    day = str(now)[0:11]
		    time = str(now)[11:19]
		    today = ''
		    residents = ''
		    limit = ''
		    page = ''
		    pagination = ''
		    residents = SwitchView.residents_value()
		    door_record = SwitchView.door_record_value(page_value)
		    method_value = request.method
		    if request.method == 'POST':
			    today = SwitchView.serch_today_value(page_value,resident_id,return_check)
			    if door_record is None or str(request.form['door_time']) != str(door_record[3]):
				    SwitchView.select_state = request.form.get('go_out')
				    machine = Machine(model=SwitchView, states=states, transitions=transitions, initial=SwitchView.select_state,
				    auto_transitions=False, ordered_transitions=False,send_event=True)
				    print(request.form['select_resident_id'])
				    SwitchView.trigger(SwitchView.select_state)
				    SwitchView.trigger(SwitchView.state,data=SwitchView.select_state,page=page_value,door_time=request.form['door_time'],resident_nb=request.form['select_resident_id'])
			    resident_nb = SwitchView.select_resident_nb_value(request.form['select_resident_id'])
			    if resident_nb != []:
				    today = SwitchView.serch_today_value(page_value,-1,return_check)
		    if request.method == 'GET':
			    if page_value != 'favicon.ico':
				    day_value = page_value
				    today = SwitchView.serch_today_value(page_value,resident_id,return_check)
		    
		    page = request.args.get(get_page_parameter(), type=int, default=1)
		    limit = today[(page -1)*10:page*10]
		    pagination = Pagination(page=page, total=len(today))
		    connection.commit()
		    
	    except MySQLdb.ProgrammingError:
		    print('ProgramingError')
		
	    except MySQLdb.OperationalError:
		    #接続を閉じる
		    connection.close()
	    return render_template('index.html', residents=residents, today=limit, day_value=day, local_time=time, pagination=pagination, page=page, page_value=page_value, resident_data=resident_id, return_check=return_check)

if __name__ == "__main__":
    app.run(port = 8000, debug=True)
