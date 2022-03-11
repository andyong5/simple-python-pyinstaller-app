import logging
import sys
import pexpect
import os
import re

__author__ = 'Andy Nguyen'

class SSH:
	def __init__(self, IP, user, passwd, root_passwd, prompt):
		self.IP = IP
		self.user = user
		self.passwd = passwd
		self.root_passwd = root_passwd
		self.prompt = prompt
		self.alarm_severity = {
			'MAJOR': 3,
			'MINOR': 4,
			'NOTIFY': 5
		}
		self.child = self.connect()


	def connect(self):
		try:
			SSH = 'ssh ' + self.user + '@' + self.IP + ' -o StrictHostKeyChecking=no'
			os.system("ssh-keygen -f " + "$HOME/.ssh/known_hosts " +
					  "-R " + self.IP + " >/dev/null 2>&1")
			child = pexpect.spawn(SSH, timeout=300)
			child.expect('(?i)Password')
			child.sendline(self.passwd)
			child.expect(self.prompt)
			logging.info('Successfully connected to ' + self.IP)
			return child
		except:
			logging.error('Failed to login to ' + self.IP)
			sys.exit(1)

	def connect_root(self):
		try:
			SSH = 'ssh ' + self.user + '@' + self.IP + ' -o StrictHostKeyChecking=no'
			os.system("ssh-keygen -f " + "$HOME/.ssh/known_hosts " +
					  "-R " + self.IP + " >/dev/null 2>&1")
			child = pexpect.spawn(SSH, timeout=300)
			child.expect('(?i)Password')
			child.sendline(self.root_passwd)
			child.expect(self.prompt)
			child.sendline('su')
			child.expect('(?i)Password')
			child.sendline(self.root_passwd)
			child.expect(self.prompt)
			logging.info('Successfully connected to ' + self.IP)
			return child
		except:
			logging.error('Failed to login to ' + self.IP)
			sys.exit(1)
	
	def get_cmd_results(self, cmd):
		self.child.sendline(cmd)
		self.child.expect(self.prompt)
		text = self.child.before.decode('utf-8')
		return str(text).strip()

	def get_alarms(self):
		t = self.get_cmd_results('show alarm')
		alarms = []
		alarm_section = False
		for line in t.splitlines():
			l = str(line.strip())
			if 'ID' in l:
				alarm_section = True
				continue
			if alarm_section:
				# regex to see if the string has any alphabet characters don't want ---|------|----
				#|---|--------|-------------------|--------------------------------------------------------------------------------|
                #|175|MINOR   |2021-09-09 04:14:35|No power detected on AC2                                                        |
				text = re.search('[a-zA-Z]', l)
				if text:
					line = l.split('|')
					alarm = {}
					alarm['eventId'] = int(line[1].strip())
					alarm['severity'] = int(self.alarm_severity.get(line[2].strip()))
					alarm['desc'] = line[4].strip()
					alarms.append(alarm)
		return alarms

	def get_gnss(self):
		output = self.get_cmd_results('show gnss status')
		gnss_status_section = False
		data = {}
		gps_list = []
		view_section = False
		for l in output.splitlines():
			if 'Latitude' in l or gnss_status_section:
				gnss_status_section = True
				if 'Latitude' in l:
					# add 2 to get rid of spacing and colon in the line
					# Latitude                  : 37 24 47.054 N 
					data['latitude'] = l[l.index(':') + 2:].strip()
				elif 'Longitude' in l: 
					data['longitude'] = l[l.index(':') + 2:].strip()
				elif 'HGT Val Ellipsoid' in l: 
					data['hgEllipsoid'] = l[l.index(':') + 2:].strip()
				elif 'Fix Quality' in l: 
					data['fixQuality'] = l[l.index(':') + 2:].strip()
				elif 'Used Satellites' in l: 
					data['usedSatellites'] = l[l.index(':') + 2:].strip()
				elif 'Reciever Status' in l: 
					data['recieverStatus'] = l[l.index(':') + 2:].strip()
				elif 'Operation Mode' in l: 
					data['opMode'] = l[l.index(':') + 2:].strip()
				elif 'Antenna Status' in l: 
					data['antennaStatus'] = l[l.index(':') + 2:].strip()
				elif 'SBAS Constellation' in l: 
					data['sbasUsedConstellation'] = l[l.index(':') + 2:].strip()
			if 'Index' in l:
				gnss_status_section = False
				view_section = True
				continue
			if view_section:
				text = re.search('[a-zA-Z]', l)
				if text:
					line = l.split('|')
					gps = {}
					gps['satId'] = line[1].strip()
					gps['gnssId'] = line[2].strip()
					gps['snr'] = line[3].strip()
					gps['azimuthAngle'] = line[4].strip()
					gps['elevationAngle'] = line[5].strip()
					gps['prRes'] = line[6].strip()
					gps_list.append(gps)
		return gps_list, data
	
	def get_system(self):
		output = self.get_cmd_results('show system')
		data = {}
		for l in output.splitlines():
			if 'Serial Num' in l:
				data['serialNumber'] = l[l.index(':') + 2:].strip()
			elif 'Model Num' in l:
				data['model'] = l[l.index(':') + 2:].strip()
			elif 'Build' in l:
				data['softwareVer'] = l[l.index(':') + 2:].strip()
			elif 'Oscillator Type' in l:
				data['oscillator'] = l[l.index(':') + 2:].strip()
		return data