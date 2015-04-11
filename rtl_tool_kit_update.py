#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
# 2014 Paul Kinsella <paulkinsella29@yahoo.ie>
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 
import wx
from functions import * 
from sms_functions import * 
from wxPython.wx import *
import serial, time
from datetime import datetime
from subprocess import call
#import subprocess
from subprocess import Popen
import sys
import binascii
import telnetlib
import getpass,socket, select,string
import os
TELNET_HOST = "127.0.0.1"
TELNET_PORT = 7356
CURRENT_PORT = ""
###################################
#	Serial setup
###################################
ser = serial.Serial()
ser.port = "/dev/ttyUSB0" #default so not null
ser.baudrate = 9600
ser.bytesize = serial.EIGHTBITS #number of bits per bytes
ser.parity = serial.PARITY_NONE #set parity check: no parity
ser.stopbits = serial.STOPBITS_ONE #number of stop bits
ser.timeout = 0             #non-block read
ser.xonxoff = False     #disable software flow control
ser.rtscts = False     #disable hardware (RTS/CTS) flow control
ser.dsrdtr = False       #disable hardware (DSR/DTR) flow control

pagecount = 0;
smsSendCount =0;
TMSI = ""
IMSI = ""
KEY = ""
FLASH = "04"
FLASH1 = "10"#4 bit encoding
FLASH2 = "14"#8 bit encoding
FLASH3 = "18"
SILENT = "C0"
NORMAL_TEXT = "04"
AT_COMMANDS = ["AT+CIMI",
"AT+CSIM=14,\"A0A40000027F20\"",
"AT+CSIM=42,\"A088000010FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF\"",
"AT+CSIM=14,\"A0A40000026F20\"",
"AT+CSIM=10,\"A0B0000009\"",
"AT+CSIM=14,\"A0A40000026F7E\"","AT+CSIM=10,\"A0B000000B\""]
ARR_SIZE =  len(AT_COMMANDS)
at_cmds_array = []
at_cmds_array_info = []


gsm = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
"¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà").decode('utf8')
ext = ("````````````````````^```````````````````{}`````\\````````````[~]`"
"|````````````````````````````````````€``````````````````````````") 

class ExampleFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent,size=wxSize(400,650),title="RTL TOOL KIT")

        self.panel = wx.Panel(self,size=wxSize(400,600),style = wx.RAISED_BORDER)
	file = open("at_cmds.txt")
	temparray =[]
	for line in file:
		line = line.rstrip('\n').rstrip('\r')
		temparray = line.split('#')
		at_cmds_array.append(temparray[0])
		at_cmds_array_info.append(temparray[1])
	file.close()


	#***************TIMERS************************
	# timers
	#sms timer to send out msgs every X secound and how many to send by count value
        self.smstimer = wx.Timer(self)
	self.timerStartRtl = wx.Timer(self)
	self.timerKillRtl = wx.Timer(self)
	self.timerFetchTmsi = wx.Timer(self)
	self.sms_single_timer = wx.Timer(self)
	self.delivery_report_wait_timer = wx.Timer(self)

        self.Bind(wx.EVT_TIMER, self.timerSendPDU, self.smstimer)
	self.Bind(wx.EVT_TIMER, self.timerStopRtl, self.timerKillRtl)
	self.Bind(wx.EVT_TIMER, self.timerSingleSendPDU, self.sms_single_timer)
	self.Bind(wx.EVT_TIMER, self.filterTmsiTimestampMode, self.delivery_report_wait_timer)
	#*********************************************


	#***************ARRAYS************************
        gsm_scan_range = ['GSM900', 'GSM850', 'GSM-R', 'EGSM', 'DCS','PCS']
	
	#*********************************************


	#***************BUTTONS***********************
	self.btnautomode = wx.Button(self.panel, label="Automode", pos=(145,55),size=(80,25))
	self.btnexttmsi = wx.Button(self.panel, label="Fetch", pos=(225,55),size=(40,25))
	self.btncleardata = wx.Button(self.panel, label="Clean", pos=(225,80),size=(40,25))

        #buttons 
        self.btnreload = wx.Button(self.panel, label="reload",pos=(5,15),size=(40,20))
        self.btn2g = wx.Button(self.panel, label="2G MODE",pos=(5,40),size=(65,25))
        self.btngetinfo = wx.Button(self.panel, label="<GET INFO",pos=(215,460),size=(60,25))
        self.btnkal = wx.Button(self.panel, label="KAL",pos=(5,65),size=(65,25))

        self.btngqrx = wx.Button(self.panel, label="GQRX",pos=(70,40),size=(65,25))
        self.btngetgqrxfreq = wx.Button(self.panel, label="Get Freq",pos=(70,65),size=(65,25))
        self.btnwireshark = wx.Button(self.panel, label="wireshark",pos=(70,90),size=(65,25))
        self.button = wx.Button(self.panel, label="Send>>",pos=(235,5),size=(60,25))
        self.btntesting = wx.Button(self.panel, label="Testing",pos=(295,5),size=(60,25))
        self.btnsms = wx.Button(self.panel, label="Send",pos=(255,144),size=(40,25))

        self.btnrtl = wx.Button(self.panel, label="Start", pos=(295,370),size=(45,25))
	self.btnrtlstop = wx.Button(self.panel, label="Stop", pos=(340,370),size=(45,25))
	#gsm btns
	self.btngsmstart = wx.Button(self.panel, label="Start", pos=(295,405),size=(45,25))
	self.btngsmstop = wx.Button(self.panel, label="Stop", pos=(340,405),size=(45,25))

	self.btnpdusend = wx.Button(self.panel, label="Send", pos=(300,515),size=(45,25))

	self.btnatstart = wx.Button(self.panel, label="Send Cmd", pos=(185,562),size=(65,25))
	#*********************************************
	
	#***************EDIT FIELDS*******************
	#self.editcomport = wx.TextCtrl(self.panel,value="/dev/ttyUSB0",size=(90,25),pos=(45,600))
        self.editname = wx.TextCtrl(self.panel,value="AT",size=(90,25),pos=(145,5))

	self.editpingrange1 = wx.TextCtrl(self.panel,value="3",size=(25,25),pos=(215,30))
	self.editpingrange2 = wx.TextCtrl(self.panel,value="8",size=(25,25),pos=(270,30))

	self.editoffsetrange1 = wx.TextCtrl(self.panel,value="3",size=(25,25),pos=(270,95))
	self.editoffsetrange2 = wx.TextCtrl(self.panel,value="6",size=(25,25),pos=(325,95))

	self.editdebugtmsi = wx.TextCtrl(self.panel, size=(80,65),value="",pos=(145,80), style=wx.TE_MULTILINE)

	self.gsm_imsi = wx.TextCtrl(self.panel,value="",size=(160,25),pos=(50,460))
	self.gsm_tmsi = wx.TextCtrl(self.panel,value="",size=(160,25),pos=(50,485))
	self.gsm_key = wx.TextCtrl(self.panel,value="",size=(160,25),pos=(50,510))

        #text boxes
        self.editnumber = wx.TextCtrl(self.panel, size=(140, -1),value="*+*+*+*+*+*",pos=(5,140))
        self.editsms = wx.TextCtrl(self.panel, size=(110, -1),value="message",pos=(145,145))
        self.editdebug = wx.TextCtrl(self.panel, size=(380,150),value="Debug Data",pos=(5,185), style=wx.TE_MULTILINE)

	#rtl textboxes
        self.editrtl_filename = wx.TextCtrl(self.panel,value="/tmp/capture.bin",size=(135,25),pos=(5,370))
        self.editrtl_samplerate = wx.TextCtrl(self.panel,value="1.0",size=(45,25),pos=(140,370))
        self.editrtl_freq = wx.TextCtrl(self.panel,value="927.55",size=(65,25),pos=(185,370))
	self.editrtl_gain = wx.TextCtrl(self.panel,value="43",size=(45,25),pos=(250,370))

	#gsm-receiver textboxes
       # self.editgsm_receiver = wx.TextCtrl(self.panel,value="/tmp/capture.bin",size=(140,25),pos=(5,440))
        self.editgsm_samplerate = wx.TextCtrl(self.panel,value="1.0",size=(45,25),pos=(5,430))
        self.editgsm_freq = wx.TextCtrl(self.panel,value="927.55",size=(65,25),pos=(50,430))
	self.editgsm_gain = wx.TextCtrl(self.panel,value="43",size=(45,25),pos=(115,430))
	self.editgsm_channel = wx.TextCtrl(self.panel,value="0B",size=(45,25),pos=(160,430))
	self.editgsm_key = wx.TextCtrl(self.panel,value="0000000000000000",size=(160,25),pos=(205,430))

	self.editpdu_NO = wx.TextCtrl(self.panel,value="123456789012",pos=(275,475),size=(120,20))
	self.editpdu_PDU_SMS = wx.TextCtrl(self.panel,value="Hello",pos=(275,495),size=(120,20))
	self.editpdu_MC = wx.TextCtrl(self.panel,value="2",pos=(275,515),size=(25,25))
	self.editpdu_MD = wx.TextCtrl(self.panel,value="15",pos=(275,540),size=(25,25))
	self.editpdu_MDR = wx.TextCtrl(self.panel,value="15",pos=(355,540),size=(25,25))

	self.editat_cmds = wx.TextCtrl(self.panel,value="43",size=(65,25),pos=(120,562))
	self.lbl_at_data = wx.TextCtrl(self.panel, value="",pos=(5,593),size=(350,50),style=wx.TE_MULTILINE)
	#*********************************************

	#***************LABELS************************
        self.comporttext = wx.StaticText(self.panel, label="Com Port:",pos=(5,5))
        self.result = wx.StaticText(self.panel, label="",pos=(75,5))
        self.lblname = wx.StaticText(self.panel, label="Send Text:",pos=(5,125))
	self.lbdebugoutput = wx.StaticText(self.panel, label="Debug output",pos=(5,170))
	#ping counter data
	self.lbltmsi_sms_count = wx.StaticText(self.panel, label="Tmsi Counter:",pos=(145,30))
	self.lblpingrange = wx.StaticText(self.panel, label="Ping count:",pos=(145,40))
	self.lblpingrange3 = wx.StaticText(self.panel, label=">= <=",pos=(240,35))
	self.lbloffset = wx.StaticText(self.panel, label="Offsets",pos=(290,80))
	self.lbloffsetrange3 = wx.StaticText(self.panel, label=">= <=",pos=(297,100))
	self.lb_smsendcount_text = wx.StaticText(self.panel, label="Sent:",pos=(355,520))

	#rtl text
	self.lblrtl = wx.StaticText(self.panel, label="RTL Record:",pos=(5,335))
	self.lblrtlfile = wx.StaticText(self.panel, label="Filename",pos=(5,350))
	self.lblrtlsamplerate = wx.StaticText(self.panel, label="SR",pos=(145,350))
	self.lblrtlfreq = wx.StaticText(self.panel, label="Freq",pos=(195,350))
	self.lblrtlgain = wx.StaticText(self.panel, label="Gain",pos=(255,350))

	#gsm-receiver text
	self.lblgsm = wx.StaticText(self.panel, label="Gsm Receiver:",pos=(5,395))
	self.lblgsmsamplerate = wx.StaticText(self.panel, label="S",pos=(15,410))
	self.lblgsmfreq = wx.StaticText(self.panel, label="F",pos=(60,410))
	self.lblgsmgain = wx.StaticText(self.panel, label="G",pos=(125,410))
	self.lblgsmchannel = wx.StaticText(self.panel, label="C",pos=(170,410))
	self.lblgsmkey = wx.StaticText(self.panel, label="Key",pos=(215,410))

	#TMSI/IMSI/KEY
	self.lblgsmsamplerate = wx.StaticText(self.panel, label="IMSI:",pos=(5,465))
	self.lblgsmsamplerate = wx.StaticText(self.panel, label="TMSI:",pos=(5,490))
	self.lblgsmsamplerate = wx.StaticText(self.panel, label=" KEY:",pos=(5,515))


	self.lbpdu_NO = wx.StaticText(self.panel, label="Number:",pos=(215,485))
	self.lbpdu_FLASH = wx.StaticText(self.panel, label="Msg Data:",pos=(215,500))
	self.lbpdu_MSGCOUNT = wx.StaticText(self.panel, label="Msg Count:",pos=(215,520))
	self.lbpdu_MSGDELAY = wx.StaticText(self.panel, label="Sms Send\nDelay:",pos=(215,543))
	self.lbpdu_MSG_DEL_DELAY = wx.StaticText(self.panel, label="Del Report\nDelay:",pos=(305,543))
	self.lbl_at_cmd = wx.StaticText(self.panel, label="Misc AT Commands",pos=(5,543))

	#*********************************************



	#**************CHECKBOX + COMBOBOX************
	tested_ports = getOpenSerialPorts()
	if len(tested_ports) < 1:
		tested_ports.append("NO PORTS")

        self.combo_serial_ports = wx.ComboBox(self.panel,size=(95,30), pos=(45,5), choices=tested_ports, style=wx.CB_READONLY)
	self.combo_serial_ports.SetSelection(0)

        self.cbkalrange = wx.ComboBox(self.panel,size=(65,30), pos=(5,90), choices=gsm_scan_range, style=wx.CB_READONLY)
	self.cbkalrange.SetSelection(0)

        self.cbk_at_cmds = wx.ComboBox(self.panel,size=(115,30), pos=(5,560), choices=at_cmds_array, style=wx.CB_READONLY)
	self.cbk_at_cmds.SetSelection(0)
	#pdu boxes
	self.cbsilent = wx.CheckBox(self.panel,-1,'Silent', pos=(280,455))
	self.cbsilent.SetValue(True)
	self.cbflash = wx.CheckBox(self.panel,-1,'Flash', pos=(340,455))

	self.cbkey = wx.CheckBox(self.panel,-1,'', pos=(365,430))
	self.cb_fetch_manual = wx.CheckBox(self.panel,-1,'Manual Mode', pos=(265,55))
	#*********************************************

	#**************BINDS**************************
	
	self.btnexttmsi.Bind(wx.EVT_BUTTON,self.whichTimestamp)
        self.button.Bind(wx.EVT_BUTTON, self.SendCommand)
        self.btn2g.Bind(wx.EVT_BUTTON, self.On2gold)
	#self.btnsms.Bind(wx.EVT_BUTTON, self.debugData)
	self.btnrtl.Bind(wx.EVT_BUTTON,self.StartRtl)
	self.btnrtlstop.Bind(wx.EVT_BUTTON,self.StopRtl)
	self.btnkal.Bind(wx.EVT_BUTTON,self.startKal)
	self.btngqrx.Bind(wx.EVT_BUTTON,self.startStopGqrx)
	self.btnwireshark.Bind(wx.EVT_BUTTON,self.startWireshark)
	self.btnpdusend.Bind(wx.EVT_BUTTON,self.onToggle)
	self.btngetgqrxfreq.Bind(wx.EVT_BUTTON,self.getGqrxFreq)
	self.btncleardata.Bind(wx.EVT_BUTTON,self.clearData)
	self.cbk_at_cmds.Bind(wx.EVT_COMBOBOX,self.atCommandList)
	self.btnatstart.Bind(wx.EVT_BUTTON,self.SendCommandAtCombo)
	self.btntesting.Bind(wx.EVT_BUTTON,self.TestingFuction)
        self.btngetinfo.Bind(wx.EVT_BUTTON, self.GetKeyBtnPress)
	self.btngsmstart.Bind(wx.EVT_BUTTON,self.StartGsmRec)
	self.btngsmstop.Bind(wx.EVT_BUTTON,self.StopGsmRec)
	self.btnautomode.Bind(wx.EVT_BUTTON,self.autoMode)
	self.btnreload.Bind(wx.EVT_BUTTON,self.reloadSerialPorts)
	#*********************************************


	#*****SET FONT SIZE***************************
	font = wx.Font(7, wx.DECORATIVE, wx.ITALIC, wx.NORMAL)

        self.comporttext.SetFont(font)
        self.result.SetFont(font)
	self.btnsms.SetFont(font)
	self.lbltmsi_sms_count.SetFont(font)
	self.lblpingrange.SetFont(font)
	self.lblpingrange3.SetFont(font)
	self.lbloffset.SetFont(font)
	self.lbloffsetrange3.SetFont(font)
        self.lb_smsendcount_text.SetFont(font)
	self.lbpdu_FLASH.SetFont(font)
	self.lbpdu_NO.SetFont(font)
	self.lbpdu_MSGCOUNT.SetFont(font)
	self.lb_smsendcount_text.SetFont(font)
	self.cbkalrange.SetFont(font)
	self.btn2g.SetFont(font)
	self.btngetinfo.SetFont(font)
	self.btnkal.SetFont(font)
	self.btngqrx.SetFont(font)
	self.btngetgqrxfreq.SetFont(font)
	self.btnwireshark.SetFont(font)
	self.button.SetFont(font)
	self.lbdebugoutput.SetFont(font)
	self.lblname.SetFont(font)
	self.comporttext.SetFont(font)
	self.lbpdu_MSGDELAY.SetFont(font)
	self.lbpdu_MSG_DEL_DELAY.SetFont(font)
	self.btnexttmsi.SetFont(font)
	self.btncleardata.SetFont(font)
	self.cb_fetch_manual.SetFont(font)
	self.lbl_at_data.SetFont(font)
	self.btnatstart.SetFont(font)
	self.btnreload.SetFont(font)

	#*********************************************
        self.result.SetForegroundColour(wx.RED)

    def TestingFuction(self,event):

		self.editdebug.AppendText(self.combo_serial_ports.GetValue())
		#openports = getOpenSerialPorts()
		#for port in openports:
		#	self.editdebug.AppendText(port+"\n")

		#low_range = int(self.editpingrange1.GetValue())
		#high_range = int(self.editpingrange2.GetValue())
		#sTmsiArray,iTmsiCount = getTmsiCount()
		#x = 0
		#for tmsi in sTmsiArray:
		#	#print(tmsi)
		#	if iTmsiCount[x] >= low_range and iTmsiCount[x] <= high_range:
		#		#print(tmsiarray[x]+":"+str(tmsiarraycount[x]))
		#		self.editdebug.AppendText(sTmsiArray[x]+":"+str(iTmsiCount[x])+'\n')
		#	x += 1
	 
    def reloadSerialPorts(self,event):
		self.combo_serial_ports.Clear()
		self.combo_serial_ports.AppendItems(getOpenSerialPorts())
		
    def atCommandList(self,event):
		self.lbl_at_data.SetValue(at_cmds_array_info[self.cbk_at_cmds.GetCurrentSelection()])



 
    def whichTimestamp(self,event):
		if self.cb_fetch_manual.GetValue() != True:
			self.filterTmsiTimestampMode(event)#USB MODEM DELIVERY REPORTS MODE TIMESTAMPS
		else:
			self.filterTmsiTimestampManMode(event)#PHONE MODE MANUAL TIMESTAMPS
    ############################################################################
    #	THIS CODE FILTERS OUT TMSI FROM TIMESTAMP RANGE WITH BUTTON PRESS
    #			USB MODEM MODE
    ############################################################################
    def filterTmsiTimestampMode(self,event):
	    #ser.close()
	    #ser.port = self.editcomport.GetValue()
	    #ser.open()
	    self.delivery_report_wait_timer.Stop()
            time.sleep(0.2)
	    times = []
	    selected_port = self.combo_serial_ports.GetValue()
	    times = getDeliveryTimeStamps(selected_port)#input serial port address
		#print("Response "+ress)
	    for xx in range (0,len(times)):
		#output = times[x][:12]+times[x][14:-2]
               	self.editdebug.AppendText(str(times[xx])+'\n')

 
	    tmsiarray = []#HOLDS SINGLE TMSI
            timestamp = []
	    tmsiarraycount =[]#HOLDS HOW MANY TIMES THE TMSI GOT PAGED
            CURRENT_TIMESTAMP = ""
            CURRENT_TMSI = ""

	    low_range = int(self.editpingrange1.GetValue())
	    high_range = int(self.editpingrange2.GetValue())
	    self.editdebugtmsi.SetValue("")
	    startindex = 0
	    endindex = 1
	    file = open("tmsicount.txt")
	    file.close()
	    loopcount = len(times)/2# EACH DELIVERY REPORT HAS 2 TIMESTAMPS SO IF 2 DEL REPORTS / 2 THAT LEAVES 4 TIMESTAMPS.
	    print("ARRAY LEN IS: "+str(loopcount))
	    #LOOP THRU ALL THE TIMESTAMPS 
            for x in range(0,loopcount):
			print("IN OPEN FILE LOOP "+str(x)+"\n")
			print(str(startindex)+":"+str(endindex)+"\n")
	    		file = open("tmsicount.txt")

	    		for line in file:
		    		line = line.rstrip('\n').rstrip('\r')
		    		#self.editdebugtmsi.AppendText(line[:8]+"@"+line[9:])
                        	if line[0:2] != "0-":
                            		CURRENT_TMSI = line[:8]
                            		CURRENT_TIMESTAMP = int(line[9:21])
                        		#self.editdebugtmsi.AppendText(str(CURRENT_TIMESTAMP))
                        		passint = 0;
                    			#print(str(startindex)+"\n"+str(endindex))
                    			# times[0] holds first timestamp and times[1] holds second timestamp    {endindex}
                            		if CURRENT_TIMESTAMP >= times[endindex]-3 and CURRENT_TIMESTAMP <= times[endindex]:
                            		#print("IN TIMESTAMP")
                                		if len(line) >= 8:
                                    			i = -1
                                    			try:
                                        			while 1:
                                            				i = tmsiarray.index(CURRENT_TMSI,i+1)
                                                			#print "match at", i,tmsiarray[i]
                                                			if i > -1:
                                            					tmsiarraycount[i] += 1
                                                                               	break
                                       			except ValueError:
                                       				tmsiarray.append(CURRENT_TMSI)
                                       				#timestamp[i] = CURRENT_TIMESTAMP
                                       				tmsiarraycount.append(1)
                                            	#self.editdebugtmsi.AppendText(line+'\n')
                                                
                        	else:
                            	     #self.editdebug.AppendText(line+'\n')
				     pass


	    		file.close()
			endindex+=2
			startindex += 2
#range loop ends here

	   #for debug output
	    #for tmsi in tmsiarray:
		   # print(tmsi)
	    
	    #prints the tmsi paged count from tmsiarraycount
	    x = 0
	    for tmsi in tmsiarray:
		    if tmsiarraycount[x] >= low_range and tmsiarraycount[x] <= high_range:
			    #print(tmsiarray[x]+":"+str(tmsiarraycount[x]))
			    self.editdebugtmsi.AppendText(tmsiarray[x]+":"+str(tmsiarraycount[x])+'\n')
		    x += 1

    ############################################################################
    #	MANUAL MODE TMSI FILTER
    #	PHONE MODE = MANUAL TIMESTAMPS
    ############################################################################
    
    def filterTmsiTimestampManMode(self,event):
	    START_TIME_OFFSET = 3
	    END_TIME_OFFSET = START_TIME_OFFSET + 3
	    SENT_TIMESTAMPS=[]
	    tmsiarray = []#HOLDS SINGLE TMSI
            timestamp = []
	    tmsiarraycount =[]#HOLDS HOW MANY TIMES THE TMSI WAS GOT
            CURRENT_TIMESTAMP = ""
            CURRENT_TMSI = ""
	    self.delivery_report_wait_timer.Stop()
	    file = open("manual_timestamps.txt")

	    for line in file:
			line = line.rstrip('\n').rstrip('\r')
			SENT_TIMESTAMPS.append(int(line))

	    file.close()


	    low_range = int(self.editpingrange1.GetValue())
	    high_range = int(self.editpingrange2.GetValue())
	    self.editdebugtmsi.SetValue("")
	    startindex = 0
	    endindex = 1
	    loopcount = len(SENT_TIMESTAMPS)
	    print("ARRAY LEN MANUAL =: "+str(loopcount))
	    #LOOP THRU ALL THE TIMESTAMPS 
            for x in range(0,loopcount):
			print("IN OPEN FILE LOOP "+str(x)+"\n")

	    		file = open("tmsicount.txt")
			print("SENT >"+str(SENT_TIMESTAMPS[x]+int(self.editoffsetrange1.GetValue()))+" < "+str(SENT_TIMESTAMPS[x]+int(self.editoffsetrange2.GetValue())))

	    		for line in file:
		    		line = line.rstrip('\n').rstrip('\r')
		    		#self.editdebugtmsi.AppendText(line[:8]+"@"+line[9:])
                        	if line[0:2] != "0-":
					#
                            		CURRENT_TMSI = line[:8]
                            		CURRENT_TIMESTAMP = int(line[9:21])
		    			#self.editdebugtmsi.AppendText(str(CURRENT_TIMESTAMP))
		    			passint = 0;
					#print(str(startindex)+"\n"+str(endindex))
					# times[0] holds first timestamp and times[1] holds second timestamp
		    			if CURRENT_TIMESTAMP >= SENT_TIMESTAMPS[x]+int(self.editoffsetrange1.GetValue()) and CURRENT_TIMESTAMP <= SENT_TIMESTAMPS[x]+int(self.editoffsetrange2.GetValue()):
						#print("SENT "+SENT_TIMESTAMPS[x]+START_TIME_OFFSET)
                                		if len(line) >= 8:
                                    			i = -1
                                    			try:
                                        			while 1:
                                            				i = tmsiarray.index(CURRENT_TMSI,i+1)
                                                			#print "match at", i,tmsiarray[i]
                                                			if i > -1:
                                            					tmsiarraycount[i] += 1
                                                                               	break
                                       			except ValueError:
                                       				tmsiarray.append(CURRENT_TMSI)
                                       				#timestamp[i] = CURRENT_TIMESTAMP
                                       				tmsiarraycount.append(1)
                                            			#self.editdebugtmsi.AppendText(line+'\n')
                                                
                        	else:
                            	     self.editdebug.AppendText(line+'\n')

	    		file.close()
#range loop ends here

	   #for debug output
	    #for tmsi in tmsiarray:
		   # print(tmsi)
	    
	    #prints the tmsi paged count from tmsiarraycount
	    x = 0
	    for tmsi in tmsiarray:
		    if tmsiarraycount[x] >= low_range and tmsiarraycount[x] <= high_range:
			    #print(tmsiarray[x]+":"+str(tmsiarraycount[x]))
			    self.editdebugtmsi.AppendText(tmsiarray[x]+":"+str(tmsiarraycount[x])+'\n')
		    x += 1
    ###############################################################################################
    #			BUTTON ACTIONS
    ##############################################################################################
    
    #clears delivery reports and deletes tmsi file for fresh attack
    def clearData(self,event):
	ser.port = self.combo_serial_ports.GetValue()
   	ser.open()
	if ser.isOpen():
		ser.write("AT+CMGD=1,4"+"\x0D")
		time.sleep(0.3)
		ress = ser.read(300)
		
		try:
			os.remove("tmsicount.txt")
			self.editdebug.AppendText("Tmsi file deleted\n")
		except OSError, e:
			self.editdebug.AppendText("Error: %s - %s.\n" % (e.filename,e.strerror))

		try:
			os.remove("manual_timestamps.txt")
			self.editdebug.AppendText("manual timestamps file deleted\n")
		except OSError, e:
			self.editdebug.AppendText("Error: %s - %s.\n" % (e.filename,e.strerror))


		if "OK" or ">" in ress:
			self.editdebug.AppendText("Delivery reports cleaned\n")
			ser.close()
		else:
			self.editdebug.AppendText("ERROR "+ress)
	ser.close()

    def getGqrxFreq(self,event):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    		s.settimeout(2)
    		# connect to remote host
    		try :
        		s.connect((TELNET_HOST, TELNET_PORT))
			print 'Connected to remote host'
			s.send("f\r\n")
			time.sleep(0.2)
			data = s.recv(1024)
			data =data.replace("\n", "");
			#self.editdebug.SetValue(data[:3]+"."+data[3:])
			self.editgsm_freq.SetValue(data[:3]+"."+data[3:])
			self.editrtl_freq.SetValue(data[:3]+"."+data[3:])
			s.close()
			print 'Connection Closed'
    		except :
        		print 'Unable to connect'
			self.editdebug.AppendText("Please set telent in gqrx on 127.0.0.1 7356\n")
        		#sys.exit()

    def autoMode(self,event):
        btnLabel = self.btnautomode.GetLabel()
        if btnLabel == "Automode":
            print "autoMode starting timer...\nSending Sms every "+self.editpdu_MD.GetValue()+" Seconds"
	    #pagecount =0; 
	    self.StartGsmRec(event)
            self.smstimer.Start(1000*int(self.editpdu_MD.GetValue()))
            self.btnautomode.SetLabel("Stop")
        else:
            print "autoMode timer stopped!"
            self.smstimer.Stop()
            self.btnautomode.SetLabel("Automode")
	    self.StopGsmRec(event)

    def startWireshark(self,event):
        btnLabel = self.btnwireshark.GetLabel()
        if btnLabel == "wireshark":
            print "Starting wireshark"
	    rtlstartstop = Popen(["wireshark","-k", "-d", "gsmtap", "-i", "lo"])
            self.btnwireshark.SetLabel("Stop")
        else:
            print "Wireshark stopped!"
	    call(["pkill","wireshark"])
            self.btnwireshark.SetLabel("wireshark")

    def onToggle(self, event):
        btnLabel = self.btnpdusend.GetLabel()
        if btnLabel == "Send":
            print "Starting Single sms timer...\nSending Sms in "+self.editpdu_MD.GetValue()+" Seconds"
	    #pagecount =0;
	    #longer delay will probably have more chance of catching all paging requests
            self.sms_single_timer.Start(1000*int(self.editpdu_MD.GetValue()))
            self.btnpdusend.SetLabel("Stop")
        else:
            print "timer stopped!"
            self.sms_single_timer.Stop()
            self.btnpdusend.SetLabel("Send")

    def On2gold(self,e):
	 selected_port = self.combo_serial_ports.GetValue()
         test(selected_port,"AT^SYSCFG=13,1,3FFFFFFF,2,4")



    def StartRtl(self,e):
        #self.editdebug.AppendText('test'+'\n') pkill rtl_sdr
       # test("AT^SYSCFG=13,1,3FFFFFFF,2,4")
	    FILENAME = self.editrtl_filename.GetValue()
	    SAMPLERATE = self.editrtl_samplerate.GetValue()
	    FREQ = self.editrtl_freq.GetValue()
	    GAIN =self.editrtl_gain.GetValue()
	    if GAIN != "":
		   rtlstartstop = Popen(["rtl_sdr", FILENAME,"-s",SAMPLERATE+"e6","-f",FREQ+"e6","-g",GAIN,])
	    else:
		    rtlstartstop  = Popen(["rtl_sdr", FILENAME,"-s",SAMPLERATE+"e6","-f",FREQ+"e6"])

    def StopRtl(self,e):
	    #rtlstartstop.terminate()
	    call(["pkill","rtl_sdr"])


    def StartGsmRec(self,e):
        #self.editdebug.AppendText('test'+'\n') pkill rtl_sdr
       # test("AT^SYSCFG=13,1,3FFFFFFF,2,4")
	   # FILENAME = self.editrtl_filename.GetValue()
	    SAMPLERATE = self.editgsm_samplerate.GetValue()
	    FREQ = self.editgsm_freq.GetValue()
	    GAIN =self.editgsm_gain.GetValue()
	    CHANNEL = self.editgsm_channel.GetValue()
	    GSMKEY = self.editgsm_key.GetValue()
	    call(["pkill","gqrx"])
	    self.btngqrx.SetLabel("GQRX")
	    #gsmstartstop = Popen(["./airprobe_rtlsdr.py"])
	    # ./airprobe_rtlsdr_mod.py -f 925.11e6 -g 43.1 -s 1.0e6 
	    if self.cbkey.GetValue() == True:
		    GSMKEY = self.gsm_key.GetValue()
		#LEFT AIRPROBE CODE HERE ALSO IF YOU WANT TO TRY
	    if GAIN != "":
		   gsmstartstop = Popen(["./gsm_receive_rtl.py","-s",SAMPLERATE+"e6","-f",FREQ+"e6","-g",GAIN,"-c",CHANNEL,"-k",GSMKEY])
		   #gsmstartstop = Popen(["./airprobe_rtlsdr.py","-f",FREQ+"e6","-g",GAIN,"-s",SAMPLERATE+"e6"])
		   #pass

	    else:
		   gsmstartstop = Popen(["./gsm_receive_rtl.py","-s",SAMPLERATE+"e6","-f",FREQ+"e6","-c",CHANNEL,"-k",GSMKEY])
		   #gsmstartstop = Popen(["./airprobe_rtlsdr.py","-f",FREQ+"e6","-s",SAMPLERATE+"e6"])
		#pass


    def StopGsmRec(self,e):
	    #rtlstartstop.terminate()
	    call(["pkill","-f","./gsm_receive_rtl.py"])
	    #call(["pkill","-f","./airprobe_rtlsdr.py"])

    def startKal(self,event):
        btnLabel = self.btnkal.GetLabel()
        if btnLabel == "KAL":
		self.btnkal.SetLabel("Stop")
		KAL = Popen(["kal","-s",self.cbkalrange.GetValue()])
		#self.btnkal.SetLabel("KAL")
		
        else:
            print "Stopping KAL....."
	    call(["pkill","kal"])
	    self.btnkal.SetLabel("KAL")

    def startStopGqrx(self,event):
        btnLabel = self.btngqrx.GetLabel()
        if btnLabel == "GQRX":
		self.btngqrx.SetLabel("Stop")
		GQRX = Popen(["gqrx"])
		#self.btngqrx.SetLabel("GQRX")
		
        else:
            print "Stopping gqrx....."
	    call(["pkill","gqrx"])
	    self.btngqrx.SetLabel("GQRX")

   
    ############################################################
    #KEY TMSI IMSI GOT HERE
    #########################################################
    def GetKeyBtnPress(self,e):
	#self.editdebug.SetValue(GetKeyTmsiImsi(self.editcomport.GetValue()))
	#selected_port = self.combo_serial_ports.GetValue().strip(' \t \r \n \r\n')
	ser.port = self.combo_serial_ports.GetValue()
	PHONE_DATA = GetKeyTmsiImsi(ser.port)

	#self.gsm_imsi.SetValue(PHONE_DATA[len(PHONE_DATA)-15:])
	self.gsm_tmsi.SetValue(PHONE_DATA[:8])
	self.gsm_key.SetValue(PHONE_DATA[9:25])

    def SendCommand(self, e):
	ser.port = self.combo_serial_ports.GetValue()
   	ser.open()
	if ser.isOpen():
         	ser.flushInput() #flush input buffer, discarding all its contents
        	ser.flushOutput()#flush output buffer, aborting current output 
	        sercmd = self.editname.GetValue()
	        #self.result.SetLabel("Ruuing on port:"+ser.port)
		#print("Ruuing on port:"+ser.port)
		#print("Command: "+"AT^SYSCFG=13,1,3FFFFFFF,2,4")
		ser.write(sercmd+"\x0D")
		time.sleep(0.5)
		ress = ser.read(300)
		#print("Response "+ress)
        	self.editdebug.AppendText(ress+'\n')
	ser.close()

        dlg = wx.MessageDialog(self,
                               message=ress,
                               caption='A Message Box',
                               style=wx.OK|wx.ICON_INFORMATION
                               )
        dlg.ShowModal()
        dlg.Destroy()
    ################################################################################
    # at combobox cmds are here
    ################################################################################
    def SendCommandAtCombo(self, e):
	ser.port = self.combo_serial_ports.GetValue()
   	ser.open()
	if ser.isOpen():
         	ser.flushInput() #flush input buffer, discarding all its contents
        	ser.flushOutput()#flush output buffer, aborting current output 
	        sercmd = self.cbk_at_cmds.GetValue()
	        #self.result.SetLabel("Ruuing on port:"+ser.port)
		#print("Ruuing on port:"+ser.port)
		#print("Command: "+"AT^SYSCFG=13,1,3FFFFFFF,2,4")
		ser.write(sercmd+"\x0D")
		time.sleep(0.5)
		bytesToRead = ser.inWaiting()
		ress = ser.read(bytesToRead)
		#print("Response "+ress)
	        self.editdebug.AppendText(ress+'\n')
	ser.close()

    ###############################################################################################
    #			MISC FUNCTIONS
    ###############################################################################################	    

    #*****************************************************************
    #			TIMER FUCTIONS
    #*****************************************************************

    ###############################################################################################
    #all the silent flash sms happen here
    ###############################################################################################
    def timerSendPDU(self,e):
        #
	if getSmsSendCount() <= int(self.editpdu_MC.GetValue()):
		ser.port = self.combo_serial_ports.GetValue()
		
		if ser.open() ==False:
			ser.open()

		if self.cbsilent.GetValue() == True:
			SMS_TYPE = SILENT
		else:
			SMS_TYPE = NORMAL_TEXT
		
		if self.cbflash.GetValue() == True:
			SMS_TYPE = FLASH2
 
		if ser.isOpen():
			incSmsSendCount()
			ser.flushInput() #flush input buffer, discarding all its contents
        		ser.flushOutput()#flush output buffer, aborting current output
			ser.write("AT+CMGS=17"+"\x0D")
                        PDU_STRING = createPduString(self.editpdu_NO.GetValue(),self.editpdu_PDU_SMS.GetValue(),SMS_TYPE)
			time.sleep(0.5)
			ser.write(PDU_STRING+"\x1A")
			time.sleep(0.5)
			ress = ser.read(500)
			self.lb_smsendcount_text.SetLabel("Sent:"+str(getSmsSendCount()))
			if "OK" or ">" in ress:
				self.editdebug.AppendText("Message Sent:\n"+str(getCurrentTimeStamp())+":\n"+self.editpdu_PDU_SMS.GetValue()+"\n")
				dumpTimeStampManMode()
				ser.close()
			else:
				self.editdebug.AppendText("Response: "+ress)
				ser.close()
	#checking that the sms count is == to whatever the user set in the box
	if getSmsSendCount() == int(self.editpdu_MC.GetValue()):
		#print(str(getSmsSendCount))
		setSmsSendCount(0)
		self.smstimer.Stop()
		#self.btnpdusend.SetLabel("Send")
		#self.StopGsmRec(e)
		#self.btnautomode.SetLabel("Start")
		#longer delay here will have more time from the sms to arrive to the receiver
		self.timerKillRtl.Start(1000*1)
		print("Stop rtl......")

	



	#send sms without auto mode
    def timerSingleSendPDU(self,e):
        #
	if getSmsSendCount() <= int(self.editpdu_MC.GetValue()):
		ser.port = self.combo_serial_ports.GetValue()
		
		if ser.open() ==False:
			ser.open()

		if self.cbsilent.GetValue() == True:
			SMS_TYPE = SILENT
		else:
			SMS_TYPE = NORMAL_TEXT
		
		if self.cbflash.GetValue() == True:
			SMS_TYPE = FLASH2
 
		if ser.isOpen():
			incSmsSendCount()
			ser.flushInput() #flush input buffer, discarding all its contents
        		ser.flushOutput()#flush output buffer, aborting current output
			ser.write("AT+CMGS=17"+"\x0D")
                        PDU_STRING = createPduString(self.editpdu_NO.GetValue(),self.editpdu_PDU_SMS.GetValue(),SMS_TYPE)
			time.sleep(0.8)
			ser.write(PDU_STRING+"\x1A")
			time.sleep(0.8)
			ress = ser.read(500)
			self.lb_smsendcount_text.SetLabel("Sent:"+str(getSmsSendCount()))
			if "OK" or ">" in ress:
				self.editdebug.AppendText("Message Sent:\n"+str(getCurrentTimeStamp())+":\n"+self.editpdu_PDU_SMS.GetValue()+"\n")
				dumpTimeStampManMode()#optional
				ser.close()
			else:
				self.editdebug.AppendText("Response: "+ress)
				ser.close()
	#checking that the sms count is == to whatever the user set in the box
	if getSmsSendCount() == int(self.editpdu_MC.GetValue()):
		#print(str(getSmsSendCount))
		setSmsSendCount(0)
		self.sms_single_timer.Stop()
		self.btnpdusend.SetLabel("Send")
		#longer delay here will have more time from the sms to arrive to the receiver
		print("Stopping Single sms timer......")




    def timerStopRtl(self,event):
	    #rtlstartstop.terminate()
	    call(["pkill","-f","./gsm_receive_rtl.py"])
	    #call(["pkill","-f","./airprobe_rtlsdr.py"])
	    self.btnautomode.SetLabel("Automode")
	    print("Filtering Tmsi in "+self.editpdu_MDR.GetValue()+" seconds\nDelaying for delivery reports to get back.")
	    self.timerKillRtl.Stop()
	    self.delivery_report_wait_timer.Start(1000*int(self.editpdu_MDR.GetValue()))
	    ser.port = self.combo_serial_ports.GetValue()
	    #ser.open()
	    #self.filterTmsiTimestampMode(event)
	    


app = wx.App(False)
frame = ExampleFrame(None)
frame.Show()
app.MainLoop()
