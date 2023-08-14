import os
import sys
import subprocess
from flask import Flask, request, render_template, jsonify, redirect, url_for
from flask_paginate import Pagination, get_page_parameter
from dotenv import load_dotenv
import datetime
import time
import nfc
import requests
import MySQLdb
from flask_bcrypt import Bcrypt

import nfc_reader
from transitions import Machine

import psutil


app = Flask(__name__)
bcrypt = Bcrypt()

cr = nfc_reader.MyCardReader()
print(cr.card_type)

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
try:
        connection = MySQLdb.connect(
	host=os.environ['CONTAINER_ID'],
	user=os.environ['DB_USER'],
	password=os.environ['DB_PASS'],
	db=os.environ['DB_NAME'],
	charset='utf8'
	)
        cursor = connection.cursor()
        cursor.execute('set global wait_timeout=86400')
except Exception as e:
        error_ms = str(e)
        print('error: ',error_ms)
        time.sleep(5)
        subprocess.call(['sudo','systemctl','restart','start_app.service'])

states = ['go', 'return','go_record','return_record','post_go_record','post_return_record']

transitions = [
	{'trigger': 'go','source':['go', 'return'], 'dest': 'go_record'},#goの信号を受け取る
	{'trigger':'go_record','source':'go_record', 'dest':'post_go_record','after':'insert_door'},#受け取った信号を登録する
	{'trigger': 'post_go_record', 'source':'post_go_record', 'dest': 'go'},
	{'trigger': 'return','source': ['return', 'go'], 'dest':'return_record'},#returnの信号を受け取る
	{'trigger':'return_record','source':'return_record', 'dest':'post_return_record','after':'insert_door'},#returnの信号を受け取り、updateかpostかを識別し登録する
	{'trigger': 'post_return_record', 'source':'post_return_record', 'dest': 'return'}
	]


auth_array = []
post_data = []


class SwitchView(object):
	def __init__(self):
	    self.select_state = ''
	    self.return_post_method = ''
	    self.url_after_create = ''
	    self.url_after_update = 'no_url'
	    self.login_staff = 'no staff'
	    
	def all_staff_id(staff_id):
	    cursor.execute('SELECT id FROM staff')
	    all_staff = tuple(item[0] for item in (cursor.fetchall()))
	    print(all_staff)
	    if int(staff_id) in all_staff:
		    return True
	
	def serch_staff(staff_id):
	    cursor.execute('SELECT * FROM staff WHERE id = %s' % (staff_id))
	    serch_staff_data = cursor.fetchone()
	    print(auth_array)
	    return serch_staff_data
	
	@app.route('/sign_in', methods=['GET','POST'])
	def sign_in():
	    try:
		    now = datetime.datetime.now()
		    day = str(now)[0:11]
		    #SwitchView.login_staff = 'no staff'
		    home_url = 'no url'
		    if request.method == 'POST':
			    login_id = request.form['login_id']
			    password = request.form['password']
			    print(login_id)
			    print(password)
			    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
			    cursor.execute('''
				    SELECT * FROM staff
				    WHERE 
				    login_id = '%s'
			    ''' % (login_id))
			    auth_staff = cursor.fetchone()
			    if bcrypt.check_password_hash(auth_staff[3],password):
				    #SwitchView.login_staff = auth_staff
				    print('login')
				    home_url = request.host_url  + '/' + day + '/-1/all_record'
				    print(SwitchView.serch_staff(auth_staff[0]))
				    login_staff = SwitchView.serch_staff(auth_staff[0])
				    print('staff_id')
				    print(auth_staff[0])
				    auth_array.append(auth_staff[0])
				    post_data.append('更新')
				    print('sign in auth_array')
				    print(auth_array)
				    return redirect(url_for('return_view',staff_id=auth_staff[0],login_staff=login_staff,page_value=day,resident_id='-1',return_check='all_record'))
			    else:
				    print('no staff')
				    home_url = 'no url'
	    except MySQLdb.OperationalError as e:
		    print(e)
	    return render_template('sign_in.html')
			    
			    
	@app.route('/<int:staff_id>/sign_up', methods=['GET','POST'])
	def sign_up(staff_id):
	    try:
		    print(request.method == 'POST')
		    print(staff_id)
		    print(auth_array)
		    print(staff_id not in auth_array)
		    login_staff = SwitchView.serch_staff(staff_id)
		    if auth_array == [] and request.method == 'GET':
			    print('copy url')
			    print('staff id')
			    print(auth_array)
			    return redirect(url_for('sign_in'))
		    elif auth_array == []:
			    auth_array.append(staff_id)
		    elif staff_id not in auth_array:
			    return redirect(url_for('sign_in'))
		    if SwitchView.all_staff_id(staff_id) and request.method == 'POST':
			    name = request.form['name']
			    login_id = request.form['login_id']
			    password = request.form['password']
			    authority = request.form['authority']
			    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
			    print(bcrypt.check_password_hash(hashed_password, password))
			    
			    cursor.execute('''
				    INSERT INTO staff(name,login_id,password,authority)
				    VALUE('%s','%s','%s',%s)
			    ''' % (name,login_id,hashed_password,authority))
			    connection.commit()
	    except UnboundLocalError:
		    login_staff = SwitchView.serch_staff(staff_id)
	    except MySQLdb.OperationalError as e:
		    print(e)
	    return render_template('sign_up.html',staff_id=staff_id,login_staff=login_staff)
	
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
	    
	def all_residents():
	    cursor.execute("SELECT * FROM resident")
	    return cursor.fetchall()

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
	    print(resident_id)
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
			    nb,
			    error_judgment
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
			    nb,
			    error_judgment
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
			    nb,
			    error_judgment
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
	    
	
machine = Machine(model=SwitchView, states=states, transitions=transitions, initial='go',
				    auto_transitions=False, ordered_transitions=False,send_event=True)

	
@app.route('/<int:staff_id>/<string:page_value>/<string:resident_id>/<string:return_check>', methods=['GET','POST'])
def return_view(staff_id,page_value,resident_id,return_check):
    try:
	    if auth_array == [] and request.method == 'GET':
		    print('copy url')
		    print('staff id')
		    print(auth_array)
		    return redirect(url_for('sign_in'))
	    elif auth_array == []:
		    auth_array.append(staff_id)
	    elif int(staff_id) not in auth_array:
		    return redirect(url_for('sign_in'))
	    now = datetime.datetime.now()
	    day = str(now)[0:11]
	    time = str(now)[11:19]
	    today = ''
	    residents = ''
	    limit = ''
	    page = ''
	    pagination = ''
	    residents = SwitchView.residents_value()
	    print('door_record')
	    
	    door_record = SwitchView.door_record_value(page_value)
	    print(door_record)
	    print(page_value)
	    method_value = request.method
	    print(request.url)
	    if SwitchView.all_staff_id(staff_id) and request.method == 'POST':
		    print(request.form.get('door_time'))
		    today = SwitchView.serch_today_value(page_value,resident_id,return_check)
		    #if door_record is None and request.form.get('go_out') is not None or str(request.form.get('door_time')) != str(door_record[3]) and request.form.get('go_out') is not None:
		    if door_record is None and request.form.get('go_out') is not None:
		    # door_record が None であり、go_out が送信された場合の処理
			    machine.add_model(SwitchView, initial=request.form.get('go_out'))
			    SwitchView.trigger(request.form.get('go_out'))
			    SwitchView.trigger(SwitchView.state,data=request.form.get('go_out'),page=page_value,door_time=request.form['door_time'],resident_nb=request.form['select_resident_id'])
			    resident_nb = SwitchView.select_resident_nb_value(request.form['select_resident_id'])
			    
		    elif door_record is not None and request.form.get('door_time') is not None and str(request.form.get('door_time')) != str(door_record[3]) and request.form.get('go_out') is not None:
		    # door_record が None でなく、door_time が送信されていて、かつ door_time が door_record[3] と異なる場合の処理
		    # ...
			    print('state')
			    print(SwitchView.state)
			    machine.add_model(SwitchView, initial=request.form.get('go_out'))
			    print(SwitchView.state)
			    SwitchView.trigger(request.form.get('go_out'))
			    print(SwitchView.state)
			    SwitchView.trigger(SwitchView.state,data=request.form.get('go_out'),page=page_value,door_time=request.form['door_time'],resident_nb=request.form['select_resident_id'])
			    resident_nb = SwitchView.select_resident_nb_value(request.form['select_resident_id'])
			    print(SwitchView.state)
			    trigger_name = request.form.get('go_out')
			    print(trigger_name)
			    if trigger_name == 'go':
				    SwitchView.state = 'go'
			    elif trigger_name == 'return':
				    SwitchView.state = 'return'
			    
			    print(SwitchView.state)
			    
		    if resident_nb != []:
			    today = SwitchView.serch_today_value(page_value,-1,return_check)
	    if request.method == 'GET':
		    if page_value != 'favicon.ico':
			    day_value = page_value
			    today = SwitchView.serch_today_value(page_value,resident_id,return_check)
	    
	    login_staff = SwitchView.serch_staff(staff_id)
	    page = request.args.get(get_page_parameter(), type=int, default=1)
	    limit = today[(page -1)*10:page*10]
	    pagination = Pagination(page=page, total=len(today))
	    connection.commit()
	    
    except UnboundLocalError:
	    login_staff = SwitchView.serch_staff(staff_id)
    except MySQLdb.ProgrammingError:
	    print('ProgramingError')
	
    except MySQLdb.OperationalError as e:
	    print(e)
    return render_template('index.html', staff_id=staff_id,login_staff=login_staff,residents=residents, today=limit, day_value=day, local_time=time, pagination=pagination, page=page, page_value=page_value, resident_data=resident_id, return_check=return_check)

def post_resident(self,staff_id,name,number,room_number,going_to_alone,card_id):
    try:
	    if staff_id not in auth_array:
		    return redirect(url_for('sign_in'))
	    self.url_after_create = 'no url'
	    now = datetime.datetime.now()
	    day = str(now)[0:11]
	    cursor.execute("""
	    INSERT INTO 
	    resident
	    (name,number,number_people,going_to_alone,card_id) 
	    VALUES
	    ('%s',%s,%s,'%s','%s')
	    """ % (name,int(number),int(room_number),going_to_alone,card_id))
	    connection.commit()
	    self.url_after_create = request.host_url +'/' + str(staff_id) + '/' + day + '/-1/all_record'
    except ValueError:
	    print('ValueError')
	    self.url_after_create = request.host_url + '/' + str(staff_id) + '/create'
    print(self.url_after_create)

def post_update_resident(self,staff_id,resident_id,name,number,room_number,going_to_alone,card_id):
    try:
	    if auth_array == [] and request.method == 'GET':
		    print('copy url')
		    print('staff id')
		    print(auth_array)
		    return redirect(url_for('sign_in'))
	    elif auth_array == []:
		    auth_array.append(staff_id)
	    elif staff_id not in auth_array:
		    return redirect(url_for('sign_in'))
	    self.url_after_update = 'no url'
	    now = datetime.datetime.now()
	    day = str(now)[0:11]
	    cursor.execute("""
	    UPDATE resident
	    SET name = '%s',number = %s,number_people= %s,going_to_alone='%s',card_id='%s'
	    WHERE id = %s
	    """ % (name,int(number),int(room_number),going_to_alone,card_id,resident_id))
	    connection.commit()
	    self.url_after_update = request.host_url +'/' + str(staff_id) + '/' + day + '/-1/all_record'
    except ValueError:
	    print('ValueError')
	    self.url_after_update = request.host_url + '/' + str(staff_id) + '/update'
    print(self.url_after_update)
    
def kill_db_use():
	# 停止したいプロセス名を指定する
	process_name = "db_use.py"
	print('kill db_use')
	os.system(f'sudo pkill -f {process_name}')

#変更後
def restart_db_use():
	process_name = "db_use.py"
	process = subprocess.Popen(["python3", process_name])

@app.route('/<int:staff_id>/create', methods=['GET','POST'])
def new_resident_create(staff_id):
    try:
	    
	    if staff_id not in auth_array:
		    return redirect(url_for('sign_in'))
	    url_after='no url'
	    print(request.method)
	    if SwitchView.all_staff_id(staff_id) and request.method == 'POST' and request.form['new_name'] != '':
		    if request.form['create_message']:
			    print(request.form['create_message'])

			    post_data.append(request.form['create_message'])
		    kill_db_use()
		    print(cr.card_data())
		    print(cr.idm_data)
		    post_resident(SwitchView,staff_id,request.form['new_name'],request.form['new_number'],request.form['new_room_number'],request.form['new_going_to_alone'],cr.idm_data)
		    url_after=SwitchView.url_after_create
		    restart_db_use()
	    login_staff = SwitchView.serch_staff(staff_id)
    except UnboundLocalError:
	    login_staff = SwitchView.serch_staff(staff_id)	    
    except MySQLdb.OperationalError as e:
	    print(e)
    except ValueError:
	    print('new resident create')
    
    return render_template('create.html',staff_id=staff_id,login_staff=login_staff,url_after_create=url_after)
    
	
@app.route('/<int:staff_id>/update', methods=['GET','POST'])
def resident_update(staff_id):
    try:
	    if staff_id not in auth_array:
		    return redirect(url_for('sign_in'))
	    residents = SwitchView.all_residents()
	    login_staff = SwitchView.serch_staff(staff_id)
	    if SwitchView.all_staff_id(staff_id) and request.method == 'POST' and request.form['name'] != '':
		    print('print')
		    print(request.url)
		    print(request.method)
		    print(request.form['name'])
		    if request.form['update_message']:
			    print(request.form['update_message'])

			    post_data.append(request.form['update_message'])
		    print('update select')
		    if request.form['card_id'] == 'change':
			    kill_db_use()
			    print('no db_use')
			    cr.card_data()
			    card_id = cr.idm_data
			    post_update_resident(SwitchView,staff_id,request.form['select_resident_id'],request.form['name'],request.form['number'],request.form['room_number'],request.form['going_to_alone'],cr.idm_data)
			    url_after = SwitchView.url_after_update
			    restart_db_use()
		    elif request.form['card_id'] != 'change':
			    print(request.form['select_resident_id'])
			    print(request.form['name'])
			    post_update_resident(SwitchView,staff_id,request.form['select_resident_id'],request.form['name'],request.form['number'],request.form['room_number'],request.form['going_to_alone'],request.form['card_id'])
			    url_after = SwitchView.url_after_update
			    print(url_after)
		    print(url_after)
		    return render_template('update.html',staff_id=staff_id,login_staff=login_staff,residents=residents, url_after_update=url_after)
	    else:
		    url_after = 'no url'
	    
    except UnboundLocalError:
	    login_staff = SwitchView.serch_staff(staff_id)
    except MySQLdb.OperationalError as e:
	    print(e)
    except ValueError:
	    print('update resident')
    
    return render_template('update.html',staff_id=staff_id,login_staff=login_staff,residents=residents,url_after_update=url_after)


@app.route('/<int:staff_id>/sign_out', methods=['GET','POST'])
def sign_out(staff_id):
    try:
	    user_agent = request.headers.get('User-Agent')
	    print(user_agent)
	    print(request.method == 'POST')
	    if request.method == 'POST':
		    print('POST')
		    data = request.get_json()
		    post_data.append(data) #ページから送られてくる信号を格納する配列
		    
		    print('post_data')
		    print(post_data)
		    print('auth_array')
		    print(auth_array)
		    
		    
		    if 'ログアウト' in post_data:
			    auth_array.remove(staff_id)
			    post_data.clear()
		    elif auth_array.count(staff_id) >= 2:
			     auth_array.remove(staff_id)
		   
			    
		    print(post_data)
		    print('auth_array')
		    print(auth_array)
		    return 'page change'
	    print('auth_array last')
	    auth_array.remove(int(staff_id))
	    print(auth_array)
    except  ValueError:
	    return redirect(url_for('sign_in'))
    return redirect(url_for('sign_in'))
	
	
if __name__ == "__main__":
    app.run(port = 8000, debug=True)
