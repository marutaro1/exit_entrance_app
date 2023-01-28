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
    connection.commit()
    
    return today

def serch_today_value(day,resident_id):
    print(day)
    print('test_day')
    print(resident_id)
    select_value = 1
    if int(resident_id) == -1:
	    select_value = 1
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
    else:
	    select_value = 0
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
    connection.commit()
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

@app.route('/<string:page_value>', methods=['GET','POST'])
def return_view(page_value):
    try:
	    print(page_value)
	    now = datetime.datetime.now()
	    day = str(now)[0:11]
	    time = str(now)[11:19]
	    today = ''
	    day_value = day
	    residents = ''
	    limit = ''
	    page = ''
	    pagination = ''
	    residents = residents_value()
	    print('error1')
	    if request.method == 'POST':
		    print('erro2')
		    if request.json is not None:
			    day_value = request.json['day_value']
			    today = serch_today_value(page_value,request.json['resident_id'])
		    elif request.form.get('day_value') is None:
			    resident_id = today = request.form.get('resident_id')
			    if request.form.get('resident_id') is None:
				    resident_id = -1
			    day_value = day
			    today = serch_today_value(day,resident_id)
		    elif request.form.get('day_value') is not None:
			    day_value = request.form['day_value']
			    today = serch_today_value(page_value,request.form['resident_id'])
	    if request.method == 'GET':
		    print('error3')
		    if page_value != 'favicon.ico':
			    print('error4')
			    day_value = page_value
			    today = serch_today_value(page_value,'-1')
			    
	    page = request.args.get(get_page_parameter(), type=int, default=1)
	    limit = today[(page -1)*10:page*10]
	    pagination = Pagination(page=page, total=len(today))
	    if page == '' or limit == '' or pagination == '' or residents == '':
		    print('koko')
		    residents = residents_value()
		    page = request.args.get(get_page_parameter(), type=int, default=1)
		    limit = today[(page -1)*10:page*10]
		    pagination = Pagination(page=page, total=len(today))
	    connection.commit()
    except MySQLdb.ProgrammingError:
	    print('ProgramingError')
    except MySQLdb.OperationalError:
	    #接続を閉じる
	    connection.close()
    return render_template('index.html', residents=residents, today=limit, day_value=day_value, pagination=pagination, page=page, page_value=page_value)

@app.route('/', methods=['POST'])
def post_select_day():
	door_record = ''
	if request.method == 'POST':
		if request.json is not None:
			door_record = door_record_value("'" + request.json['day_value'] + "'")
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
	    print(door_record)
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
	    page = request.args.get(get_page_parameter(), type=int, default=1)
	    limit = today[(page -1)*10:page*10]
	    pagination = Pagination(page=page, total=len(today))
	    connection.commit()
    
    except MySQLdb.OperationalError:
		    #接続を閉じる
		    connection.close()
    return render_template('form.html',residents=residents,today=limit,local_time=local_time,page=page,pagination=pagination)
	  

if __name__ == "__main__":
    app.run(port = 8000, debug=True)
