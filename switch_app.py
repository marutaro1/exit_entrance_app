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

class SwitchView(object):

	def select_day(num=0):
	    now = datetime.datetime.now()
	    day_value = now + datetime.timedelta(days=num)
	    return str(day_value)[0:11]
	    
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

	def serch_today_value(day,resident_id,return_check):
	    select_value = 1
	    if int(resident_id) == -1:
		    select_value = 1
	    elif int(resident_id) != -1:
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

	def post_door_record(identify_day,identify_time,resident_id,day,time,nb):
	     cursor.execute("""
		 INSERT INTO door_record(resident_id,%s,%s,nb)
		 VALUES (%s,%s,%s,%s)
		 """ % (identify_day,identify_time,resident_id,"'" + day + "'","'" + time + "'","'" + nb + "'")
	     )

	def update_door_record(day,time,resident_id):

	    cursor.execute("""
		UPDATE door_record
		SET entrance_day = %s, entrance_time = %s
		WHERE exit_time <= %s AND resident_id = %s AND entrance_time is Null ORDER BY id DESC LIMIT 1
		""" % ("'" + day + "'","'" + time + "'","'" + time + "'",resident_id)
	    )
	    connection.commit()

	def door_record_value(day):
	    cursor.execute("SELECT * FROM door_record WHERE exit_day = %s ORDER BY exit_time DESC" % ("'" + day + "'"))
	    door_record = cursor.fetchone()
	    return door_record

	def return_door_record(resident_id,day,time):
	    cursor.execute("""
		SELECT * FROM door_record 
		WHERE resident_id = %s and exit_day = %s and exit_time <= %s and entrance_day is Null
		""" % (resident_id,"'" + day + "'","'" + time + "'")
	    )
	    door_record = cursor.fetchone()
	    return door_record

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
		    print(door_record)
		    if request.method == 'POST':
			    today = SwitchView.serch_today_value(page_value,resident_id,return_check)
			    if door_record is None:
				    door_record = ['','','','','','','']
			    if str(request.form['door_time']) != str(door_record[3]):
				    if request.form['go_out'] == 'go':
					    if request.form['select_resident_id'].endswith('(一部)'):
						    SwitchView.post_door_record('exit_day','exit_time',request.form['select_resident_id'][:-10],page_value,request.form['door_time'],request.form['select_resident_id'][-10:])
					    elif request.form['select_resident_id'].endswith('可能'):
						    print(request.form['select_resident_id'][-6:])
						    SwitchView.post_door_record('exit_day','exit_time',request.form['select_resident_id'][:-6],page_value,request.form['door_time'],request.form['select_resident_id'][-6:])
				    elif request.form['go_out'] == 'return':
					    if request.form['select_resident_id'].endswith('(一部)'):
						    return_door = SwitchView.return_door_record(request.form['select_resident_id'][:-10],page_value,request.form['door_time'])
					    elif request.form['select_resident_id'].endswith('可能'):
						    return_door = SwitchView.return_door_record(request.form['select_resident_id'][:-6],page_value,request.form['door_time'])
					    if return_door == None:
						    if request.form['select_resident_id'][-10:] == '一人外出可能(一部)':
							    SwitchView.post_door_record('entrance_day','entrance_time',request.form['select_resident_id'][:-10],page_value,request.form['door_time'],request.form['select_resident_id'][-10:])
						    elif request.form['select_resident_id'][-6:] == '一人外出可能':
							    SwitchView.post_door_record('entrance_day','entrance_time',int(request.form['select_resident_id'][:-6]),page_value,request.form['door_time'],request.form['select_resident_id'][-6:])
					    elif return_door != None:
						    if request.form['select_resident_id'][-10:] == '一人外出可能(一部)':
							    SwitchView.update_door_record(page_value,request.form['door_time'],request.form['select_resident_id'][:-10])
						    elif request.form['select_resident_id'][-6:] == '一人外出可能':
							    SwitchView.update_door_record(page_value,request.form['door_time'],request.form['select_resident_id'][:-6])
				    
			    if request.form['select_resident_id'][-10:] == '一人外出可能(一部)':
				    today = SwitchView.serch_today_value(page_value,-1,return_check)
			    elif request.form['select_resident_id'][-6:] == '一人外出可能':
				    today = SwitchView.serch_today_value(page_value,-1,return_check)
		    if request.method == 'GET':
			    if page_value != 'favicon.ico':
				    day_value = page_value
				    today = SwitchView.serch_today_value(page_value,resident_id,return_check)
				    
		    page = request.args.get(get_page_parameter(), type=int, default=1)
		    limit = today[(page -1)*10:page*10]
		    pagination = Pagination(page=page, total=len(today))
		    if page == '' or limit == '' or pagination == '' or residents == '':
			    residents = SwitchView.residents_value()
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
