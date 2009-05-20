#!/usr/bin/env python
import os, sys, subprocess

lang = sys.argv[1]

print "Running format for %s with corrections" % lang

mo_file = 'locale/%s/LC_MESSAGES/django.mo' % lang
po_file = 'locale/%s/LC_MESSAGES/django.po' % lang


#subprocess.Popen(["msgfmt", "--check-format", "-o", mo_file, po_file], stderr=subprocess.STDOUT).communicate()[0]


print "Reading output file for lang %s " % lang

f = open("%s.out" % lang)

po = open(po_file)

source = {}

count = 1

fixed_source = []
begin_errors = {}
end_errors = {}

for l in f:
    try:
        (file, line, error)  = l.split(':')
    except ValueError:
        continue
    if "do not both begin " in error:
        begin_errors[int(line)] = 1
    if "do not both end " in error:
        end_errors[int(line)] = 1


count = 1
for l in po:
    source_line = l
    if count in begin_errors:
        print "Correcting %s" % source_line
        source_line = source_line.replace('msgstr "', 'msgstr "\\n')

    if count in end_errors:
        source_line  = source_line.strip()[:-1]
        source_line = source_line + '\\n"\n'
    fixed_source.append(source_line)
    count += 1

fixed_po_file = open('locale/%s/LC_MESSAGES/django-fixed.po' % lang, 'w')

for l in fixed_source:
    fixed_po_file.write(l)




