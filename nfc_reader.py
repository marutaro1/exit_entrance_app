import binascii
import nfc
import os
import sys
import MySQLdb

import requests
from dotenv import load_dotenv
import datetime
import time

import timeout_decorator


load_dotenv()


#db接続
connection = MySQLdb.connect(
	host=os.environ['CONTAINER_ID'],
	user=os.environ['DB_USER'],
	password=os.environ['DB_PASS'],
	db=os.environ['DB_NAME'],
	charset='utf8'
	)
cursor = connection.cursor()


class MyCardReader(object):
    def __init__(self):
            self.idm_data = ''
            #self.card_type = input('go or return')
            self.card_type = 'go'
            self.now_format = ''
            self.last_time = datetime.datetime.now()
            self.error_judgment = ''
            self.motor_run = ''
            
    def on_connect(self, tag):
        now = datetime.datetime.now()
        elapsed_time = (now - self.last_time).total_seconds()
        print('test date: ' + str(elapsed_time))
        if elapsed_time < 5.0 and self.idm_data == str(binascii.hexlify(tag._nfcid))[2:-1]:
            # 5秒以内に同じカードを読み込んでいたら、何もしない
            print('test')
            self.motor_run = 'no'
            return
        else:
            print('else')
            self.now_format = str(now)[:-7]
            #タグ情報を全て表示
            #print(tag)
            #IDmのみ取得して表示
           
            idm = binascii.hexlify(tag._nfcid)
            self.idm_data = str(idm)[2:-1]
            self.add_record_database()
            
            self.last_time = datetime.datetime.now()
        
    def add_record_database(self):
        self.motor_run = 'ok'
        cursor.execute("INSERT INTO card_record(datetime,type,idm) values('%s','%s','%s')" % (self.now_format,self.card_type,self.idm_data))
        connection.commit()
        
    def read_id(self):
        try:
                print('start')
                clf = nfc.ContactlessFrontend('usb')
                try:
                    clf.connect(rdwr={'on-connect': self.on_connect})
                    
                finally:
                    clf.close()
                    print('end')
        except timeout_decorator.timeout_decorator.TimeoutError:
                clf.close()
                print('timeout')
                
    def card_data(self):
        #タッチ待ち
        self.read_id()
        return self.idm_data

#t = MyCardReader()
#t.read_id()
