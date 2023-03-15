import binascii
import nfc
import os
import MySQLdb

import requests
from dotenv import load_dotenv
import datetime
import time

import timeout_decorator
load_dotenv()

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

class MyCardReader(object):
    def __init__(self):
            self.idm_data = ''
            #self.card_type = input('go or return')
            self.card_type = 'go'
            self.now_format = ''
            
    def on_connect(self, tag):
        now = datetime.datetime.now()
        self.now_format = str(now)[:-7]
        #タグ情報を全て表示
        #print(tag)
        #IDmのみ取得して表示
        self.idm = binascii.hexlify(tag._nfcid)
        card_idm = str(self.idm)[2:-1]
        self.add_record_database(card_idm)
        
        self.idm_data = self.idm
        
    def add_record_database(self,card_idm):
        cursor.execute("INSERT INTO card_record(datetime,type,idm) values(%s,%s,%s)" % ("'" + self.now_format + "'","'" + self.card_type + "'","'" + card_idm + "'"))
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
