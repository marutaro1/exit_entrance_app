import mysql.connector

# MySQLに接続
cnx = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",
    database="sampledb"
)

# カーソルを作成
cursor = cnx.cursor()

# クエリを実行
query = "SELECT * FROM users"
cursor.execute(query)

# 結果を取得
result = cursor.fetchall()
print(result)

# MySQLから切断
cursor.close()
cnx.close()
