#!/usr/bin/env python
#
# scsicheck -- Read message(s)-file(s) and produce a basic
# analysis of encountered SCSI errors on disks and/or tape
# devices
#
#   Cris van Pelt
#
# Usage:
#    scsicheck [MESSAGE FILES..]
#
#  Multiple messages files can be specified, in any order.
#
#  If no arguments are given scsicheck will read from standard
#  input.
#
#  NOTE: NO distinction is made between nodes.  Do NOT use
#        this script on the logs produced by a central
#        loghost.
#

#  This script will:
#
#    * Check for any type of SCSI error (retryable, fatal, informational, etc)
#    * Inform of 'Drive operation marginal' if firmware has reported it.
#    * Check for changes in disk serial number.
#    * Give a breakdown of errors per block.
#    * Give a breakdown of the firmware sense key information.
#

# Version      : 1.0b6 (Deep Space Filius Edition)
# Last modified: 2008-01-03  15:41:44 CET
#
# Changes:
#    * 1.0b: FrIST PSOT!!!!!
#    * 1.0b2: Clean-up (ahem); fix 'last reported time' for operation marginal
#    * 1.0b3: Add handling for 'disk not responding to selection'; Fix bug in
#      time-parsing.
#    * 1.0b4: Add handling for 'i/o to invalid geometry'; Fixed a typo which
#      stopped the script from parsing.  Oops.
#    * 1.0b5: Rewrote the whole thing in Python, added generic handling for
#      ASC/ASCQ codes.  A listing for those was added to the device summary.
#      Also shows device serial number in the summary now.
#    * 1.0b6: Allowed for messages without indication of error blocks or diag
#      level.
#

import sys
import re

disks = dict()
d = dict()
lines = 0

if len(sys.argv) < 2:
	sys.argv += '-'

for arg in sys.argv[1:]:

	if arg == '-':
		f = sys.stdin
	else:
		try:
			f = open(arg, "r")
		except IOError, (errno, strerror):
			print >> sys.stderr, 'Failed to open file:',arg,':',strerror

	for line in f:
		lines += 1

		m = re.search('WARNING:.*?(\/.*?) \((s+[dt][0-9]+)',line)
		if m:
			disks.setdefault(m.group(2), dict())

			d = disks[m.group(2)]

			d['devicepath'] = m.group(1)
			d['device'] = m.group(2)
			d.setdefault('errorcount', 0)

			d['errorcount'] += 1

		m = re.search('Error Level: +(.*)$', line)
		if m:
			levels = d.get('levels',dict())
			levels.setdefault(m.group(1), 0)

			levels[m.group(1)] += 1

			d['levels'] = levels

		m = re.search('Sense Key: +(.*)$', line)
		if m:
			sensekey = d.get('sensekey',dict())

			sensekey.setdefault(m.group(1), 0)
			sensekey[m.group(1)] += 1

			d['sensekey'] = sensekey
			skey = m.group(1)

		m = re.search('ASC: 0x([^ ]+) \((.*)\), ASCQ: 0x([^ ,]+)', line)
		if m:
			event = { 'asc': m.group(1), 'string': m.group(2), 'ascq': m.group(3), 'sense': skey}

			d.setdefault('events', ())
			if not event in d['events']:
				d['events'] += (event,)

		m = re.search('Serial Number: +(.*)$', line)
		if m:
			d.setdefault('serial', m.group(1))

		m = re.search('Error Block: *([0-9]+)', line)
		if m:
			blocks = d.get('blocks',dict())

			blocks.setdefault(m.group(1), 0)
			blocks[m.group(1)] += 1

			d['blocks'] = blocks

		m = re.search('([A-Z][a-z]{2} [0-9 ][0-9] .*?[0-9]+ ).*disk not responding to selection', line)
		if m:
			d.setdefault('noresponse', 1)
			d.setdefault('noresponsetime', m.group(1))

		m = re.search('([A-Z][a-z]{2} [0-9 ][0-9] .*?[0-9]+ ).*drive operation marginal', line)
		if m:
			d.setdefault('marginal', 1)
			d.setdefault('marginaltime', m.group(1))

		m = re.search('([A-Z][a-z]{2} [0-9 ][0-9] .*?[0-9]+ ).*i\/o to invalid geometry', line)
		if m:
			d.setdefault('invalidgeo', 1)
			d.setdefault('invalidgeotime', m.group(1))

		if 'device' in d:
			disks[d['device']] = d

	if f != sys.stdin:
		f.close()

for k in disks:
	print
	print '=============  Device:',k,'(',disks[k]['devicepath'],') ============='
	if 'blocks' in disks[k]:
		print '%-15s %-15s %15s' % ('Block', "Count", "Percentage")

		keys = disks[k]['blocks'].keys()
		keys.sort()

		for b in keys:
			print '%-15s %-15s %15.2f%%' % (b, disks[k]['blocks'][b], float(disks[k]['blocks'][b])/float(disks[k]['errorcount']) * 100.0);
	else:
		print
		print "No error blocks indicated for this device!"


	print
	print "=============== DEVICE SUMMARY ====================";
	print
	print "---- Report for device %s (%s) [s/n: %s]--" % (k, disks[k]['devicepath'], disks[k].get('serial', 'unknown'))
	print
	print "     Total errors for device %s: %d" % (k, disks[k]['errorcount'])

	if 'marginal' in disks[k]:
		print "     !!! WARNING: Drive", k, "operation marginal last reported at ", disks[k]['marginaltime']
	if 'noresponse' in disks[k]:
		print "     !!! WARNING: Drive", k, "not responding to selection last reported at ", disks[k]['noresponsetime']
	if 'invalidgeo' in disks[k]:
		print "     !!! WARNING: Drive", k, "last reported I/O to invalid geometry at ", disks[k]['invalidgeotime']

	if 'levels' in disks[k]:
		for l in disks[k]['levels']:
			print '     %s errors for device %s: %d' % (l, k, disks[k]['levels'][l])

	if 'events' in disks[k]:
		print
		print '     Unique ASC/ASCQ codes:'
		for event in disks[k]['events']:
			print '        0x%2s/0x%-2s -> "%s" (%s)' % (event['asc'], event['ascq'], event['string'], event['sense'])

print
print 'Log lines analyzed:', lines
