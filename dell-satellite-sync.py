#!/usr/bin/env python
#
# _author_ = Vinny Valdez <vvaldez@redhat.com>
# _version_ = 1.0
#
# Copyright (c) 2009 Red Hat, Inc.
#
# Updates for version 1.0 by Jose De La Rosa <jose_de_la_rosa@dell.com>
# Copyright (c) 2013 Dell
# See README for updates
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
# 
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation. 

# Populate dell-satellite-sync.conf with your specific information or pass as arguments
execfile("/etc/sysconfig/dell-satellite-sync/dell-satellite-sync.conf")
idfile = "/etc/sysconfig/dell-satellite-sync/dell-system-ids"
RED       = '\033[31m'
GREEN     = '\033[32m'
BOLD      = '\033[1m'
ENDC      = '\033[0m'                     # end color

# Change this to a specific version as needed
SYSTEM_VENDOR_ID = 'system.ven_0x1028'
PLATFORM_INDEPENDENT = 'platform_independent'		# Subdir of repo that contains platform agnostic rpms
DELL_INFO = { 
	# Careful with the label and name values, they are appended to system ids + base_channel names, and cannot exceed 64 characters
	'label' : 'dell-om',
	'name' : 'Dell OM',
	'summary' : 'Dell OpenManage Software' 
}

###################################################################################
# Import modules
try:
	import xmlrpclib, os, sys, signal, time, re, getpass, urllib2
	from optparse import OptionParser
	from urllib2 import Request, urlopen, URLError
except:
	print "Could not import modules"
	raise

# options parsing
usage = "\n%prog [options]\n\nThis program will create Satellite or Spacewalk channels for the Dell yum repos,\npopulate them with RPMs and subscribe registered clients to their proper channels."
description = "Use -h or --help for all available options. Options can be specified as arguments\nor defined in /etc/sysconfig/dell-satellite-sync/dell-satellite-sync.conf."
parser = OptionParser(usage=usage, description=description)
parser.add_option("-u", "--user", dest="user", help="Satellite username", default=SATELLITE_USER)
parser.add_option("-p", "--password", dest="password", help="Satellite password (will be prompted if omitted)", default=SATELLITE_PASSWORD)
parser.add_option("-s", "--satserver", dest="satserver", help="FQDN of Satellite server", default=SATELLITE_SERVER)
parser.add_option("-S", "--server-actions-only", action="store_true", dest="server_actions_only", help="Create channels and upload RPMs, skip system subscriptions.", default=False)
parser.add_option("-r", "--repo", dest="repo", help="Location of Dell yum repositories. Defaults to 'http://linux.dell.com/repo/hardware/latest'", default=REPO)
parser.add_option("-c", "--channel", dest="channel", help="OS parent channel to use. e.g. 'rhel4', 'rhel5', 'rhel6' or 'sles11'", default=CHANNEL)
parser.add_option("-o", "--only-systems", dest="only_systems", help="Create system-specific channels ONLY for these systems. e.g. 'per720,per620,pet620'", default=ONLY_SYSTEMS)
parser.add_option("-a", "--all-systems", action="store_true", dest="all_systems", help="Create system-specific channels for ALL supported Dell systems.", default=False)
parser.add_option("-d", "--delete", action="store_true", dest="delete", help="Delete all unused Dell channels / packages for given OS parent channel.", default=False)
parser.add_option("-C", "--client-actions-only", action="store_true", dest="client_actions_only", help="Subscribe systems to corresponding channels", default=False)
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help="Enable verbose output", default=False)
parser.add_option("-D", "--debug", action="store_true", dest="debug", default=False, help="Enable lots of debug output (more than verbose)")

(options, terms) = parser.parse_args()

def timestamp():
    lt = time.localtime(time.time())
    return "%02d.%02d.%04d %02d:%02d:%02d:" % (lt[1], lt[2], lt[0], lt[3], lt[4], lt[5])

# Perform some setup tasks
error = False
if options.user == '':
	print "! Error: '--user' must be specified"
	error = True
if options.satserver == '':
	print "! Error: '--satserver' must be specified"
	error = True
if options.server_actions_only and options.client_actions_only:
	print "! Error: '--server-actions-only' and '--client-actions-only' are mutually exclusive"
	error = True
if not options.server_actions_only and not options.client_actions_only:
	print "! Error: '--server-actions-only' or '--client-actions-only' must be specified"
	error = True
if (options.server_actions_only):
	if options.repo == '' and not options.delete:
		print "! Error: '--repo' must be specified"
		error = True
	if not (options.channel == "rhel4" or options.channel == "rhel5" or options.channel == "rhel6" or options.channel == "sles11"):
		print "! Error: '--channel' must be specified with a valid OS channel."
		error = True
	if options.only_systems and options.all_systems and not options.delete:
		print "! Error: '--only-systems' and '--all-systems' are mutually exclusive"
		error = True
if (options.delete and not options.server_actions_only):
	print "! Error: '--server-actions-only' must be specified with '--delete'"
	error = True
if error:
	print description
	sys.exit(1)
else:
	if options.password == '':
		options.password = getpass.getpass()

# global parameters
sat_url = "http://%s/rpc/api" % options.satserver
if not options.repo[-1] == "/":
	repo_url = options.repo + "/"
else:
	repo_url = options.repo

if options.debug:
	client_verbose = 1
else:
	client_verbose = 0
client = xmlrpclib.Server(sat_url, verbose = client_verbose)

def check_url(url):
	try:
		response = urllib2.urlopen(url)
	except URLError, e:
		if hasattr(e, 'reason'):
			# Couldn't connect to server
			return False
		elif hasattr(e, 'code'):
			# The server couldn't fulfill the request
			return False
	return response	# If we get here, then connection to url is ok

def build_supported_channels(channel):
	# RHEL 6 channels
	if channel == "rhel6":
		SUPPORTED_CHANNELS = {
		#	'other_existing_base_channel' : { 'arch' : 'arch_type', 'subdir' : 'subdir within Dell repo' },
			'rhel-i386-server-6' :  { 'arch' : 'i386' , 'subdir' : 'rh60' },
			'rhel-x86_64-server-6' :  { 'arch' : 'x86_64' , 'subdir' : 'rh60_64' },
		}
	# RHEL 5 channels
	elif channel == "rhel5":
		SUPPORTED_CHANNELS = {
		#	'other_existing_base_channel' : { 'arch' : 'arch_type', 'subdir' : 'subdir within Dell repo' },
			'rhel-i386-server-5' :  { 'arch' : 'i386' , 'subdir' : 'rh50' },
			'rhel-x86_64-server-5' :  { 'arch' : 'x86_64' , 'subdir' : 'rh50_64' },
		}
	# RHEL 4 channels
	elif channel == "rhel4":
		SUPPORTED_CHANNELS = {
		#	'other_existing_base_channel' : { 'arch' : 'arch_type', 'subdir' : 'subdir within Dell repo' },
			'rhel-i386-as-4' :  { 'arch' : 'i386' , 'subdir' : 'rh40' },
			'rhel-x86_64-as-4' :  { 'arch' : 'x86_64' , 'subdir' : 'rh40_64' },
		}
	# SLES 11 channels
	elif options.channel == "sles11":
		SUPPORTED_CHANNELS = {
		#	'other_existing_base_channel' : { 'arch' : 'arch_type', 'subdir' : 'subdir within Dell repo' },
			'sles11-sp1-pool-x86_64' :  { 'arch' : 'x86_64' , 'subdir' : 'suse11_64' },
		}
	else:
		# Should not really reach here, but just in case
		print "You must provide a valid OS channel with '--channel'. Use -h or --help for details."
		sys.exit(1)

	return SUPPORTED_CHANNELS

def listall():
        '''Replace only_systems with all systems found in idfile'''
        systems = []
        # open file where Dell system IDs are defined
        if os.path.isfile(idfile):
                fh = open(idfile, 'r')
                ll = fh.readlines()
                fh.close()
        else:
                print RED + "Could not find Dell system ID file %s" % idfile + ENDC
                sys.exit(1)
        for line in ll:
		if not line.strip() or line[0] == '#':	# skip comments and empty lines
			continue
                server = line.split(':')[0]
                systems.append(server)

        return systems

def build_system_list(vendor_id, only_systems):
	'''Go through system ID file and look for matches for servers given'''
	systems = {}

	# open file where Dell system IDs are defined
	if os.path.isfile(idfile):
  		fh = open(idfile, 'r')
  		ll = fh.readlines()
  		fh.close()
	else:
  		print RED + "Could not find Dell system ID file %s" % idfile + ENDC
  		sys.exit(1)

	# Read file and look for line that contains 'system' we want
	for server in only_systems:
		found = False
		for line in ll:
			if not line.strip() or line[0] == '#':	# skip comments and empty lines
				continue
			if server == line.split(':')[0]:
				if options.verbose: print BOLD + "+ Adding %s to requested system list." % server + ENDC
    				systemid = (line.rstrip().split(':'))[1]    # remove end-of-line, then split, then extract location '1'
				full_system_id = "system.ven_0x1028.dev_" + systemid
				systems[full_system_id] = server
		 		found = True
    				break
		if not found:
			print RED + "- System '%s' not found in %s" % (server, idfile) + ENDC 
		
	return systems

def delete_channel(key, label):
        '''Deletes a channel on the Satellite server and removes packages (if any)'''
	packages_to_remove = []
	packages = client.channel.software.list_all_packages(key, label)
	for package in packages:
		if options.debug: print "  + Removing package: %s:%i from %s" % (package['name'], package['id'], label)
		packages_to_remove.append(int(package['id']))
	if not client.channel.software.remove_packages(key, label, packages_to_remove):
		if options.verbose: print "  Warning: Unable to delete the following packages:", packages_to_remove
        print "  + Deleting channel:", label
        return client.channel.software.delete(key, label)

def channel_exists(key, channel, channels):
	'''Check if channel exists in the list of channels'''
	for curchan in channels:
		if channel == curchan['label']:
			if options.debug: print "    Match found for %s and %s" % (channel, curchan['label'])
			return True
	if options.debug: print "    No match found for", channel
	return False

def create_channel(key, label, channels, name, summary, arch, parent):
	# Creates a temporary channel, then clones it with GPG key location, then deletes tmp channel
	# I'm doing this because just creating a channel does not currently support assigning it a GPG key.
	# Also, each channel can only have one GPG key
	if PLATFORM_INDEPENDENT in label:
		channel_map = { 'name' : name, 'label' : label, 'summary' : summary, 'parent_label' : parent, 'gpg_url' : repo_url + 'RPM-GPG-KEY-libsmbios' }
	else:
		channel_map = { 'name' : name, 'label' : label, 'summary' : summary, 'parent_label' : parent, 'gpg_url' : repo_url + 'RPM-GPG-KEY-dell' }
	try:
		if label not in channels:
			if options.verbose: print "  + Creating temporary channel:", label + '-tmp'
 			client.channel.software.create(key, label + '-tmp', name + '-tmp', summary, arch, parent)
		else:
			print "-  Temporary channel exists, using that:", label + '-tmp'
	except:
		print RED + "! Error creating temporary channel:", label + '-tmp' + ENDC
		raise
	try:
		if options.verbose: print "  + Cloning temporary channel into real channel:", label
 		repo_id = client.channel.software.clone(key, label + '-tmp', channel_map, True)
	except:
		print RED + "! Error cloning channel:", label + ENDC
		raise
	try:
		if options.verbose: print "  + Deleting temporary channel:", label + '-tmp'
 		client.channel.software.delete(key, label + '-tmp')
	except:
		print RED + "  Error deleting channel:", label + '-tmp' + ENDC
		raise

	return repo_id

def subscribe(key, base_channel, new_channel, system_id, system_name):
	'''Subscribes system_id to new_channel'''
	# Get a list of current child channels, since subscribe removes all channels
	channels = client.system.list_subscribed_child_channels(key, system_id)
	channel_labels = []
	for channel in channels:
		channel_labels.append(channel['label'])
	if new_channel in channel_labels:
		if options.verbose: print "  %s is already subscribed to %s." % (system_name, new_channel)
		return True
	available_channels = client.system.list_subscribable_child_channels(key, system_id)
	available_channel_labels = []
	for channel in available_channels:
		available_channel_labels.append(channel['label'])
	if new_channel not in available_channel_labels:
		if options.verbose: print "Warning: Attemped to subscribe %s to %s, but it is not available." % (system_name, new_channel)
		return False
	if options.verbose: print GREEN + "  + Subscribing %s to %s" % (system_name, new_channel) + ENDC
	channel_labels.append(new_channel)
	return client.system.set_child_channels(key, system_id, channel_labels)

def subscribe_clients(key):
	'''Creates list of registered clients, and subscribes them to the platform_independent channel'''
	systems = client.system.list_systems(key)
	scheduled = []
	for system in systems:
		# Check if it is a Dell system
		if options.verbose: print "Checking system %s with id %i:" % (system['name'], system['id'])
		system_dmi = client.system.get_dmi(key, system['id'])
		if system_dmi == '':
			vendor = 'unknown'
		else:
			vendor = system_dmi['vendor']
		if not ('Dell' in vendor):	# Do only for Dell systems, but we can add back a command parameter to override this 
			print "  Warning: %s vendor is '%s', skipping." % (system['name'], vendor)
			if options.verbose: print "  - Removing %s from list" % (system['name'])
			system['skip'] = True
		else:
			if options.verbose: print "  %s vendor is: '%s'" % (system['name'], vendor)
			system['skip'] = False
			try:
				base_channel = client.system.get_subscribed_base_channel(key, system['id'])['label']
				system['base_channel'] = base_channel
				if options.verbose: print "  %s is subscribed to base channel: %s." % (system['name'], base_channel)
				scheduled.append(system['id'])
				new_channel = DELL_INFO['label'] + '-' + PLATFORM_INDEPENDENT + '-' + base_channel
				system['platform_independent'] = new_channel
				if not subscribe(key, base_channel, new_channel, system['id'], system['name']):
					system['skip'] = True
					if options.verbose: print RED + "  Error attempting to subscribe %s to %s." % (system['name'], new_channel) + ENDC
			except:
				print RED + "  No base channel found for %s. Please subscribe this system to a supported channel." % (system['name']) + ENDC
				raise
	return systems

def schedule_actions(key, systems):
	'''Schedules GPG key install, package install, and "smbios-sys-info" action on clients'''
	gpg_script = '''
#!/bin/bash
# Check if libsmbios gpg key is installed
rpm -q gpg-pubkey-5e3d7775-42d297af
if [ ! "$?" = "0" ]
then
	echo Importing RPM-GPG-KEY-libsmbios
	rpm --import ''' + repo_url + 'RPM-GPG-KEY-libsmbios' + '''
fi
# Check if dell gpg key is installed
rpm -q gpg-pubkey-23b66a9d-3adb5504
if [ ! "$?" = "0" ]
then
	echo Importing RPM-GPG-KEY-dell
	rpm --import ''' + repo_url + 'RPM-GPG-KEY-dell' + '''
fi
	'''
	action_script = '''
#!/bin/bash
rpm -q smbios-utils
if [ ! "$?" = "0" ]
then
	echo Waiting for smbios-utils to be installed
	sleep 60
fi
/usr/sbin/smbios-sys-info
	'''
	for system in systems:
		if system['skip']: continue
		print "Scheduling for %s:" % system['name']
		# First find the package id for smbios-utils
		package_found = False
		package_search_tries = 0
		while not package_found: 	# Added retry while looking for smbios-utils.  If it happens too fast it won't be synced yet.
			smbios_packages = []
			packages = client.channel.software.list_all_packages(key, system['platform_independent'])
			for package in packages:
				if package['name'] == 'smbios-utils':
					smbios_packages.append(package['id'])
					if options.debug: 
						print "  + Package %s:%i found for %s in channel %s." % (package['name'], package['id'], system['name'], system['platform_independent'])
			smbios_packages.sort()
			if smbios_packages == []:
				if package_search_tries > 5:
					print RED + "! Fatal Error: Could not find 'smbios-utils' uploaded on the server." + ENDC
					sys.exit(1)
				if options.verbose: print "  Package 'smbios-utils' not found, waiting for server sync."
				package_search_tries += 1
				time.sleep(5)
				continue
			else:
				package_found = True
			if options.debug: print "  %s package search results: %s" % (system['name'], smbios_packages)
		smbios_package = smbios_packages[-1]
		# First try to schedule gpg key imports for libsmbios and dell
		try:
			if options.verbose: print "  + Scheduling GPG key install on system: %s id: %i" % (system['name'], system['id'])
			id = client.system.schedule_script_run(key, system['id'], "root", "root", 600, gpg_script, system['last_checkin'])
		except:
			print RED + "! Error trying to schedule GPG key install for %s" % system['name'] + ENDC
			system['skip'] = True
			if options.debug: raise
			continue 
		# Now schedule package install for 'smbios-utils'
		try:
			# Find smbios-utils in newly subscribed platform-independent channel, and schedule install
			if options.verbose: print "  + Scheduling package install 'smbios-utils' on system: %s id: %i" % (system['name'], system['id'])
			# TODO: Need to schedule it 1 minute after 'last_checkin' to avoid race condition with gpg keys
			result = client.system.schedule_package_install(key, system['id'], smbios_package, system['last_checkin'])
			if options.debug: print "  Result of package scheduling for %s: %i" % (system['name'], result)
		except:
			print RED + "! Error trying to install 'smbios-utils' package for %s" % system['name'] + ENDC
			system['skip'] = True
			if options.debug: raise
			continue
		# Now schedule script that gets system ID. Will not do anything if 'smbios-utils' is not installed.
		try:
			if options.verbose: print "  + Scheduling execution of 'smbios-sys-info' on system: %s id: %i" % (system['name'], system['id'])
			# TODO: schedule this 2 minutes after 'last_checkin'
			system['action_id'] = client.system.schedule_script_run(key, system['id'], "root", "root", 14400, action_script, system['last_checkin'])
			system['complete'] = False
		except:
			print RED + "! Error trying to execute script on %s" % system['name'] + ENDC
			system['skip'] = True
			if options.debug: raise
			continue

	return systems

def minutes(iterations, ticks):
	'''Returns number appropriate to the number of ticks in minutes'''
	return iterations * (60 / ticks)

def get_action_results(key, systems):
	'''Gets action results that have been scheduled'''
	time_warn = 5
	time_bail = 121
	complete = False
	waits = 0
	warned_short = False
	warned_long = False

	try:
		while not complete:
			print
			for system in systems:
				if system['skip']: continue
				if not system['complete']:
					if options.verbose: print timestamp(), "Checking system:", system['name']
					script_result = client.system.get_script_results(key, system['action_id'])
					if options.debug and not script_result == []: 
						print "Script result for %s: %s:" % (system['name'], script_result)
					if not script_result == []:
						if options.debug:
							print "Script result: %s" % script_result
						system['output'] = script_result[0]['output']
						system['return_code'] = script_result[0]['returnCode']
						system['complete'] = True
					else:
						system['complete'] = False
						if options.verbose: print timestamp(), "  %s not completed yet." % (system['name'])
			complete = True
			for system in systems:
				if system['skip']: continue
				if not system['complete']:
					complete = False
			if not complete:
				# I had a fancy 2nd level for loop, but I wanted the timestamp to refresh.  Feel free to fix
				print "\r", timestamp(), "           waiting for results           ",
				sys.stdout.flush()
				print "\r", timestamp(), "         . waiting for results .         ",
				time.sleep(1)
				sys.stdout.flush()
				print "\r", timestamp(), "       . . waiting for results . .       ",
				time.sleep(1)
				sys.stdout.flush()
				print "\r", timestamp(), "     . . . waiting for results . . .     ",
				time.sleep(1)
				sys.stdout.flush()
				print "\r", timestamp(), "   . . . . waiting for results . . . .   ",
				time.sleep(1)
				sys.stdout.flush()
				print "\r", timestamp(), " . . . . . waiting for results . . . . . ",
				time.sleep(1)
				ticks = 5		# This is how many seconds have passed, roughly
				if waits > minutes(time_bail, ticks):
					if not warned_long:
						print "\r", "Warning: Process is taking too long, moving on."
						warned_long = True
						break
				elif waits > minutes(time_warn, ticks):
					if not warned_short:
						still_running = []
						for sys_to_check in systems:
							if not sys_to_check['complete']:
								still_running.append(sys_to_check['name'])
						print "\r", "Warning: Process is taking long, check the following systems: %s" % still_running
						print "     - Are the systems configured for remote acctions (rhn-actions-control --enable-run)?"
						print "     - Is 'osad' started on the systems?"
						print "     - Is the system on, reachable on the network, and allow connections from %s?" % options.satserver
						print "     - You can run 'rhn_check' on the systems to force a check-in."
						print "Ctrl+C will abort this waiting. (default wait time: %i minutes)" % time_bail
						warned_short = True
				waits += 1
	except KeyboardInterrupt:
		print "\nInfo: KeyboardInterrupt detected, moving on."

	for system in systems:
		system['no_child'] = False
		if system['skip'] or not system['complete']: continue
		data = system['output'].split('\n')
		if options.debug: print "Raw output from %s script: %s" %(system['name'], data)
		for line in data:
			if options.debug: print " %s checking '%s'" % (system['name'], line)
			if 'System ID:' in line:
				if options.debug: print "+ Found system_id %s for %s" % (line.split()[-1], system['name'])
				system['system_id'] = line.split()[-1].lower()
				break
		else:
			system['system_id'] = 0		# invalid
			print RED + "! Error running remote actions on %s" % system['name'] + ENDC
	print
	for system in systems:
		if system['skip'] or not system['complete'] or system['system_id'] == 0: continue
		if options.verbose: print "System ID for %s is: %s" % (system['name'], system['system_id'])
		new_channel = DELL_INFO['label'] + '-' + SYSTEM_VENDOR_ID + '.dev_' + system['system_id'] + '-' + system['base_channel']
		system['system_channel'] = new_channel
		if options.verbose: print "  Subscribing %s to channel %s" % (system['name'], system['system_channel'])
		if not subscribe(key, system['base_channel'], system['system_channel'], system['id'], system['name']):
			system['no_child'] = True
	return systems

def show_client_results(systems):
	skipped = []
	completed = []
	no_child = []
	not_completed = []
	for system in systems:
		if system['skip']: 
			skipped.append(system['name'])
		elif system['no_child']:
			no_child.append(system['name'])
		elif system['complete']:
			completed.append(system['name'])
		else:
			not_completed.append(system['name'])
	if completed == []:
		print "! No systems were successfully completed!"
	else:
		print "Completed: %s" % completed
	if not skipped == []:
		print "Skipped: %s" % skipped
	if not no_child == []:
		print "No system-specific channel: %s" % no_child
	if not not_completed == []:
		print "Not completed: %s" % not_completed

def main():
	# Check RHN version to ensure minimum compatibiity
	if client.api.get_version() < 5.1:
		print RED + "This script uses features not available with Satellite versions older than 5.1" + ENDC
		sys.exit(1)

	# Login to Satellite server
	key = client.auth.login(options.user, options.password)

	# Server actions
	if options.server_actions_only:
		# Build existing parent channel list
		current_channels = client.channel.list_all_channels(key)
		current_channel_labels = []
		for channel in current_channels:
			current_channel_labels.append(channel['label'])

		# Build only_systems array
                if options.all_systems:
                        only_systems = listall()
		elif not options.only_systems == []:
			only_systems = []
			for system in options.only_systems.split(','):
				if not system == '':
					only_systems.append(system.lower())
		else:
			only_systems = []

		# Build list based on --only-systems (if any) and add 'platform_independent'
		# No need to build out system list if we're deleting channels
		if not options.delete:
			systems = build_system_list(SYSTEM_VENDOR_ID, only_systems)
			systems['platform_independent'] = PLATFORM_INDEPENDENT

		# Build supported channel list based on --channel
		SUPPORTED_CHANNELS = build_supported_channels(options.channel)

		# Iterate through list of supported OS versions and archs, create parent channels if needed
		channels = {}
		for parent in SUPPORTED_CHANNELS:
			print "\nChecking base channel '%s'" % parent
			# Check each supported base channel, skip if it does not exist on Satellite server
			if parent not in current_channel_labels:
				print "Channel '%s' not found, skipping." % parent
				continue
			else:
				print "Channel '%s' found." % parent
				# Ask if we want to delete channels, and then keep going through loop (continue)
				if options.delete:
					for channel in current_channels:
						# Get list of relevant channels that do not have any systems associated with it
						if 'dell-om-' in channel['label'] and parent in channel['label'] and channel['systems'] == 0:
							delete_channel(key, channel['label'])
							# Remove repo associated with channel - repo has same name as channel
		                                        # and there is only one repo per channel so ok to use here. Doing this
							# way because of issue with older versions of Spacewalk (RHN).
							try:
								client.channel.software.removeRepo(key, channel['label'])
							except:
								print RED + "  ! Error removing repo:", channel['name'] + ENDC
								raise
					continue

				channels[parent] = SUPPORTED_CHANNELS[parent]
				channels[parent]['child_channels'] = []		# Initialize key for child channels

			if channels[parent]['arch'] == 'i386':
				# This is because x86 is referenced as 'ia32'
				arch = 'channel-ia32'
			else:
				arch = 'channel-' + channels[parent]['arch']
			subdir = channels[parent]['subdir']
			
			# If a channel already exists, then I skip it, even if there are zero packages in it. Is that a good idea?
			for system in systems:
				# use system name plus parent to create a unique child channel
				c_label = DELL_INFO['label'] + '-' + system + '-' + parent
				c_name = DELL_INFO['name'] + ' on ' + systems[system] + ' for ' + parent
				c_summary = DELL_INFO['summary'] + ' on ' + systems[system] + ' running ' + parent
				c_arch = arch
				channels[parent]['child_channels'].append(system)

				# Build Repo URL
				url = repo_url + systems[system] + "/" + subdir
				# Check if repo location exists. Some repos (RHEL 6 x86 for example) are not supported
				if check_url(url) == False:
					print BOLD + "  Repo requested '%s' does not exist." % url + ENDC
					continue

				print "  Checking child channel '%s'" % c_name
				if channel_exists(key, c_label, current_channels):
					print BOLD + "  Channel found, skipping." + ENDC
				else:
					# Create channel & repo, associate repo to channel, and schedule repo sync
					# Note that label for channel and repo is the same (c_label)
					error = False
					if options.verbose: print "  Creating channel..."
					repo_id = create_channel(key, c_label, current_channel_labels, c_name, c_summary, c_arch, parent)

					if options.verbose: print "  Creating repo for channel..."
					try:
						client.channel.software.createRepo(key, c_label, "yum", url)
					except:
						print RED + "  Problem with creating repo %s" % c_label + ENDC
						error = True
						if options.debug: raise

					if options.verbose: print "  Associating repo to channel..."
					try:
						client.channel.software.associateRepo(key, c_label, c_label)
					except:
						print RED + "  Problem with associating repo %s" % c_label + ENDC
						error = True
						if options.debug: raise

					if options.verbose: print "  Scheduling repo sync..."
					try:
						client.channel.software.syncRepo(key, c_label)
					except:
						print RED + "  Problem with syncing repo %s" % c_label + ENDC
						error = True
						if options.debug: raise

					if error == True:
						# Remove repo (if created) and channel to keep things clean 
						client.channel.software.removeRepo(key, c_label)
						delete_channel(key, c_label)
						print
					else:
						print GREEN + "  Channel '%s' created." % c_name + ENDC

	# Client actions
	if options.client_actions_only:
		print "\nSubscribing clients to the '%s' channel:" % (PLATFORM_INDEPENDENT)
		client_systems = subscribe_clients(key)
		print "\nScheduling package installation and actions on clients:"
		client_systems = schedule_actions(key, client_systems)
		print "\nWaiting for client actions to complete..."
		client_systems = get_action_results(key, client_systems)
		show_client_results(client_systems)

	# Logout of the Satellite server
	client.auth.logout(key)

if __name__ == "__main__":
	main()
