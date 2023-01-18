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

def today_value(day):
    try:
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
    except MySQLdb.OperationalError:
	    #接続を閉じる
	    connection.close()
    return today


def residents_value():
    try:
	    cursor.execute("""SELECT
			*
			FROM
			resident
			WHERE 
			going_to_alone = '一人外出可能' OR going_to_alone = '一人外出可能(一部)'
			""")
	    residents = cursor.fetchall()
	    connection.commit()
    except MySQLdb.OperationalError:
	    #接続を閉じる
	    connection.close()
    return residents
    
def post_door_record(identify_day,identify_time,resident_id,day,time,nb):
    try:
	     cursor.execute("""
		 INSERT INTO door_record(resident_id,%s,%s,nb)
		 VALUES (%s,%s,%s,%s)
		 """ % (identify_day,identify_time,resident_id,day,time,nb)
	     )
	     connection.commit()
    except MySQLdb.OperationalError:
	    #接続を閉じる
	    connection.close()

def update_door_record(day,time,resident_id):
    try:
	    cursor.execute("""
		UPDATE door_record
		SET entrance_day = %s, entrance_time = %s
		WHERE exit_time <= %s AND resident_id = %s AND entrance_time is Null
		""" % (day,time,time,resident_id)
	    )
	    connection.commit()
    except MySQLdb.OperationalError:
	    #接続を閉じる
	    connection.close()

def door_record_value(day):
    cursor.execute("SELECT * FROM door_record WHERE exit_day = %s ORDER BY exit_time DESC" % day)
    return cursor.fetchone()

def return_door_record(resident_id,day,time):
    try:
	    cursor.execute("""
		SELECT * FROM door_record 
		WHERE resident_id = %s and exit_day = %s and exit_time <= %s and entrance_day is Null
		""" % (resident_id,day,time)
	    )
	    connection.commit()
    except MySQLdb.OperationalError:
	    #接続を閉じる
	    connection.close()
    return cursor.fetchone()

@app.route('/')
def return_view():
    now = datetime.datetime.now()
    day = str(now)[0:11]
    today =  today_value(day)
    page = request.args.get(get_page_parameter(), type=int, default=1)
    limit = today[(page -1)*10:page*10]
    pagination = Pagination(page=page, total=len(today))
    return render_template('index.html', today=limit, pagination=pagination)


@app.route('/form', methods=['GET','POST'])    
def form_view():
    try:
	    now = datetime.datetime.now()
	    local_date = str(now)[0:11]
	    local_tim = str(now)[11:19]
	    door_record = door_record_value("'" + local_date + "'")
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
					    return_door = return_door_record(request.form['resident_id'][:-10],date,tim)
				    elif request.form['resident_id'].endswith('可能'):
					    return_door = return_door_record(request.form['resident_id'][:-6],date,tim)
				    print(return_door)
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
		    
	    today = today_value(local_date)
	    residents = residents_value()
	    connection.commit()
    
    except MySQLdb.OperationalError:
		    #接続を閉じる
		    connection.close()
    return render_template('form.html',residents=residents,today=today,local_date=local_date,local_tim=local_tim)
	  

if __name__ == "__main__":
    app.run(port = 8000, debug=True)
