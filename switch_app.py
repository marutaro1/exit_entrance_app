from flask import Flask, request, render_template
from flask_paginate import Pagination, get_page_parameter

import datetime

import nfc
import requests
import MySQLdb
import schedule
import nfc_reader


app = Flask(__name__)


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
	charset='utf8',
)
cursor = connection.cursor()

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
    connection.commit()
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

def serch_today_value(day,resident_id):
    select_value = 1
    if int(resident_id) == -1:
	    select_value = 1
    else:
	    select_value = 0
    print(resident_id)
    print(select_value)
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
    today = cursor.fetchall()
    return today

def post_door_record(identify_day,identify_time,resident_id,day,time,nb):
     cursor.execute("""
	 INSERT INTO door_record(resident_id,%s,%s,nb)
	 VALUES (%s,%s,%s,%s)
	 """ % (identify_day,identify_time,resident_id,day,time,nb)
     )
     connection.commit()

def update_door_record(day,time,resident_id):

    cursor.execute("""
	UPDATE door_record
	SET entrance_day = %s, entrance_time = %s
	WHERE exit_time <= %s AND resident_id = %s AND entrance_time is Null
	""" % (day,time,time,resident_id)
    )
    connection.commit()

def door_record_value(day):
    cursor.execute("SELECT * FROM door_record WHERE exit_day = %s ORDER BY exit_time DESC" % day)
    return cursor.fetchone()

def return_door_record(resident_id,day,time):
    cursor.execute("""
	SELECT * FROM door_record 
	WHERE resident_id = %s and exit_day = %s and exit_time <= %s and entrance_day is Null
	""" % (resident_id,day,time)
    )
    connection.commit()
    return cursor.fetchone()

@app.route('/', methods=['GET','POST'])
def return_view(post_day=''):
    now = datetime.datetime.now()
    day = str(now)[0:11]
    time = str(now)[11:19]
    today = serch_today_value(day,-1)
    if request.method == 'POST':
	    if request.form['day_value'] is None:
		    today = serch_today_value(day,request.form['resident_id'])
	    elif request.form['day_value'] is not None:
		    today = serch_today_value(request.form['day_value'],request.form['resident_id'])
    residents = residents_value()
    page = request.args.get(get_page_parameter(), type=int, default=1)
    limit = today[(page -1)*10:page*10]
    pagination = Pagination(page=page, total=len(today))
    connection.commit()
    return render_template('index.html', residents=residents, today=limit, pagination=pagination)

@app.route('/', methods=['POST'])
def post_select_day():
	if request.method == 'POST':
		if request.form['day_value']:
			door_record = door_record_value("'" + request.form['day_value'] + "'")
			return door_record

@app.route('/form', methods=['GET','POST'])    
def form_view():
    try:
	    now = datetime.datetime.now()
	    local_date = str(now)[0:11]
	    local_time = str(now)[11:19]
	    door_record = door_record_value("'" + local_date + "'")
	    today = serch_today_value(local_date,-1)
	    if request.method == 'POST':
		    if str(request.form['door_time']) != str(door_record[3]):
			    date = "'" + request.form['door_date'] + "'"
			    tim = "'" + request.form['door_time'] + "'"
			    if request.form['go_out'] == 'go':
				    if request.form['resident_id'].endswith('(一部)'):
					    post_door_record('exit_day','exit_time',request.form['resident_id'][:-10],date,tim,"'" + request.form['resident_id'][-10:] + "'")
				    elif request.form['resident_id'].endswith('可能'):
					    print('true')
					    post_door_record('exit_day','exit_time',request.form['resident_id'][:-6],date,tim,"'" + request.form['resident_id'][-6:] + "'")
			    elif request.form['go_out'] == 'return':
				    if request.form['resident_id'].endswith('(一部)'):
					    print('koko')
					    return_door = return_door_record(request.form['resident_id'][:-10],date,tim)
				    elif request.form['resident_id'].endswith('可能'):
					    print('koko')
					    return_door = return_door_record(request.form['resident_id'][:-6],date,tim)
				    if return_door == None:
					    if request.form['resident_id'][-10:] == '一人外出可能(一部)':
						    post_door_record('entrance_day','entrance_time',request.form['resident_id'][:-10],date,tim,"'" + request.form['resident_id'][-10:] + "'")
					    elif request.form['resident_id'][-6:] == '一人外出可能':
						    post_door_record('entrance_day','entrance_time',int(request.form['resident_id'][:-6]),date,tim,"'" + request.form['resident_id'][-6:] + "'")
				    elif return_door != None:
					    if request.form['resident_id'][-10:] == '一人外出可能(一部)':
						    update_door_record(date,tim,request.form['resident_id'][:-10])
					    elif request.form['resident_id'][-6:] == '一人外出可能':
						    update_door_record(date,tim,request.form['resident_id'][:-6])
			    if request.form['resident_id'][-10:] == '一人外出可能(一部)':
				    today = serch_today_value(local_date,-1)
			    elif request.form['resident_id'][-6:] == '一人外出可能':
				    today = serch_today_value(local_date,-1)
			    
	    residents = residents_value()
	    print(today)
	    page = request.args.get(get_page_parameter(), type=int, default=1)
	    limit = today[(page -1)*10:page*10]
	    pagination = Pagination(page=page, total=len(today))
	    connection.commit()
    
    except MySQLdb.OperationalError:
		    #接続を閉じる
		    connection.close()
    return render_template('form.html',residents=residents,today=limit,local_time=local_time,pagination=pagination)
	  

if __name__ == "__main__":
    app.run(port = 8000, debug=True)
