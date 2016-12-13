#!/usr/bin/env python

print """This program bridges the output of terraform apply to ansible playbook.
You will need to have the .pem file in the same directory as this program."""

from subprocess import Popen, PIPE, call
import os
import json
import paramiko
from paramiko import *
import socket
import time
import argparse

run_book = False
pem = "/aws/kafka_key_pair.pem"
interval = 5

def get_args():
    parser = argparse.ArgumentParser(
        prog = 'bridge.py',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description = testwrap.dedent("""\
                                      This program bridges the output of terraform apply to ansible playbook.
                                      """))


    parser.add_argument("--terra_target", "-t", action = "store", default = "",
                        dest = "terra_target",
                        help = "The target directory for the Terraform *.tf files, default current directory.")

    parser.add_argument("--no_apply", "-n", action = "store_true", default = False,
                        dest = "no_apply",
                        help = "If this flag is set, Terraform will not apply, only output. Default apply.")

    parser.add_argument("--format", "-f", action = "store", default = "public_dns",
                        dest = "format",
                        help = """Sets the output format of Terraform, possible values (default public_dns):
                        public_dns, private_dns, public_ip, private_ip""")

    parser.add_argument("--book", "-b", action = "store", default = "", required = True,
                        dest = "book",
                        help = "Full path of the ansible playbook.")

    parser.add_argument("--key_file", "-k", action = "store", default = "",
                        dest = "key_file",
                        help = "Full path of the identity file for connecting to instances, (.pem)")

    parser.add_argument("--var", "-v", action = "store", default = "",
                        dest = "var",
                        help = "Same as --extra-vars for ansible-playbook")


    return parser


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

def run_playbook( book, hosts, key = "", var=""):
    cmd = "export ANSIBLE_HOST_KEY_CHECKING=false; ansible-playbook --verbose %s -i %s"%(book, hosts)
    if key != "":
        cmd = cmd + " --private-key=%s "%key
    if var != "":
        cmd = cmd + " --extra-vars " + '"%s"'%var
    print cmd
    os.system(cmd)


def main():
    p = get_args()

    out_str = ""
    state = ""
    directory = p.terra_target
    if directory != "":
        state  = "-state=%s/*.tfstate"%directory
    book = p.book
    key_file = p.key_file
    var = p.var


    if not p.no_apply:
        error, t_output = cmdline("terraform apply %s"%directory)
        if error == "":
            print("[Terraform msg]:\n%s"%t_output)
            print "Applied, processing output."

            out_str = cmdline("terraform output -json %s"%state)[1]
            run_book = True
        else:
            print("[Terraform msg]:\n%s"%t_output)
            print("[Terraform error]:\n%s"%error)
            run_book = False
    else:
        error, out_str = cmdline("terraform output -json")
        if error == "":
            print("[Terraform output]:\n%s"%t_output)
            run_book = True
        else:
            print("[Terraform msg]:\n%s"%t_output)
            print("[Terraform error]:\n%s"%error)
            run_book = False


    if run_book:
        print out_str
        out_json = json.loads(out_str)

        print("hosts: \n%s"%out_json["public_dns"]["value"])
        hosts = out_json["public_dns"]["value"]
        #test_ssh_availability(hosts)

        if hosts != []:
            hosts_str = ",".join(hosts)
            run_playbook(book, hosts_str, key_file, var)


if __name__ == "__main__":
    main()
