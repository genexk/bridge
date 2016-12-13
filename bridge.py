#!/usr/bin/env python

print """This program bridges the out of terraform apply to ansible playbook.
You will need to have the .pem file in the same directory as this program."""

from subprocess import Popen, PIPE, call
import os
import json
import paramiko
from paramiko import * 
import socket
import time 
run_book = False
pem = "/aws/kafka_key_pair.pem"
interval = 5




def cmdline(cmd):
  process = Popen([cmd], stdout=PIPE, stderr=PIPE, shell=True)
  stdout, stderr  = process.communicate()
  return [stderr, stdout]

def test_ssh_availability(hosts):
  ssh = paramiko.SSHClient()
  ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  failed = True
  while failed:
    try:
      for host in hosts:
        ssh.connect(host, username = "ec2-user", key_filename = pem)
        print("%s: success"%host)
      failed = False
      print "All hosts are Ready!"
    except (BadHostKeyException, AuthenticationException, 
        SSHException, socket.error) as e:
      print "%s: failed...\n%s\nRetry in 5 seconds..."%(host, e)
      time.sleep(interval)

def run_playbook( book, hosts, key, var=""):
  cmd = "export ANSIBLE_HOST_KEY_CHECKING=false; ansible-playbook --verbose --private-key=%s %s -i %s"%(key, book, hosts)
  print cmd
  os.system(cmd) 



error = cmdline("terraform apply")[0]
if error == "":
  print "Applied, processing output."

  out_str = cmdline("terraform output -json")[1] 
  run_book = True
else:
  print "The error is: \n%s"%error
  run_book = False

if run_book:
  print out_str
  out_json = json.loads(out_str) 
  print("hosts: \n%s"%out_json["public_dns"]["value"]) 
  hosts = out_json["public_dns"]["value"]
  #test_ssh_availability(hosts)
  hosts_str = ",".join(hosts)
  run_playbook("test.yml", hosts_str, pem)



