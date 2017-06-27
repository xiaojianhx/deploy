#! /usr/bin/python

import paramiko
import os
import time
import sys
import configparser
import urllib  
import urllib.request

from utils import SSHConnection

class Deploy:
    
    __config_file = ''

    def __init__ (self, config_file):
        self.__config_file = config_file

    def deploy(self):
        start = int(round(time.time() * 1000))

        CONFIG_SECTIONS_GLOBAL = 'global'
        CONFIG_SECTIONS_LOCAL = 'local'
        CONFIG_SECTIONS_REMOTE = 'remote'

        NOW = time.strftime('%Y%m%d_%H%M%S')

        print ('loading config file:', self.__config_file)
        config = configparser.ConfigParser()
        config.read(self.__config_file)
        print ('loading config file success!')

        # global
        PROJECT_NAME = config.get(CONFIG_SECTIONS_GLOBAL, 'project_name')
        ENV = config.get(CONFIG_SECTIONS_GLOBAL, 'env')

        # local
        LOCAL_PROJECT_DIR = config.get(CONFIG_SECTIONS_LOCAL, 'project_dir')
        SRC = LOCAL_PROJECT_DIR + '/target/ROOT.war'

        # remote
        REMOTE_HOSTNAME = config.get(CONFIG_SECTIONS_REMOTE, 'hostname')
        REMOTE_PORT = config.getint(CONFIG_SECTIONS_REMOTE, 'port')
        REMOTE_USERNAME = config.get(CONFIG_SECTIONS_REMOTE, 'username')
        REMOTE_PASSWORD = config.get(CONFIG_SECTIONS_REMOTE, 'password')

        REMOTE_DB_USERNAME = config.get(CONFIG_SECTIONS_REMOTE, 'db_username')
        REMOTE_DB_PASSWORD = config.get(CONFIG_SECTIONS_REMOTE, 'db_password')
        REMOTE_DB_PORT = config.get(CONFIG_SECTIONS_REMOTE, 'db_port')
        REMOTE_DB_NAME = config.get(CONFIG_SECTIONS_REMOTE, 'db_name')

        TMP_DIR = config.get(CONFIG_SECTIONS_REMOTE, 'tmp_dir')
        BAK_DIR = config.get(CONFIG_SECTIONS_REMOTE, 'bak_dir')
        BAK_DB_DIR = BAK_DIR + '/db'
        BAK_APP_DIR = BAK_DIR + '/app'

        TOMCAT_HOME = config.get(CONFIG_SECTIONS_REMOTE, 'tomcat_home')
        APP_TEST_URL = config.get(CONFIG_SECTIONS_REMOTE, 'app_test_url')

        KEY_MAVEN_HOME = 'MAVEN_HOME'
        MAVEN_HOME = os.getenv(KEY_MAVEN_HOME)

        if (MAVEN_HOME == None):
            print ('没有配置环境变量[' + KEY_MAVEN_HOME + ']')
            os._exit(0)

        # 本地打包
        cmd = MAVEN_HOME + '/bin/mvn -f' + LOCAL_PROJECT_DIR + '/pom.xml package -Denv=' + ENV + ' -Dmaven.test.skip=true -q'
        print ('Running local command:', cmd)
        os.system(cmd)
        print ('Running local command success, file path:', SRC)

        # 建立远程连接
        ssh = SSHConnection.SSHConnection(REMOTE_HOSTNAME, REMOTE_PORT, REMOTE_USERNAME, REMOTE_PASSWORD)
        ssh.SSHClient()

        # war包上传
        ssh.upload(SRC, TMP_DIR + '/ROOT.war')

        # 远程数据库备份
        print ('backup database....')
        ssh.exec_command('mysqldump -u' + REMOTE_DB_USERNAME + ' -p' + REMOTE_DB_PASSWORD + ' ' + ' -P' + REMOTE_DB_PORT + ' ' + REMOTE_DB_NAME + ' > ' + BAK_DB_DIR + '/' + NOW + '.sql')
        print ('backup database success')

        # 远程关闭tomcat
        print ('stop tomcat....')
        ssh.exec_command(TOMCAT_HOME + '/bin/shutdown.sh')
        print ('stop tomcat success')

        print ('kill process....')
        ssh.exec_command('ps -ef | grep ' + TOMCAT_HOME + ' | grep -v grep | awk \'{print $2}\' | xargs kill -15')
        print ('kill process success')

        # 远程备份应用
        print ('backup webapp....')
        ssh.exec_command('cp -r ' + TOMCAT_HOME + '/webapps/ROOT ' + BAK_APP_DIR + '/' + NOW)
        print ('backup webapp success')

        # 远程删除工程
        print ('remove project....')
        ssh.exec_command('rm -rf ' + TOMCAT_HOME + '/webapps/ROOT*')
        print ('remove project success')

        # 远程清空缓存
        print ('remove work....')
        ssh.exec_command('rm -rf ' + TOMCAT_HOME + '/work')
        print ('remove work success')

        # 远程移动war到tomcat下
        print ('mv war....')
        SRC = TMP_DIR + '/ROOT.war'
        DST = TOMCAT_HOME + '/webapps/'
        ssh.exec_command( 'mv %s %s' % (SRC, DST))
        print ('mv war success: %s --> %s' % (SRC, DST))

        # 远程启动tomcat
        print ('start tomcat....')
        ssh.exec_command(TOMCAT_HOME + '/bin/startup.sh')
        print ('start tomcat success')

        # 关闭连接
        ssh.close()

        # 检测是否成功
        print ('connectionning', APP_TEST_URL, '....')
        response = urllib.request.urlopen(APP_TEST_URL)
        print ('connection', APP_TEST_URL, ' http code:', response.getcode())
        if(response.getcode() == 200):
            print ('Success!')
        else:
            print ('Fail !!!')

        end = int(round(time.time() * 1000))

        print ('deploy %s use time %dms.' % (PROJECT_NAME, (end - start)))

if __name__ == '__main__':
    deploy = Deploy((sys.argv[1]))
    deploy.deploy()