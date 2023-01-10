from flask import Flask, request, render_template

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

@app.route('/')    
def return_view():
    now = datetime.datetime.now()
    day = str(now)[0:11]
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
    return render_template('index.html', today=today)


@app.route('/form', methods=['GET','POST'])    
def form_view():
    cursor.execute("""SELECT
		*
		FROM
		resident
		WHERE 
		going_to_alone = '一人外出可能' OR going_to_alone = '一人外出可能(一部)'
		""")
    residents = cursor.fetchall()
    
    
    if request.method == 'POST':
	    date = "'" + request.form['door_date'] + "'"
	    tim = "'" + request.form['door_time'] + "'"
	    if request.form['go_out'] == 'go':
		    if request.form['resident_id'].endswith('(一部)'):
			    cursor.execute("""INSERT INTO door_record(resident_id,exit_day,exit_time,nb)
			    VALUES (%s,%s,%s,%s)
			    """ % (request.form['resident_id'][:-10],date,tim,"'" + request.form['resident_id'][-10:] + "'")
			    )
		    elif request.form['resident_id'].endswith('可能'):
			    cursor.execute("""INSERT INTO door_record(resident_id,exit_day,exit_time,nb)
			    VALUES (%s,%s,%s,%s)
			    """ % (request.form['resident_id'][:-6],date,tim,"'" + request.form['resident_id'][-6:] + "'")
			    )
	    elif request.form['go_out'] == 'return':
		    if request.form['resident_id'].endswith('(一部)'):
			    cursor.execute("""SELECT * FROM door_record 
			    WHERE resident_id = %s and exit_day = %s and exit_time <= %s and entrance_day is Null
			    """ % (request.form['resident_id'][:-10],date,tim)
			    )
			    return_door = cursor.fetchone()
		    elif request.form['resident_id'].endswith('可能'):
			    cursor.execute("""SELECT * FROM door_record 
			    WHERE resident_id = %s and exit_day = %s and exit_time <= %s and entrance_day is Null
			    """ % (request.form['resident_id'][:-6],date,tim)
			    )
			    return_door = cursor.fetchone()
		    return_door = cursor.fetchone()
		    if return_door == None:
			    if request.form['resident_id'][-10:] == '一人外出可能(一部)':
				    cursor.execute("""INSERT INTO door_record(resident_id,entrance_day,entrance_time,nb)
				    VALUES (%s,%s,%s,%s)
				    """ % (request.form['resident_id'][:-10],date,tim,"'" + request.form['resident_id'][-10:] + "'")
				    )
			    elif request.form['resident_id'][-6:] == '一人外出可能':
				    cursor.execute("""INSERT INTO door_record(resident_id,entrance_day,entrance_time,nb)
				    VALUES (%s,%s,%s,%s)
				    """ % (int(request.form['resident_id'][:-6]),date,tim,"'" + request.form['resident_id'][-6:] + "'")
				    )
		    elif return_door != None:
			    if request.form['resident_id'][-10:] == '一人外出可能(一部)':
				    cursor.execute("""UPDATE door_record
				    SET entrance_day = %s, entrance_time = %s
				    WHERE exit_time <= %s AND resident_id = %s AND entrance_time is Null
				    """ % (date,tim,tim,request.form['resident_id'][:-10])
				    )
			    elif request.form['resident_id'][-6:] == '一人外出可能':
				    cursor.execute("""UPDATE door_record
				    SET entrance_day = %s, entrance_time = %s
				    WHERE exit_time <= %s AND resident_id = %s AND entrance_time is NUll
				    """ % (date,tim,tim,request.form['resident_id'][:-6])
				    )
    now = datetime.datetime.now()
    local_date = str(now)[0:11]
    local_tim = str(now)[11:19]
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
		    exit_day = %s OR entrance_day = %s ORDER BY exit_time DESC""" % ("'" + local_date + "'","'" + local_date + "'")
		    )
    today = cursor.fetchall()
    connection.commit()

    return render_template('form.html',residents=residents,today=today,local_date=local_date,local_tim=local_tim)
	  

if __name__ == "__main__":
    app.run(port = 8000, debug=True)
