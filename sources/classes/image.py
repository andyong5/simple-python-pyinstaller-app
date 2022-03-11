import os
import subprocess
import re
#import pexpect
import time
import pexpect
import urllib3
urllib3.disable_warnings()


class Image:
    def __init__(self, DUTIP, path, IP, user, passwd, prompt, type):
        self.DUTIP = DUTIP
        self.path = path
        self.IP = IP
        self.user = user
        self.passwd = passwd
        self.prompt = prompt
        self.type = type
        self.folder = None
        self.name = None
        self.auth_name = None
        self.date = None
        self.date_reg = "[0-9]{4}_[0-9]{2}_[0-9]{2}_sdk"
        self.is_found = False
        self.success_upgrade = False
        self.version = None

    def get_image(self):
        ### get latest image version ###
        os.system("ssh-keygen -f " +
                  "$HOME/.ssh/known_hosts " + "-R " + self.IP)
        SSH = 'ssh ' + self.user + '@' + self.IP + ' -o StrictHostKeyChecking=no'
        child = pexpect.spawn(SSH, timeout=120)
        child.expect('(?i)Password')
        child.sendline(self.passwd)
        child.expect(self.prompt)
        child.sendline("cd " + self.path)
        child.expect(self.prompt)
        child.sendline("ls -td -- */ | head -n 1")
        child.expect(self.prompt)
        folder = re.search(self.date_reg, str(child.before))
        self.date = subprocess.check_output(['date', '+%Y_%m_%d'])
        if folder is not None:
            folder = folder.group(0)
            child.sendline("cd " + folder)
            child.expect(self.prompt)
            child.sendline("ls -1")
            child.expect(self.prompt)
            tmp = str(child.before, encoding="ascii")
            child.close()

            self.auth_name = re.search(
                r"[\d]*.[\d]*.[\d]*.[\d]*_auth.dat", tmp)
            # will make this better later if there are more
            if self.type == "K2":
                self._get_k2_image(folder, tmp)
            elif self.type == "tp4100":
                self._get_tp4100_image(tmp)
        else:
            print("could not find")

    def _get_k2_image(self, folder, tmp):
        self.name = re.search(r"SyncServer6x0_v5.*bin", tmp)
        if self.name is not None and self.auth_name is not None:
            fw = re.search(r"[\d]+.[\d]+.[\d]+.[\d]*", self.auth_name.group(0))
            if fw is not None:
                fw = fw.group(0)
                self.name = self.name.group(0)
                self.auth_name = self.auth_name.group(0)
                tmp = "scp -o StrictHostKeyChecking=no " + str(self.user) + "@" + str(self.IP) + ":" + str(
                    self.path) + str(folder) + "/{" + str(self.name) + "," + str(self.auth_name) + "} ."
                child = pexpect.spawn(tmp)
                child.expect('(?i)Password')
                child.sendline(self.passwd)
                time.sleep(20)
                print('Auth_file_name = ' + self.auth_name +
                      ". Image Name = " + self.name + '.')
                # Get version number from auth file
                search = re.search(".+?(?=_)", self.auth_name)
                self.version = search.group()
                self.is_found = True
        else:
            print("error in getting K2 image")

    def _get_tp4100_image(self, tmp):
        self.name = re.search(r"TimeProvider4100_v.*bin", tmp)
        if(self.name != None and self.auth_name != None):
            fw = re.search(r"[\d]+.[\d]+.[\d]+.[\d]*", self.auth_name.group(0))
            if(fw != None):
                fw = fw.group(0)
                self.name = self.name.group(0)
                self.auth_name = self.auth_name.group(0)
                print(self.name + " " + self.auth_name)
                self.is_found = True
        else:
            print("error in getting TP4100 image")

    def upgrade(self):
        if self.type == "tp4100":
            self._upgrade_tp4100()

    def _upgrade_tp4100(self):
        os.system("ssh-keygen -f " +
                  "$HOME/.ssh/known_hosts " + "-R " + self.DUTIP)
        SSH = 'ssh ' + self.user + '@' + self.DUTIP + ' -o StrictHostKeyChecking=no'
        child = pexpect.spawn(SSH, timeout=90)
        child.expect('(?i)Password')
        child.sendline(self.passwd)
        child.expect(self.prompt)
        child.sendline("show status")
        child.expect(self.prompt)
        child.sendline("show image")
        child.expect(self.prompt)
        ImageStr = re.search("Active Image Version.*", str(child.before))
        if ImageStr is not None:
            upgrade = "upgrade imagefilepath " + \
                str(self.path) + str(self.folder) + '/' + str(self.name) + ' '
            auth = "authfilepath " + \
                str(self.path) + str(self.folder) + '/' + str(self.auth_name)
            scp = " scp:" + str(self.IP) + " " + str(self.user)
            clicmd = upgrade + auth + scp
            # print(clicmd)
            child.sendline(clicmd)
            child.expect('(?i)Password')
            child.sendline(self.passwd)
            child.expect('Please Confirm')
            child.sendline('yes')
            time.sleep(900)
            child.close()
            return True
        else:
            print("Error couldn't get image #")
            return False

    def check_version(self, software_version):
        if self.type == "tp4100" or "tp4100v2":
            software_version = self._check_tp4100_image()
        version = re.search(r"[\d]+\.[\d]+\.[\d]+\.*[\d]*", str(self.name))
        if version is not None and software_version is not None:
            version = version.group(0)
            if version == software_version:
                print("Software matches")
                return True
            else:
                return False

    def _check_tp4100_image(self):
        os.system("ssh-keygen -f " +
                  "$HOME/.ssh/known_hosts " + "-R " + self.DUTIP)
        SSH = 'ssh ' + self.user + '@' + self.DUTIP + ' -o StrictHostKeyChecking=no'
        child = pexpect.spawn(SSH, timeout=90)
        child.expect('(?i)Password')
        child.sendline(self.passwd)
        child.expect(self.prompt)
        child.sendline('show image')
        child.expect(self.prompt)
        tmp = str(child.before, encoding="ascii")
        software_version = re.search(
            r"Active Image Version.*[\d]+\.[\d]+\.[\d]+\.*[\d]*", str(tmp))
        if software_version is not None:
            return re.search(r"[\d]+\.[\d]+\.[\d]+\.*[\d]*", str(software_version))

    def _get_login_info(self):
        if self.type == 'tp4100':
            user = 'testuser'
            Prompt = 'TimeProvider:'
            passwd = 'Microsemi**'
            root_pass = 'tp!a6Qbv.'
        elif self.type == 'k2' or self.type == 'K2':
            user = 'testuser'
            Prompt = 'SyncServer:'
            passwd = 'Microsemi**'
            root_pass = 'K22Sxxx!.'
        else:
            user = None
            Prompt = None
            passwd = None
            root_pass = None
        return user, Prompt, passwd, root_pass

    def _connect(self):
        try:
            print("Running script on machine " + str(self.IP))
            user, Prompt, passwd, root_pass = self._get_login_info()
            if user is None:
                print("Failed to get login info")
                return False, Prompt
            SSH = 'ssh ' + user + '@' + self.DUTIP + ' -o StrictHostKeyChecking=no'
            os.system("ssh-keygen -f " + "$HOME/.ssh/known_hosts " +
                      "-R " + self.DUTIP + " >/dev/null 2>&1")
            child = pexpect.spawn(SSH, timeout=300)
            child.expect('(?i)Password')
            child.sendline(passwd)
            child.expect(Prompt)
            child.sendline('su')
            child.expect('(?i)Password')
            child.sendline(root_pass)
            child.expect(Prompt)
            return child, Prompt
        except:
            print("Failed to login to machine")
            return False, Prompt

    def _create_gateway_ip(self):
        IPtmp = re.split('[.]', str(self.DUTIP))
        IPtmp = str(IPtmp[0]) + '.' + str(IPtmp[1]) + \
            '.' + str(IPtmp[2]) + '.' + "1"
        return IPtmp

    def ping_gateway(self):
        for i in range(0, 5):
            child, Prompt = self._connect()
            print("LOOP = " + str(i))
            if (child == 0):
                return False
            IP_GW = self._create_gateway_ip()
            child.sendline("ping " + str(IP_GW) + " -c 4")
            child.expect(Prompt)
            result = re.search(", 0% packet loss", str(child.before))
            if(result == None):
                print("packets missing")
                return False
            else:
                print("All packets found")
            time.sleep(5)
        child.close
        return True
