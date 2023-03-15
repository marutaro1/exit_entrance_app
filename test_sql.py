import mysql.connector

container_ip = "172.17.0.2"

cnx = mysql.connector.connect(user='root',password='password',host=container_ip,database='exit_entrance_management')

cursor = cnx.cursor()
cursor.execute("insert into resident(name,number,number_people,going_to_alone,card_id) values('test',3,0,'一人外出可能','ttttt')")
cnx.commit()

query = ("select * from resident")
cursor.execute(query)
print(True)
cursor.close()

