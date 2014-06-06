
# TODO: Validate inputs
# TODO: Invite system/ban list
# TODO: Timezone support
# TODO: Group messaging
# TODO: Record response

from flask import Flask, request, redirect
import sqlite3
import twilio.twiml
import time
import datetime
import db
import thread
import config
import sys
from twilio.rest import TwilioRestClient

app_url = config.app_url
account_sid = config.account_sid
auth_token = config.auth_token
twilio_phone = config.twilio_phone
client = None

app = Flask(__name__)

@app.route("/", methods=['GET','POST'])
def wewake():
	try:
		# Parse user request
		phone = request.values.get('From', None)
		req_body = request.values.get('Body', None)

		req_parts = req_body.split(' ')
		command = req_parts[0].upper()

		# Check if user is registered, otherwise get them to register
		user = db.user_name(phone)
		if user == None:
			# If user texted anything but REGISTER, send them registration prompt
		 	if command != 'REGISTER':
		 		resp_body = 'Hello! Welcome to WeWake!\nPlease text REGISTER <name> to create your account.'
		 	# Otherwise, check whether user is already registered, and if so, cancel re-registration
		 	else:
		 		name = req_parts[1]
		 		user_created = db.user_create(phone,name)
		 		if user_created == True:
		 			resp_body = 'Hi, ' + name + '! Your account has been created.\nText INSTRUCTIONS to get a list of available commands.'	
		 		else:
		 			resp_body = 'Sorry, the name \'' + name + '\' is already in use. Please choose another name and try again.'

		# INSTRUCTIONS menu
		elif command == 'INSTRUCTIONS':
			resp_body = '\nWelcome to WeWake!\n' \
			'\nYou can use the following commands:\n\n' \
			'* Account *\n' \
			'RENAME <name> - Rename your account\n' \
			'LIST - List all groups you are a part of\n' \
			'JOIN <group> - Adds you to a group\n' \
			'LEAVE <group> - Removes you from a group\n' \
			'\n' \
			'* Groups *\n' \
			'CREATE <group>- Create a new group\n' \
			'INVITE <phonenumber> <group> - (A) Invite a user to a group\n'
			'VIEW <group> - View details for a group\n' \
			'REMOVE <name> <group> - (A) Removes a member from a group\n' \
			'DELETE <group> - (A) Delete a group\n' \
			'\n' \
			'* Paging *\n'
			'TEXT <group> <message> - (A) Send a message to the group\n' \
			'CALL <group> - (A) Starts a conference call with members of the group\n' \
			'\n' \
			'* Alarms *\n' \
			'SET <group> <HH:MM> <retries> - (A) Sets an alarm for the group\n' \
			'RESET <group> - (A) Resets alarm status for group\n' \
			'CANCEL <group> - (A) Cancels a group alarm\n' \
			'CHECK <group> - Checks a group alarm status\n' \
			'WAKE <group> - (A) Wakes up group immediately\n' \
			'\n' \
			'(A) - Group admin only commands'

		# Disallow re-REGISTER if already registered
		elif command == 'REGISTER':
			resp_body = 'Sorry, this number has already been registered. Use RENAME <name> to change your name.'

		### ACCOUNT COMMANDS ###

		# Registered user wants to RENAME account
		elif command == 'RENAME':
			newname = req_parts[1]
			if db.user_rename(phone,newname) == True:
				resp_body = 'Hi, ' + newname + '. Your name has been changed.'
			else:
				resp_body = "ERROR: Name already in use."

		# LIST all groups
		elif command == 'LIST':
			name = db.user_name(phone)
			groups = db.user_groups(phone)
			resp_body = name + '\n'
			if groups == None or groups == []:
				resp_body = 'You are not a member of any groups.'
			else:
				for group in groups:
					admin = db.group_admin(group)
					if admin == phone:
						resp_body = resp_body + group + ' <Admin>\n'
					else:
						resp_body = resp_body + group + '\n'

		# JOIN a group
		elif command == 'JOIN':
			groupid = req_parts[1]
			group_exists = db.group_exists(groupid)
			if group_exists == True:
				db.group_add(groupid,phone)
				resp_body = 'You have been added to the group ' + groupid + '.'
				# Inform group admin
				name = db.user_name(phone)
				group_text_admin(groupid, name + ' <' + phone + '> has joined ' + groupid + '.')
			else:
				resp_body = 'ERROR: Group does not exist.'

		# LEAVE a group
		elif command == 'LEAVE':
			groupid = req_parts[1]
			group_exists = db.group_exists(groupid)
			if group_exists == True:
				admin = db.group_admin(groupid)
				if admin == phone:
					resp_body = 'You cannot leave a group you created. You have to delete it.'
				else:
					db.group_remove(groupid,phone)
					resp_body = 'You have been removed from the group ' + groupid + '.'
					name = db.user_name(phone)
					group_text_admin(groupid, name + ' <' + phone + '> has left ' + groupid + '.')
			else:
				resp_body = 'ERROR: Group does not exist.'	

		### GROUP COMMANDS ###

		# CREATE group
		elif command == 'CREATE':
			groupid = req_parts[1]

			db.group_create(groupid, phone)
			resp_body = 'Your group ' + groupid + ' has been created.'

		# INVITE a user
		elif command == 'INVITE':
			invitee = req_parts[1]
			groupid = req_parts[2]
			inviter = db.user_name(phone)

			# Santize invitee phone number
			if invitee[0] != '+' or invitee[1:].isdigit() == False:
				resp_body = "ERROR: Invalid number. Prefix a '+', include all country and area codes and use no spaces, hypens or parantheses"
			else:
				# Check if group exists
				group_exists = db.group_exists(groupid)
				if group_exists == True:
					admin = db.group_admin(groupid)
					if admin == phone:
						# Check if user exists
						invitee_name = db.user_name(invitee)
						if invitee_name != None:
							text_send(invitee, inviter + ' has invited you to join the group ' + groupid + '. Text JOIN <group> to join the group.')
						else:
							# Invite user
							text_send(invitee, inviter + ' has invited you to join the group ' + groupid + 'on WeWake. Text REGISTER <name> to this number to sign up. Then text JOIN <group> to join the group.')
						resp_body = invitee + ' has been invited to join ' + groupid + '.'
					else:
						resp_body = "ERROR: Only the admin can invite members to join the group."
				else:
					resp_body = 'ERROR: Group does not exist.'

		# VIEW group members
		elif command == 'VIEW':
			groupid = req_parts[1]
			members = db.group_members(groupid)
			admin = db.group_admin(groupid)
			if members == None:
				resp_body = 'ERROR: Group does not exist.'
			else:
				resp_body = groupid + '\n'
				for member in members:
					member_name = db.user_name(member)
					member_avail = db.group_avail_get(groupid,member)
					if member == admin:
						resp_body = resp_body + member_name + ' <Admin> - ' + member + ' - ' + member_avail + '\n'
					else:
						resp_body = resp_body + member_name + ' - ' + member + ' - ' + member_avail + '\n'

		# REMOVEs a user from a group
		elif command == 'REMOVE':
			user = req_parts[1]
			groupid = req_parts[2]
			if db.group_exists(groupid) == True:
				user_phone = db.user_phone(user)
				if user_phone != None:
					if db.group_remove(groupid,user_phone) == True:
						resp_body = user + ' has been removed from ' + groupid + '.'
						text_send(user_phone, 'You have been reoved from the group ' + groupid + ' by the group admin.')
					else:
						resp_body = "ERROR: User is not a part of this group."
				else:
					resp_body = "ERROR: User does not exist."				
			else:
				resp_body = "ERROR: Group does not exist."

		# DELETE group
		elif command == 'DELETE':
			groupid = req_parts[1]
			if db.group_exists(groupid) == True:
				if phone == db.group_admin(groupid):
					group_text_all(groupid, 'The group admin has deleted the group ' + groupid + '.')
					db.group_delete(groupid)
					resp_body = None
				else:
					resp_body = 'ERROR: Only the group admin can delete the group. Text LEAVE <group> to leave the group.'
			else:
				resp_body = 'ERROR: Group does not exist.'

		# RESET group alarm status
		elif command == 'RESET':
			groupid = req_parts[1]
			if db.group_exists(groupid) == True:
				if phone == db.group_admin(groupid):
					db.alarm_cancel(groupid)
					db.group_reset(groupid)
					resp_body = groupid + ' has been reset.'
				else:
					resp_body = 'ERROR: Only the group admin can reset the alarm.'
			else:
				resp_body = 'ERROR: Group does not exist.'

		# Sends a PAGE to the group
		elif command == 'TEXT':
			groupid = req_parts[1]
			if db.group_exists(groupid) == True:
				if phone == db.group_admin(groupid):
					msg = " ".join(req_parts[2:])
					group_text_all(groupid, "<Page from " + groupid + ">: " + msg);
					resp_body = None
				else:
					resp_body = "ERROR: Only the group admin can page the group."
			else:
				resp_body = "ERROR: Group does not exist."

		# CALLs a group and sets up a conference call
		elif command == 'CALL':
			groupid = req_parts[1]
			if db.group_exists(groupid) == True:
				if phone == db.group_admin(groupid):
					members = db.group_members(groupid)
					for member in members:
						conf(member,groupid)
					resp_body = None
				else:
					resp_body = "ERROR: Only the group admin can page the group."
			else:
				resp_body = "ERROR: Group does not exist."


		### ALARMS ###

		# SET alarm
		elif command == 'SET':
			groupid = req_parts[1]
			timestr = req_parts[2]
			retries = req_parts[3]

			try:
				tries = int(retries) + 1
				if db.group_exists(groupid):
					if phone == db.group_admin(groupid):
						alarm = parse_alarm(timestr)
						if alarm != None:
							db.alarm_set(groupid,alarm,tries)
							resp_body = 'Alarm set for ' + groupid + ' @ ' + alarm + '.'
							group_text_all(groupid, resp_body)
							resp_body = None
						else:
							resp_body = 'ERROR: Invalid time format: Use HH:MM.'
					else:
						resp_body = 'ERROR: Only the group admin can set alarms.'
				else:
					resp_body = 'ERROR: Group does not exist.'
			except ValueError:
				resp_body = 'ERROR: Invalid number of retries'
			
		# CANCEL alarm
		elif command == 'CANCEL':
			groupid = req_parts[1]
			if db.group_exists(groupid):
				if phone == db.group_admin(groupid):
					db.alarm_cancel(groupid)
					resp_body = 'Alarm cancelled for ' + groupid + '.'
					group_text_all(groupid,resp_body)
					resp_body = None
				else:
					resp_body = 'ERROR: Only the group admin can cancel alarms.'	
			else:
				resp_body = 'ERROR: Group does not exist.'

		# CHECK alarm
		elif command == 'CHECK':
			groupid = req_parts[1]
			if db.group_exists(groupid):
				alarm = db.alarm_check(groupid)
				if alarm != None:
					resp_body = 'Alarm set for ' + groupid + ' @ ' + alarm + '.'
				else:
					resp_body = 'No alarm set for ' + groupid + '.'
			else:
				resp_body = 'ERROR: Group does not exist.'

		elif command == 'WAKE':
			groupid = req_parts[1]
			if db.group_exists(groupid):
				if phone == db.group_admin(groupid):
					if db.buzzer_exists(groupid) == False:
						db.group_buzz(groupid,0)
						resp_body = groupid + ' is being woken up.'
					else:
						resp_body = 'ERROR: Alarm already in progress.'
				else:
					resp_body = 'ERROR: Only the admin can wake the group.'
			else:
				resp_body = 'ERROR: Group does not exist.'

		else:
			resp_body = 'ERROR: Invalid command. Text INSTRUCTIONS to get a list of available commands.'

	except:
		resp_body = "ERROR: Check inputs and try again. Text INSTRUCTIONS to get a list of available commands."

	### SEND RESPONSE TO USER ###
	twiml_resp = twilio.twiml.Response()
	twiml_resp.message(resp_body)
	return str(twiml_resp)

### TEXT METHDODS ###

def text_send(phone,text):
	client.messages.create(to=phone, from_=twilio_phone, body=text)

def group_text_admin(groupid,text):
	if db.group_exists(groupid) == True:
		admin = db.group_admin(groupid)
		text_send(admin,text)
		return True
	else:
		return False

def group_text_all(groupid,text):
	if db.group_exists(groupid) == True:
		members = db.group_members(groupid)
		for phone in members:
			text_send(phone,text)
		return True
	else:
		return False

### CALL METHODS ###

def conf(phone,groupid):
	print 'Calling ' + phone
	db.inflight_add(phone,groupid)
	client.calls.create(to=phone,
		from_=twilio_phone,
		url=app_url+"conference")

def buzz(phone,groupid):
	print 'Buzzing ' + phone
	db.inflight_add(phone,groupid)
	client.calls.create(to=phone,
		                from_=twilio_phone,
		                url=app_url+"alarm",
		                if_machine="Hangup",
		                status_callback=app_url+"postflight")


@app.route("/conference", methods=['POST'])
def conference():
	phone = request.values.get('To', None)
	groupid = db.inflight_group(phone)
	db.inflight_remove(phone)

	twiml_resp = twilio.twiml.Response()
	twiml_resp.say("This is a conference call from WeWake for your group : " + groupid + ". Please wait while other members are connected.")
	with twiml_resp.dial() as d:
		d.conference(name=groupid, muted=False, beep=True,
			startConferenceOnEnter=True, endConferenceOnExit=False)
	return str(twiml_resp)

### ALARM HANDLER ###

@app.route("/postflight", methods=['POST'])
def postflight():
	phone = request.values.get('To', None)
	groupid = db.inflight_group(phone)
	db.inflight_remove(phone)
	db.buzzer_retry_dec(phone,groupid)
	return str(twilio.twiml.Response())

@app.route("/alarm_resp", methods=['POST'])
def alarm_resp():
	phone = request.values.get('To', None)
	digits = request.values.get('Digits', None)
	groupid = db.inflight_group(phone)

	twiml_resp = twilio.twiml.Response()
	
	if digits == '1' or digits == '2':
		twiml_resp.say('Your response has been recorded.')
		if digits == '1':
			db.group_avail_set(groupid,phone,'Y')
		elif digits == '2':
			db.group_avail_set(groupid,phone,'N')
		db.buzzer_remove(phone,groupid)
	
	twiml_resp.say('Goodbye!')
	return str(twiml_resp)

@app.route("/alarm", methods=['GET','POST'])
def alarm():
	phone = request.values.get('To', None)
	twiml_resp = twilio.twiml.Response()
	status = request.values.get('CallStatus', None)

	if status == 'in-progress':
		twiml_resp.say("Hello! This is your team alarm from WeWake! Please wake up!")
		with twiml_resp.gather(action=app_url+"alarm_resp", method='POST', timeout=10, numDigits=1) as g:
			g.say("Please press 1 if you are available. Press 2 if you are not available.")
	return str(twiml_resp)

### ALARM THREADS ###

def buzzer():
	while (1):
		buzz_reqs = db.buzzer_get_all()
		for buzz_req in buzz_reqs:
			phone = buzz_req[0]
			groupid = buzz_req[1]
			if db.inflight_exists(phone) == False:
				buzz(phone,groupid)
		time.sleep(1)

def clock():
	while (1):
	# Fetch next alarm
		(groupid, alarm_str, tries) = db.alarm_get_next()

		if groupid == None:
			time.sleep(1)
			continue

		# Parse alarm
		now = datetime.datetime.now()
		alarm = datetime.datetime.strptime(alarm_str, "%Y-%m-%dT%H:%M:%S")

		# Fire alarm if ready
		if alarm <= now and db.buzzer_exists(groupid) == False:
			print 'Buzzing ' + groupid
			db.group_buzz(groupid,tries)
		else:
			time.sleep(1)

def parse_alarm(alarm_str):
	now = datetime.datetime.now()
	delta = datetime.timedelta(days=1)
	alarm = now
	try:
		alarm = datetime.datetime.strptime(alarm_str,'%H:%M')
	except ValueError:
		return None
	alarm = alarm.replace(year=now.year,month=now.month,day=now.day)
	if alarm < now:
		alarm = alarm + delta
	return alarm.isoformat()

### MAIN METHOD ###

if __name__ == "__main__":
	if app_url == "" or twilio_phone == "" or account_sid == "" or auth_token == "":
		print("ERROR: Edit config.py. Read README.md.")
		sys.exit(1)
	client = TwilioRestClient(account_sid, auth_token)
	thread.start_new_thread(clock, ())
	thread.start_new_thread(buzzer, ())
	app.run(debug=True)