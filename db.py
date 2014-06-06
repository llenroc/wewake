import sqlite3

# GLOBAL METHODS

def connect_db():
	db_conn = sqlite3.connect('db')
	db_curs = db_conn.cursor()
	return(db_conn, db_curs)

# USER METHODS

def user_name(phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT name FROM users WHERE phone=?', (phone,))
	user = db_curs.fetchone()
	if user != None:
		return user[0]
	else:
		return None

def user_phone(name):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT phone FROM users WHERE name=?', (name,))
	user = db_curs.fetchone()
	if user != None:
		return user[0]
	else:
		return None

def user_groups(phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT groupid FROM groups WHERE phone=?', (phone,))
	groups = db_curs.fetchall()
	if groups == None:
		return None
	else:
		group_names = []
		for group in groups:
			group_names = group_names + [group[0]]
		return group_names

def user_create(phone,name):
	(db_conn, db_curs) = connect_db()
	if user_name(phone) == None and user_phone(name) == None:
		db_curs = db_curs.execute('INSERT INTO users VALUES(?,?)', (phone, name))
		db_conn.commit()
		return True
	else:
		return False

def user_delete(phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('DELETE FROM users WHERE phone=?', (phone,))
	db_conn.commit()

def user_rename(phone,name):
	(db_conn, db_curs) = connect_db()
	old_phone = user_phone(name)
	if old_phone != None:
		return False
	db_curs = db_curs.execute('UPDATE users SET name=? WHERE phone=?', (name,phone))
	db_conn.commit()
	return True

# BUZZER METHODS

def buzzer_add(phone,groupid,tries):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('INSERT INTO buzzer VALUES (?,?,?)', (phone,groupid,tries))
	db_conn.commit()

def buzzer_remove(phone,groupid):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('DELETE FROM buzzer WHERE phone=? AND groupid=?', (phone,groupid))
	db_conn.commit()

def buzzer_get_all():
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT phone, groupid FROM buzzer')
	buzz_reqs = db_curs.fetchall()
	return buzz_reqs

def buzzer_exists(groupid):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT groupid FROM buzzer WHERE groupid=?', (groupid,))
	if db_curs.fetchone() != None:
		return True
	else:
		return False

def buzzer_retry_dec(phone,groupid):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('UPDATE buzzer SET tries = tries - 1 WHERE phone=? AND groupid=?', (phone,groupid))
	db_curs = db_curs.execute('DELETE FROM buzzer WHERE tries <= 0')
	db_conn.commit()

# INFLIGHT METHODS

def inflight_add(phone,groupid):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('INSERT INTO inflight VALUES(?,?)', (phone,groupid))
	db_conn.commit()

def inflight_exists(phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT * FROM inflight WHERE phone=?',(phone,))
	if db_curs.fetchone() != None:
		return True
	else:
		return False	

def inflight_group(phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT groupid FROM inflight WHERE phone=?',(phone,))
	res = db_curs.fetchone()
	return res[0]

def inflight_remove(phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('DELETE FROM inflight WHERE phone=?',(phone,))
	db_conn.commit()

# GROUP METHODS

def group_create(groupid,admin):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('INSERT INTO groups VALUES (?,?,?)', (groupid, admin, '?'))
	db_curs = db_curs.execute('INSERT INTO admins VALUES (?,?)', (groupid, admin))
	db_conn.commit()

def group_admin(groupid):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT phone FROM admins WHERE groupid = ?', (groupid,))
	admin = db_curs.fetchone()
	if admin != None:
		return admin[0]
	else:
		return None

def group_exists(groupid):
	admin = group_admin(groupid)
	if admin == None:
		return False
	else:
		return True

def group_member(groupid,phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT * FROM groups WHERE groupid = ? AND phone = ?', (groupid, phone))
	res = db_curs.fetchone()
	if res != None:
		return True
	else:
		return False

def group_add(groupid,phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('INSERT INTO groups VALUES (?,?,?)', (groupid,phone,'?'))	
	db_conn.commit()

def group_remove(groupid,phone):
	if group_member(groupid, phone) == True:
		(db_conn, db_curs) = connect_db()
		db_curs = db_curs.execute('DELETE FROM groups WHERE groupid=? AND phone=?', (groupid,phone))
		db_conn.commit()	
		return True
	else:
		return False

def group_members(groupid):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT phone FROM groups WHERE groupid=?', (groupid,))
	group = db_curs.fetchall()
	if group != None:
		numbers = []
		for member in group:
			numbers = numbers + [member[0]]
		return numbers
	else:
		return None

def group_delete(groupid):
	group_reset(groupid)
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('DELETE FROM groups WHERE groupid=?', (groupid,))
	db_curs = db_curs.execute('DELETE FROM admins WHERE groupid=?', (groupid,))
	db_conn.commit()

def group_reset(groupid):
	(db_conn, db_curs) = connect_db()
	members = group_members(groupid)
	for member in members:
		db_curs = db_curs.execute('DELETE FROM buzzer WHERE groupid=?', (groupid,))	
	db_curs = db_curs.execute('DELETE FROM buzzer WHERE groupid=?', (groupid,))
	db_curs = db_curs.execute('DELETE FROM alarms WHERE groupid=?', (groupid,))
	db_curs = db_curs.execute('UPDATE groups SET avail=? WHERE groupid=?', ('?',groupid))
	db_conn.commit()

def group_buzz(groupid,tries):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('DELETE FROM alarms WHERE groupid=?', (groupid,))
	db_conn.commit()

	members = group_members(groupid)
	for member in members:
		if group_avail_get(groupid,member) == '?':
			buzzer_add(member,groupid,tries)

def group_avail_set(groupid,phone,avail):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('UPDATE groups SET avail=? WHERE groupid=? AND phone=?', (avail,groupid,phone))
	db_conn.commit()

def group_avail_get(groupid,phone):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT avail FROM groups WHERE groupid=? AND phone=?', (groupid,phone))
	result = db_curs.fetchone()
	if result == None:
		return None
	else:
		return result[0]

# ALARM METHODS

def alarm_cancel(groupid):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('DELETE FROM alarms WHERE groupid=?', (groupid,))
	db_conn.commit()

def alarm_set(groupid,time,tries):
	alarm_cancel(groupid)
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('INSERT INTO alarms VALUES (?,?,?)', (groupid, time, tries))
	db_conn.commit()

def alarm_check(groupid):
	(db_conn, db_curs) = connect_db()
	db_curs = db_curs.execute('SELECT alarm FROM alarms WHERE groupid=?', (groupid,))
	alarm_res = db_curs.fetchone()
	if alarm_res == None:
		return None
	else:
		return alarm_res[0]

def alarm_get_next():
	(db_conn, db_curs) = connect_db()
	db_curs.execute('SELECT groupid, alarm, tries FROM alarms ORDER BY time(alarm) ASC')
	result = db_curs.fetchone()
	if result != None:
		groupid = result[0]
		alarm = result[1]
		tries = result[2]
		return (groupid, alarm, tries)
	else:
		return (None,None,None)