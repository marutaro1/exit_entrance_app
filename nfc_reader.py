import binascii
import nfc
import os
import MySQLdb
from dotenv import load_dotenv
import datetime

import timeout_decorator
load_dotenv()
#db接続
connection = MySQLdb.connect(
	host='localhost',
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
            
    def on_connect(self, tag):
        now = datetime.datetime.now()
        print(now)
        now_format = str(now)[:-7]
        #タグ情報を全て表示
        #print(tag)
        #IDmのみ取得して表示
        self.idm = binascii.hexlify(tag._nfcid)
        card_idm = str(self.idm)[2:-1]
        self.add_record_database(now_format,card_idm)
        self.idm_data = self.idm
        
    def add_record_database(self,now_format,card_idm):
        cursor.execute("INSERT INTO card_record(datetime,type,idm) values(%s,%s,%s)" % ("'" + now_format + "'","'" + self.card_type + "'","'" + card_idm + "'"))
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
                
    
    def card_data(self):
        #タッチ待ち
        self.read_id()
        return self.idm_data
