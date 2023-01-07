import binascii
import nfc
import os

import timeout_decorator

class MyCardReader(object):
    def __init__(self):
            self.idm_data = ''
            
    def on_connect(self, tag):
        #タグ情報を全て表示
        #print(tag)
        
        #IDmのみ取得して表示
        self.idm = binascii.hexlify(tag._nfcid)
        print("IDm : " + str(self.idm))
        self.idm_data = self.idm

    def read_id(self):
        try:
        
                print('ここでエラー')
                clf = nfc.ContactlessFrontend('usb')
                print('エラー乗り越え')
                try:
                    clf.connect(rdwr={'on-connect': self.on_connect})
                finally:
                    clf.close()
        except timeout_decorator.timeout_decorator.TimeoutError:
                clf.close()
                
    
    def card_data(self):
        #タッチ待ち
        self.read_id()
        return self.idm_data

