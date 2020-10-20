Contents = """
The information contained herein is proprietary to Applanix corporation. Release to third parties of this publication or of information contained herein is prohibited without the prior written 
consent of Applanix Corporation. Applanix reserves the right to change the specifications and information in this document without notice. A record of the changes made to this document is 
contained in the Revision History sheet. 


 
POS MV V4 User ICD 
Document # : PUBS-ICD-000551 
Revision: 0.0 
Date: 12-May-06 


ii 


 
Table of Contents 
Page 
1 SCOPE .................................................................................................................................................. 1 
2 ETHERNET AND DATA ACQUISITION INTERFACES................................................................ 1 
3 OUTPUT GROUPS .............................................................................................................................. 3 
3.1 Introduction .................................................................................................................................... 3 
3.2 Output Group Specification............................................................................................................ 3 
3.2.1 Group Data Rates .................................................................................................................... 3 
3.2.2 Group Classification and Numbering Convention .................................................................. 3 
3.2.3 Group Format .......................................................................................................................... 6 
3.2.4 Compatibility with Previous POS Products ............................................................................ 9 
3.3 Output Group Tables .................................................................................................................... 10 
3.3.1 POS Data Groups .................................................................................................................. 10 
3.3.1.1 Group 1: Vessel Position, Velocity, Attitude & Dynamics ........................................... 10 
3.3.1.2 Group 2: Vessel Navigation Performance Metrics ........................................................ 12 
3.3.1.3 Group 3: Primary GPS Status ........................................................................................ 13 
3.3.1.4 Group 4: Time-tagged IMU Data................................................................................... 16 
3.3.1.5 Group 5: Event 1 ............................................................................................................ 17 
3.3.1.6 Group 6: Event 2 ............................................................................................................ 17 
3.3.1.7 Group 7: PPS Time Recovery and Status ...................................................................... 17 
3.3.1.8 Group 8: Reserved ......................................................................................................... 18 
3.3.1.9 Group 9: GAMS Solution .............................................................................................. 18 
3.3.1.10 Group 10: General Status and FDIR .............................................................................. 20 
3.3.1.11 Group 11: Secondary GPS Status .................................................................................. 26 
3.3.1.12 Group 12: Auxiliary 1 GPS Status ................................................................................. 27 
3.3.1.13 Group 13: Auxiliary 2 GPS Status ................................................................................. 27 
3.3.1.14 Group 14: Calibrated Installation Parameters ................................................................ 29 
3.3.1.15 Group 15: Reserved ....................................................................................................... 31 
3.3.1.16 Group 16: Reserved ....................................................................................................... 31 


iii 


 
3.3.1.17 Group 17: User Time Status........................................................................................... 31 
3.3.1.18 Group 20: IIN Solution Status ....................................................................................... 32 
3.3.1.19 Group 21: Base GPS 1 Modem Status ........................................................................... 33 
3.3.1.20 Group 22: Base GPS 2 Modem Status ........................................................................... 34 
3.3.1.21 Group 23: Auxiliary 1 GPS Display Data...................................................................... 34 
3.3.1.22 Group 24: Auxiliary 2 GPS Display Data...................................................................... 34 
3.3.1.23 Group 25: Reserved ....................................................................................................... 35 
3.3.1.24 Group 26: Reserved ....................................................................................................... 35 
3.3.1.25 Group 99: Versions and Statistics .................................................................................. 35 
3.3.1.26 Group 102: Sensor 1 Position, Velocity, Attitude, Heave & Dynamics ........................ 37 
3.3.1.27 Group 103: Sensor 2 Position, Velocity, Attitude, Heave & Dynamics ........................ 37 
3.3.1.28 Group 104: Sensor 1 Position, Velocity, and Attitude Performance Metrics ................ 38 
3.3.1.29 Group 105: Sensor 2 Position, Velocity, and Attitude Performance Metrics ................ 38 
3.3.1.30 Group 110: MV General Status & FDIR ....................................................................... 39 
3.3.1.31 Group 111: Heave & True Heave Data.......................................................................... 40 
3.3.1.32 Group 112: NMEA Strings ............................................................................................ 41 
3.3.1.33 Group 113: Heave & True Heave Performance Metrics................................................ 41 
3.3.1.34 Group 114: TrueZ & TrueTide Data .............................................................................. 42 
3.3.2 Raw Data Groups .................................................................................................................. 43 
3.3.2.1 Group 10001: Primary GPS Data Stream ...................................................................... 43 
3.3.2.2 Group 10002: Raw IMU Data........................................................................................ 44 
3.3.2.3 Group 10003: Raw PPS ................................................................................................. 45 
3.3.2.4 Group 10004: Raw Event 1............................................................................................ 45 
3.3.2.5 Group 10005: Raw Event 2............................................................................................ 45 
3.3.2.6 Group 10006: Reserved ................................................................................................. 46 
3.3.2.7 Group 10007: Auxiliary 1 GPS Data Stream................................................................. 46 
3.3.2.8 Group 10008: Auxiliary 2 GPS Data Stream................................................................. 46 
3.3.2.9 Group 10009: Secondary GPS Data Stream .................................................................. 47 
3.3.2.10 Group 10010: Reserved ................................................................................................. 47 
3.3.2.11 Group 10011: Base GPS 1 Data Stream ........................................................................ 48 
3.3.2.12 Group 10012: Base GPS 2 Data Stream ........................................................................ 48 


iv 


 
4 MESSAGE INPUT AND OUTPUT ................................................................................................... 49 
4.1 Introduction .................................................................................................................................. 49 
4.2 Message Output Data Rates.......................................................................................................... 49 
4.2.1 Message Numbering Convention .......................................................................................... 49 
4.2.2 Compatibility with Previous POS Products .......................................................................... 52 
4.3 Message Format ........................................................................................................................... 52 
4.3.1 Introduction ........................................................................................................................... 52 
4.4 Messages Tables........................................................................................................................... 54 
4.4.1 General Messages.................................................................................................................. 54 
4.4.1.1 Message 0: Acknowledge .............................................................................................. 54 
4.4.2 Installation Parameter Set-up Messages................................................................................ 56 
4.4.2.1 Message 20: General Installation and Processing Parameters ....................................... 56 
4.4.2.2 Message 21: GAMS Installation Parameters ................................................................. 61 
4.4.2.3 Message 22: Reserved.................................................................................................... 63 
4.4.2.4 Message 23: Reserved.................................................................................................... 63 
4.4.2.5 Message 24: User Accuracy Specifications ................................................................... 63 
4.4.2.6 Message 25: Reserved.................................................................................................... 64 
4.4.2.7 Message 30: Primary GPS Setup ................................................................................... 64 
4.4.2.8 Message 31: Secondary GPS Setup ............................................................................... 67 
4.4.2.9 Message 32: Set POS IP Address .................................................................................. 69 
4.4.2.10 Message 33: Event Discrete Setup................................................................................. 71 
4.4.2.11 Message 34: COM Port Setup........................................................................................ 71 
4.4.2.12 Message 35: See Message 135....................................................................................... 73 
4.4.2.13 Message 36: See Message 136....................................................................................... 73 
4.4.2.14 Message 37: Base GPS 1 Setup ..................................................................................... 73 
4.4.2.15 Message 38: Base GPS 2 Setup ..................................................................................... 74 
4.4.2.16 Message 40: Reserved.................................................................................................... 75 
4.4.2.17 Message 41: Reserved.................................................................................................... 75 
4.4.3 Processing Control Messages................................................................................................ 75 
4.4.3.1 Message 50: Navigation Mode Control ......................................................................... 75 
4.4.3.2 Message 51: Display Port Control ................................................................................. 76 


v 


 
4.4.3.3 Message 52: Real-Time Data Port Control .................................................................... 77 
4.4.3.4 Message 53: Reserved.................................................................................................... 79 
4.4.3.5 Message 54: Save/Restore Parameters Control.............................................................. 79 
4.4.3.6 Message 55: User Time Recovery ................................................................................. 80 
4.4.3.7 Message 56: General Data ............................................................................................. 80 
4.4.3.8 Message 57: Installation Calibration Control ................................................................ 82 
4.4.3.9 Message 58: GAMS Calibration Control....................................................................... 84 
4.4.3.10 Message 60: Reserved.................................................................................................... 85 
4.4.3.11 Message 61: Logging Data Port Control........................................................................ 85 
4.4.4 Program Control Override Messages .................................................................................... 85 
4.4.4.1 Message 90: Program Control........................................................................................ 85 
4.4.4.2 Message 91: GPS Control .............................................................................................. 86 
4.4.4.3 Message 92: Reserved.................................................................................................... 87 
4.4.4.4 Message 93: Reserved.................................................................................................... 87 
4.4.5 POS MV Specific Messages ................................................................................................. 87 
4.4.5.1 Message 105: Analog Port Set-up.................................................................................. 87 
4.4.5.2 Message 106: Heave Filter Set-up ................................................................................. 89 
4.4.5.3 Message 111: Password Protection Control................................................................... 90 
4.4.5.4 Message 120: Sensor Parameter Set-up ......................................................................... 91 
4.4.5.5 Message 121: Vessel Installation Parameter Set-up ...................................................... 94 
4.4.5.6 Message 135: NMEA Output Set-up ............................................................................. 95 
4.4.5.7 Message 136: Binary Output Set-up .............................................................................. 97 
4.4.6 POS MV Specific Diagnostic Control Messages ................................................................ 100 
4.4.6.1 Message 20102: Binary Output Diagnostics................................................................ 100 
4.4.6.2 Message 20103: Analog Port Diagnostics ................................................................... 101 
5 APPENDIX A: DATA FORMAT DESCRIPTION......................................................................... 103 
5.1 Data Format ................................................................................................................................ 103 
5.2 Invalid Data Values .................................................................................................................... 105 
6 APPENDIX B: GLOSSARY OF ACRONYMS ............................................................................... 107 


vi 


 
List of Tables 
Table 1: Output Group Data Rates................................................................................................................ 4 
Table 2: Group format .................................................................................................................................. 6 
Table 3: Time and distance fields ................................................................................................................. 7 
Table 4: Group 1: Vessel position, velocity, attitude & dynamics ............................................................. 10 
Table 5: Group 1 alignment status .............................................................................................................. 11 
Table 6: Group 2: Vessel navigation performance metrics......................................................................... 12 
Table 7: Group 3: Primary GPS status........................................................................................................ 13 
Table 8: GPS receiver channel status data .................................................................................................. 14 
Table 9: GPS navigation solution status ..................................................................................................... 14 
Table 10: GPS channel status ..................................................................................................................... 15 
Table 11: GPS receiver type ....................................................................................................................... 15 
Table 12: Trimble BD950 GPS receiver status........................................................................................... 16 
Table 13: Group 4: Time-tagged IMU data ................................................................................................ 16 
Table 14: Group 5/6: Event 1/2 .................................................................................................................. 17 
Table 15: Group 7: PPS Time Recovery and Status ................................................................................... 18 
Table 16: Group 9: GAMS Solution Status ................................................................................................ 19 
Table 17: Group 10: General and FDIR status ........................................................................................... 21 
Table 18: Group 11: Secondary GPS status................................................................................................ 26 
Table 19: Group 12/13: Auxiliary 1/2 GPS status ...................................................................................... 28 
Table 20: Group 14: Calibrated installation parameters ............................................................................. 29 
Table 21: IIN Calibration Status ................................................................................................................. 31 
Table 22: Group 20: IIN solution status...................................................................................................... 32 
Table 23: Group 21/22: Base GPS 1/2 Modem Status................................................................................ 34 
Table 24: Group 23/24: Auxiliary 1/2 GPS raw display data ..................................................................... 35 
Table 25: Group 99: Versions and statistics ............................................................................................... 35 
Table 26: Group 102/103: Sensor 1/2 Position, Velocity, Attitude, Heave & Dynamics........................... 37 
Table 27: Group 104/105: Sensor 1/2 Position, Velocity, and Attitude Performance Metrics ................... 39 
Table 28: Group 110: MV General Status & FDIR .................................................................................... 39 


vii 


 
Table 29: Group 111: Heave & True Heave Data....................................................................................... 40 
Table 30: Group 112: NMEA Strings ......................................................................................................... 41 
Table 31: Group 113: Heave & True Heave Performance Metrics............................................................. 42 
Table 32: Group 114: TrueZ & TrueTide Data........................................................................................... 43 
Table 33: Group 10001: Primary GPS data stream..................................................................................... 44 
Table 34: Group 10002: Raw IMU data ..................................................................................................... 44 
Table 35: Group 10003: Raw PPS .............................................................................................................. 45 
Table 36: Group 10004/10005: Raw Event 1/2 .......................................................................................... 46 
Table 37: Group 10007/10008: Auxiliary 1/2 GPS data streams ............................................................... 46 
Table 38: Group 10009: Secondary GPS data stream................................................................................. 47 
Table 39: Group 10011/10012: Base GPS 1/2 data stream......................................................................... 48 
Table 40: Control messages output data rates............................................................................................. 50 
Table 41: Message format........................................................................................................................... 52 
Table 42: Message 0: Acknowledge ........................................................................................................... 55 
Table 43: Message response codes ............................................................................................................. 55 
Table 44: Message 20: General Installation and Processing Parameters .................................................... 59 
Table 45: Message 21: GAMS installation parameters............................................................................... 62 
Table 46: Message 24: User accuracy specifications.................................................................................. 63 
Table 47: Message 30: Primary GPS Setup ................................................................................................ 65 
Table 48: RS-232/422 communication protocol settings............................................................................ 66 
Table 49: Message 31: Secondary GPS Setup ............................................................................................ 68 
Table 50: Message 32: Set POS IP Address ............................................................................................... 69 
Table 51: Message 33: Event Discrete Setup.............................................................................................. 71 
Table 52: Message 34: COM Port Setup .................................................................................................... 72 
Table 53: COM port parameters ................................................................................................................. 73 
Table 54: Message 37/38: Base GPS 1/2 Setup .......................................................................................... 74 
Table 55: Message 50: Navigation mode control ....................................................................................... 76 
Table 56: Message 51: Display Port Control .............................................................................................. 77 
Table 57: Message 52/61: Real-Time/Logging Data Port Control ............................................................. 78 
Table 58: Message 54: Save/restore parameters control............................................................................. 79 
Table 59: Message 55: User time recovery................................................................................................. 80 
Table 60: Message 56: General data ........................................................................................................... 81 


viii 


 
Table 61: Message 57: Installation calibration control ............................................................................... 83 
Table 62: Message 58: GAMS Calibration Control.................................................................................... 84 
Table 63: Message 90: Program Control .................................................................................................... 86 
Table 64: Message 91: GPS control............................................................................................................ 87 
Table 65: Message 105: Analog Port Set-up .............................................................................................. 87 
Table 66: Message 106: Heave Filter Set-up .............................................................................................. 89 
Table 67: Message 111: Password Protection Control ............................................................................... 90 
Table 68: Message 120: Sensor Parameter Set-up ...................................................................................... 92 
Table 69: Message 121: Vessel Installation Parameter Set-up ................................................................... 94 
Table 70: Message 135: NMEA Output Set-up .......................................................................................... 95 
Table 71: NMEA Port Definition................................................................................................................ 95 
Table 72: Message 136: Binary Output Set-up ........................................................................................... 97 
Table 73: Binary Port Definition ................................................................................................................ 97 
Table 74: Message 20102: Binary Output Diagnostics............................................................................. 100 
Table 75: Message 20103: Analog Port Diagnostics ................................................................................ 101 
Table 76: Byte Format .............................................................................................................................. 103 
Table 77: Short Integer Format ................................................................................................................. 103 
Table 78: Long Integer Format ................................................................................................................. 103 
Table 79: Single-Precision Real Format ................................................................................................... 103 
Table 80: Double-Precision Real Format.................................................................................................. 104 
Table 81: Invalid data values .................................................................................................................... 106 


1 

"""

Structures = """
1 Scope 
This document presents the functional specification of the POS MV Control, Display and Data 
Ports and data structures used by the POS Computer System (PCS) to communicate with the user 
over its Control, Display and Data Ports. The document is separated into specifications of output 
data groups and input and output control messages that are relevant to the user. 
This document describes the data structures that are implemented in the V4 system version of 
POS MV. POS MV V4 shall hereafter be refered to as POS MV or simply POS. 
2 Ethernet and Data Acquisition Interfaces 
The POS MV provides a mechanism for control and data exchange in the form of control 
messages and data groups. Control messages direct POS MV to execute a well-defined action 
such as mode transition, or start or stop of data acquisition. Data groups contain the data output 
by the POS MV for the purpose of display on a control computer, recording to a mass storage 
device, or for real-time processing by another subsystem. POS MV exchanges all control 
messages with a user via the POS's Control Port. It outputs all data groups on the Display and 
Data Logging Ports. 
Applanix provides a program called MV POSView with the POS MV to run on the user's PC- 
compatible computer running Microsoft Windows 2000 or XP. The user's PC is called the client 
computer and is used to both control the system and allow the user to view POS data via the 
control messages and data groups specified in this document. The user can create custom control 
and display software that implements similar functionality. In either case, the program that 
provides the control and display functions on the client computer will hereafter be referred to as 
the POS Controller. 
POS MV provides one physical Ethernet interface that has four logical communications ports 
called the Display Port, the Control Port, the Real-Time Data Port and the Logging Data Port. 
POS MV outputs data in specified group formats defined in the body of this document. Messages 
are used to both change and describe the system configuration. Both message and group data are 
output on three ports: Display, Real-Time Data and Logging Data. Messages are input on the 
Control Port. 
The Display Port is a low rate UDP output port that is designed to broadcast low rate data and 
status information for display. The POS Controller reads the message and group data from this 
port for display purposes. POS MV is designed to allow multiple POS Controller programs 
running on different computers to receive and display data from the PCS. However, only one 
POS Controller at any time can be designated as the master controller and be capable of sending 
commands to the PCS via the Control Port. This arrangement prevents conflicting controller 
information from being received by the PCS. 
The port address for the Display Port is 5600. The subnet mask is 255.255.255.255. 
The Real-Time Data Port is a high rate UDP output port that is designed to output multiple data 


2 


 
groups at high data rates with minimal latency. Since there is no handshaking implemented in 
UDP there is a possibility that the client may not receive all data packets. The Real-Time Data 
Port design emphasizes real-time delivery of the data without the overhead of ensuring totally 
reliable data transfer. To receive data from the Real-Time Data Port, a computer must listen to 
the port using the UDP socket protocol. Several computers may be connected to the Real-Time 
Data Port at any one time. MV POSView uses this port to obtain some higher rate data from 
POS MV that is required for display plots. 
The Logging Data Port is a high rate TCP/IP output port that is designed to output multiple data 
groups at high data rates. The emphasis is on reliable and efficient data transfer to the client 
computer. The Logging Data Port implements several buffers to store data in the event the 
TCP/IP connection between POS and the client computer becomes bogged down or requires 
retransmission of packets. To receive data from the Logging Data Port, a computer must connect 
to it using the TCP/IP socket protocol. Only one computer may be connected to the Logging 
Data Port at any one time. MV POSView can log this data to the client computer's hard drive. 
The port address for the Real-Time Data Port is 5602 and 5603 for the Logging Data Port. The 
IP subnet mask is 255.255.255.255. 
The user is able to select, from several different options, the data required for output. Each port 
can be configured to output different data than the other ports. POS MV accepts changes to the 
output options of the Display, Data and Logging ports at any time. MV POSView automatically 
sends the Display Port control message to output the data groups that it requires to populate the 
display windows as the user opens them. 
The Control Port is designed to receive set-up and control commands from the POS Controller 
and to acknowledge the commands to indicate successful reception of each message. The Control 
Port is bi-directional and uses the TCP/IP protocol to communicate with the POS Controller. 
The port address for the Control Port is 5601. The IP subnet mask is 255.255.255.255. 


3 


 
3 Output Groups 
3.1 Introduction 
POS MV organizes the data going to the Display and Data ports into output groups. Each group 
contains a block of related data at a specified group rate. The user directs POS MV via Control 
Port messages generated by the POS Controller to include a group or groups containing data 
items of interest in the Display and Data port data streams. The output groups have been 
designed to allow simple parsing and decoding of the output data streams into the selected 
groups. All groups are framed by ASCII delimiters and have identifiers that uniquely identify 
each group. 
The output data rate on the Display Port is typically once per second or less. This output is 
intended for updating the POS Controller display; hence a higher data output rate is not required. 
The output data rate on the Data Ports is group dependent and has a range from 1Hz to an IMU 
rate. For certain output groups, it is possible to select, from several options, the output data rate 
of choice on the Data ports. 
3.2 Output Group Specification 
3.2.1 Group Data Rates 
There are several output groups defined for the Display and Data ports. The user can select any 
of these groups and may select different groups for the Display Port, Real-Time Data Port and 
Logging Data Port. The Standby and Navigate modes shown in Table 1 are defined in 
POS MV V4 User Guide. 
3.2.2 Group Classification and Numbering Convention 
All POS products use the following group numbering convention. POS MV outputs the group 
categories shown. Reserved group numbers are assigned to other products. 
0 - 99 POS Core User data groups 
100 - 199 POS MV User data groups 
200 - 299 POS AV User data groups 
300 - 399 POS TG User data groups 
400 - 499 POS LV User data groups 
500 - 599 POS LS User data groups 
600 - 699 POS SV User data groups 
700 - 799 POS MC User data groups 
800 - 9999 Reserved 


4 


 
10000 - 10099 POS Core Raw data groups 
10100 - 10199 POS MV Raw data groups 
10200 - 10299 POS AV Raw data groups 
10300 - 10399 POS TG Raw data groups 
10400 - 10499 POS LV Raw data groups 
10500 - 10599 POS LS Raw data groups 
10600 - 10699 POS SV Raw data groups 
10700 - 10799 POS MC Raw data groups 
10800 - 19999 Reserved 
20000 POS Core User diagnostic group 
20001 - 20099 POS Core Proprietary diagnostic groups 
20100 POS MV User diagnostic group 
Core User data groups and MV User data groups comprise groups that contain real-time 
operational data. During normal operation, these are the only groups that a user would require for 
observing or recording relevant POS MV data. 
Core Raw data groups and POS MV Raw data groups comprise the unaltered data streams 
from the navigation sensors received by the PCS. POS MV packages the sensor data into the 
specified group formats and outputs the groups. These groups are typically used for post-mission 
processing and analysis. 

Table 0: PCSRecordHeader 
Creating this type since POS MV spec didn't declare a header typ eeven though they use two interchangeable headers
Start 4 char $GRP N/A 
ID 2 ushort 2 N/A 
Byte count 2 ushort 80 bytes 

Table 1: GrpRecordHeader 
Creating this type since POS MV spec didn't declare a header typ eeven though they use two interchangeable headers
Start 4 char $GRP N/A 
ID 2 ushort 2 N/A 
Byte count 2 ushort 80 bytes 
Time 1 8 double N/A seconds 
Time 2 8 double N/A seconds 
Distance tag 8 double N/A meters 
Time types 1 byte Time 1 Select Value in bits 0-3 

xTable 1: Output Group Data Rates 
Display Port Output 
Rate (Hz) 
Real-Time Data 
Port Output Rate 
(Hz) 
Logging Data Port 
Output Rate (Hz) 
Group Contents 
Standby Navigate Standby Navigate Standby Navigate 
POS Data Groups 
1* Vessel position, velocity, attitude & 
dynamics 
- 1 1 - 1-200 - 1-200 
2 Vessel navigation performance metrics - 1 1 - 1 - 1 
3 Primary GPS status 1 1 1 1 1 1 1 1 
4 Time-tagged IMU data 1 1 200 200 200 200 
5 Event 1 data 2 1 1 1-500 1-500 1-500 1-500 
6 Event 2 data 2 1 1 1-500 1-500 1-500 1-500 
7 PPS data 2 1 1 1 1 1 1 
8 Reserved - - - - - - 


5 


 
Display Port Output 
Rate (Hz) 
Real-Time Data 
Port Output Rate 
(Hz) 
Logging Data Port 
Output Rate (Hz) 
Group Contents 
Standby Navigate Standby Navigate Standby Navigate 
9 GAMS solution status - 1 - 1 - 1 
10 General and FDIR status 1 1 1 1 1 1 1 1 
11 Secondary GPS status 1 1 1 1 1 1 
12 Auxiliary 1 GPS status 1 1 1 1 1 1 
13 Auxiliary 2 GPS status 1 1 1 1 1 1 
14 Calibrated installation parameters - 1 - 1 - 1 
15 Reserved - - - - - - 
16 Reserved - - - - - - 
17 User time status 1 1 1 1 1 1 
20 IIN solution status - 1 - 1 - 1 
21 Base 1 GPS modem status 1 1 1 1 1 1 
22 Base 2 GPS modem status 1 1 1 1 1 1 
23 Auxiliary 1 GPS display data 2 1 1 1 1 1 1 
24 Auxiliary 2 GPS display data 2 1 1 1 1 1 1 
25 Reserved - - - - - - 
26 Reserved - - - - - - 
99 Versions and statistics 1 1 1 1 1 1 
102 Sensor 1 position, velocity, attitude, 
heave & dynamics 
- 1 - 1-200 - 1-200 
103 Sensor 2 position, velocity, attitude, 
heave & dynamics 
- 1 - 1-200 - 1-200 
104 Sensor 1 position, velocity & attitude 
performance metrics 
- 1 - 1 - 1 
105 Sensor 2 position, velocity & attitude 
performance metrics 
- 1 - 1 - 1 
110 MV general status & FDIR 1 1 1 1 1 1 
111 Heave & True Heave - 1 - 25 - 25 
112 NMEA strings - 1 - 1-50 - 1-50 
113 Heave performance metrics - 1 - 25 - 25 
114 TrueZ and TrueTide altitude - 1 - 25 - 25 
Raw Data Groups 
10001 Primary GPS data stream - - 1-10 1-10 1-10 1-10 


6 


 
Display Port Output 
Rate (Hz) 
Real-Time Data 
Port Output Rate 
(Hz) 
Logging Data Port 
Output Rate (Hz) 
Group Contents 
Standby Navigate Standby Navigate Standby Navigate 
10002 IMU data stream - - 200 200 200 200 
10003 PPS data - - 1 1 1 1 
10004 Event 1 data - - 1-500 1-500 1-500 1-500 
10005 Event 2 data - - 1-500 1-500 1-500 1-500 
10006 Reserved - - - - - - 
10007 Auxiliary 1 GPS data stream 1-10 1-10 1-10 1-10 
10008 Auxiliary 2 GPS data stream 1-10 1-10 1-10 1-10 
10009 Secondary GPS data stream - - 1-10 1-10 1-10 1-10 
10010 Reserved - - - - - - 
10011 Base 1 GPS data stream - - 0-1 0-1 0-1 0-1 
10012 Base 2 GPS data stream - - 0-1 0-1 0-1 0-1 
Note: When POS is in Navigation mode but not aligned then the output rate is implementation dependent. 
* Data is in the vessel frame for POS MV. 
1 These groups are the minimum output of the Display Port for driving the POS View display and cannot be 
deselected. 
2 Groups are only posted when data were available. 
3.2.3 Group Format 
The structure of each output group is defined in this section. The group structure is the same for 
all groups and consists of a header, data and footer. Table 2 presents the complete groups 
format, showing the header and footer separated by the data. The next section specifies the data 
for each group. 
Table 2: Group format 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort Group number N/A 
Byte count 2 ushort Group dependent bytes 
Time/Distance Fields 26 See Table 3 
Data Group dependent size and format 
Pad 0 to 3 _byte 0 N/A 


7 


 
Item Bytes Format Value Units 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Table 3: Time and distance fields 
Item Bytes Format Value Units 
Time 1 8 double N/A seconds 
Time 2 8 double N/A seconds 
Distance tag 8 double N/A meters 
Time types 1 byte Time 1 Select Value in bits 0-3 
Time 1: POS time 0 
Time 1: GPS time 1 (default) 
Time 1: UTC time 2 
Time 2 Select Value in bits 4-7 
Time 2: POS time 0 (default) 
Time 2: GPS time 1 
Time 2: UTC time 2 
Time 2: User time 3 
Distance type 1 byte Distance Select Value 
N/A 0 
POS distance 1 (default) 
DMI distance 2 
The header consists of the following components: 
# 
ASCII group start ($GRP) 
# 
group identification (Group ID) number 
# 
byte count 
# 
time/distance fields 
The group identification or Group ID is a short unsigned integer equal to the group number 
having the group numbering convention described in Section 3.2.2. 


8 


 
The byte count is a short unsigned integer that includes all fields in the group except the $GRP 
delimiter, the Group ID and the byte count. Therefore, the byte count is always 8 bytes less than 
the length of the group. 
The time/distance fields are shown in Table 3. These occupy 26 bytes and have the same format 
across all groups. They comprise the following: 
# 
Time 1 
# 
Time 2 
# 
Distance tag and time and distance type flags. 
Time 1 is the POS MV system time of validity of the data in the group, given in one of the 
following time bases: 
# 
POS time (time in seconds since power-on) 
# 
GPS seconds of the week 
# 
UTC seconds of the week 
The user can select any of these times for Time 1. Time 1 is set to POS time on power-up and 
changes to the user selected time base once the primary GPS receiver has locked on to a 
sufficient number of satellites to compute a time solution. 
Time 2 is the POS MV system time of validity of the data in the group, given in one of the 
following time bases: 
# 
POS time (time in seconds since power-on) 
# 
GPS seconds of the week 
# 
UTC seconds of the week 
# 
User time 
User time is specified by the user, with the procedure to set user time described in the 
POS MV V4 User Guide. It allows the groups to be time tagged with an external computer's 
time clock. The Time 2 field is always set to POS time for the raw (10000) series of data groups. 
Distance tag is the distance of validity of the data in the group as determined by one of the 
following distance measurement sources: 
# 
distance traveled derived from the POS MV blended navigation solution 
# 
DMI (distance measurement index) distance tag 
The group data follows the header. Its format is dependent on the particular group. Some group 
data lengths are fixed, whereas others may vary. For variable length groups the byte count is 
always updated to reflect the actual length of the group. 


9 


 
The group is terminated by the footer, which consists of the following components: 
# 
a pad (if required) 
# 
checksum 
# 
ASCII group end delimiter ($#). 
The pad is used to make the total lengths of all groups a multiple of four bytes. The checksum is 
calculated so that the sum of byte pairs cast as short (16 bit) integers over the complete group 
results in a net sum of zero. 
The byte, short, ushort, long, ulong, float and double formats are defined in Appendix A: Data 
Format Description. 
The ranges of valid values for group fields that contain numbers are specified using the 
following notation. 
[a, b] implies the range a to b including the range lower and upper boundaries. A value x 
that falls in this range will respect the inequality a # 
x # 
b. 
(a, b) implies the range a to b excluding the range lower and upper boundaries. A value x 
that falls in this range will respect the inequality a # 
x # 
b. 
(a, b] implies the range a to b excluding the lower boundary and including the upper 
boundary. A value x that falls in this range will respect the inequality a # 
x # 
b. 
[a, b) implies the range a to b excluding the range lower and upper boundaries. A value x 
that falls in this range will respect the inequality a # 
x # 
b. 
If a value a or b is not given, then there is no corresponding lower or upper boundary. 
The following are special cases: 
(0, ) represents all positive numbers (excludes 0) 
[0, ) represents all non-negative numbers (includes 0) 
( , 0) represents all negative numbers (excludes 0) 
( , 0] represents all non-positive numbers (includes 0) 
( , ) represents all numbers in the range of valid numbers. 
Group fields that contain numerical values may contain invalid numbers. Invalid byte, short, 
ushort, long, ulong, float and double values are defined in Table 82 in Appendix A: Data Format 
Description. POS MV outputs invalid values in fields containing numerical values for which 
POS MV has no valid data. This does not apply to fields containing bit settings. 
3.2.4 Compatibility with Previous POS Products 
The compatibility of POS MV V4 groups with POS MV V3 products is given as follows: 
The POS MV V4 group format is the same as that of the POS MV V3 products. 


10 


 
The contents of Groups 1-8 and Group 99 are the same as those of the POS MV V3 products. 
However, Groups 7 and 8 have been expanded with new fields that occur before the Pad 
field. This is compatible with the POS MV V3 group design. Groups 9-98 are not defined in 
POS MV V3 products. Hence, no compatibility requirement exists for these groups. 
Several groups in the range of Groups 9-98 are the same as or similar to some POS MV V3 
product-specific groups. For example, Group 10 is similar to POS MV V3 Group 101. 
The contents of Groups 10001-10005 are the same as those of all POS MV V3 products. 
3.3 Output Group Tables 
3.3.1 POS Data Groups 
Group 1: Vessel Position, Velocity, Attitude & Dynamics 
The POS MV group 1 contains data valid for the position defined by the user-entered reference 
to vessel lever arms (see Message 121: Vessel Installation Parameter Set-up). POS MV assumes 
the vessel and reference frames are co-aligned, therefore the reference to vessel mounting angles 
(see Message 20: General Installation and Processing Parameters) should be zero. 
Table 4: Group 1: Vessel position, velocity, attitude & dynamics 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 1 N/A 
Byte count 2 ushort 132 bytes 
Time/Distance Fields 26 See Table 3 
Latitude 8 double (-90, 90] degrees 
Longitude 8 double (-180, 180] degrees 
Altitude 8 double ( , ) meters 
North velocity 4 float ( , ) meters/second 
East velocity 4 float ( , ) meters/second 
Down velocity 4 float ( , ) meters/second 
Vessel roll 8 double (-180, 180] degrees 
Vessel pitch 8 double (-90, 90] degrees 
Vessel heading 8 double [0, 360) degrees 
Vessel wander angle 8 double (-180, 180] degrees 


11 


 
Item Bytes Format Value Units 
Vessel track angle 4 float [0, 360) degrees 
Vessel speed 4 float [0, ) meters/second 
Vessel angular rate about longitudinal axis 4 float ( , ) degrees/second 
Vessel angular rate about transverse axis 4 float ( , ) degrees/second 
Vessel angular rate about down axis 4 float ( , ) degrees/second 
Vessel longitudinal acceleration 4 float ( , ) meters/second 2 
Vessel transverse acceleration 4 float ( , ) meters/second 2 
Vessel down acceleration 4 float ( , ) meters/second 2 
Alignment status 1 byte See Table 5 N/A 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Table 5: Group 1 alignment status 
Group 1 
Status 
Description 
0 Full navigation (User accuracies are met) 
1 Fine alignment is active (RMS heading error is less than 15 degrees) 
2 GC CHI 2 (alignment with GPS, RMS heading error is greater than 15 degrees) 
3 PC CHI 2 (alignment without GPS, RMS heading error is greater than 15 degrees) 
4 GC CHI 1 (alignment with GPS, RMS heading error is greater than 45 degrees) 
5 PC CHI 1 (alignment without GPS, RMS heading error is greater than 45 degrees) 
6 Coarse leveling is active 


12 


 
Group 1 
Status 
Description 
7 Initial solution assigned 
8 No valid solution 
Group 2: Vessel Navigation Performance Metrics 
This group contains vessel position, velocity and attitude performance metrics. The data in this 
group is valid for the position defined by the user-entered reference vessel lever arms. 
All data items in this group are given in RMS values. 
Table 6: Group 2: Vessel navigation performance metrics 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 2 N/A 
Byte count 2 ushort 80 bytes 
Time/Distance Fields 26 See Table 3 
North position RMS error 4 float [0, ) meters 
East position RMS error 4 float [0, ) meters 
Down position RMS error 4 float [0, ) meters 
North velocity RMS error 4 float [0, ) meters/second 
East velocity RMS error 4 float [0, ) meters/second 
Down velocity RMS error 4 float [0, ) meters/second 
Roll RMS error 4 float [0, ) degrees 
Pitch RMS error 4 float [0, ) degrees 
Heading RMS error 4 float [0, ) degrees 
Error ellipsoid semi-major 4 float [0, ) meters 
Error ellipsoid semi-minor 4 float [0, ) meters 
Error ellipsoid orientation 4 float (0, 360] degrees 
Pad 2 byte 0 N/A 


13 


 
Item Bytes Format Value Units 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 3: Primary GPS Status 
This group contains status data from the primary GPS receiver. The group length is variable, 
depending on the number of primary GPS receiver channels that report data. This group assumes 
that the primary GPS receiver contains up to 12 channels and therefore provides up to 12 channel 
status fields. Each channel status field has the format given in Table 8. The GPS receiver type 
field identifies the primary GPS receiver in POS MV from among the GPS receiver types listed 
in Table 11 that POS MV supports. The GPS status field comprises a 4 _byte array of status bits 
whose format depends on the GPS receiver type. 
Table 7: Group 3: Primary GPS status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 3 N/A 
Byte count 2 ushort 76 + 20 x (number of channels) bytes 
Time/Distance Fields 26 See Table 3 
Navigation solution status 1 byte See Table 9 N/A 
Number of SV tracked 1 byte [0, 12] N/A 
Channel status byte count 2 ushort [0, 240] bytes 
Channel status variable See Table 8 
HDOP 4 float ( , ) N/A 
VDOP 4 float ( , ) N/A 
DGPS correction latency 4 float [0, 999.9] seconds 
DGPS reference ID 2 ushort [0, 1023] N/A 
GPS/UTC week number 4 ulong [0, 1023] 
0 if not available 
week 
GPS/UTC time offset 8 double ( , ) seconds 


14 


 
Item Bytes Format Value Units 
GPS navigation message latency 4 float Number of seconds from the 
PPS pulse to the start of the 
GPS navigation data output 
seconds 
Geoidal separation 4 float ( , ) meters 
GPS receiver type 2 ushort See Table 11 N/A 
GPS status 4 ulong GPS summary status fields which depend on GPS receiver type. 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Table 8: GPS receiver channel status data 
Item Bytes Format Value Units 
SV PRN 2 ushort [1, 40] N/A 
Channel tracking status 2 ushort See Table 10 N/A 
SV azimuth 4 float [0, 360) degrees 
SV elevation 4 float [0, 90] degrees 
SV L1 SNR 4 float [0, ) dB 
SV L2 SNR 4 float [0, ) dB 
Table 9: GPS navigation solution status 
Status Value Description Expected Accuracy 
-1 Unknown N/A 
0 No data from Receiver N/A 
1 Horizontal C/A mode (unconstrained vertical 
position) 
75 meters 
2 3-dimension C/A mode 75 meters 
3 Horizontal DGPS mode (unconstrained vertical 
position) 
1 meter 
4 3-dimension DGPS mode 1 meter 


15 


 
Status Value Description Expected Accuracy 
5 Float RTK mode 0.25 meters 
6 Integer wide lane RTK mode 0.2 meters 
7 Integer narrow lane RTK mode 0.02 meters 
8 P-Code mode 10 meters 
Table 10: GPS channel status 
Channel 
Status 
Description 
0 L1 Idle 
1 Reserved 
2 L1 acquisition 
3 L1 Code lock 
4 Reserved 
5 L1 Phase lock (full performance tracking for L1-only receiver) 
6 L2 Idle 
7 Reserved 
8 L2 acquisition 
9 L2 Code lock 
10 Reserved 
11 L2 phase lock (full performance for L1/L2 receiver) 
Table 11: GPS receiver type 
GPS type Description 
0 No receiver 
1 to 7 Reserved
8 Trimble BD112
9 Trimble BD750
10 Reserved 
11 Trimble Force 5 GRAM-S 
12 Trimble BD132 
13 Trimble BD950
14 to 15 Reserved
16 Trimble BD960
17 Trimble BD982


16 


 
GPS type Description 
14 and up Reserved 
Table 12: Trimble BD950 GPS receiver status 
Item Bytes Format Failure 
Status of Receiver 4 chars Description Value 
SETT Setting time 
GETD Updating Health 
CAL1 Calibrating 
MEAS Static Survey 
KINE Kinematic Survey 
Group 4: Time-tagged IMU Data 
This group consists of the time-tagged IMU data that is suitable for import by POSPAC, 
Applanix' post-processing software package. U.S. and Canadian export control laws prohibit 
publication of the IMU data format. 
Table 13: Group 4: Time-tagged IMU data 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 4 N/A 
Byte count 2 ushort 60 bytes 
Time/Distance Fields 26 See Table 3
IMU Data 29 byte 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 

17 


 
Group 5: Event 1 
The time and distance fields in this group indicate the time and distance of Event 1 discrete 
signals that the POS MV receives. A client can use this message to attach GPS/UTC time to 
external events. 
Group 6: Event 2 
The time and distance fields in this group indicate the time and distance of Event 2 discrete 
signals that the POS MV receives. A client can use this message to attach GPS/UTC time to 
external events. 
Table 14: Group 5/6: Event 1/2 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 5 or 6 N/A 
Byte count 2 ushort 36 bytes 
Time/Distance Fields 26 See Table 3 
Event pulse number 4 ulong [0, ) N/A 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 7: PPS Time Recovery and Status 
The time and distance fields in this group indicate the time and distance of the PPS from the 
primary GPS receiver. The PPS count is the number of PPS messages since power-up and 
initialization of the GPS receivers. The time synchronization status field indicates the status of 
POS MV synchronization to the PPS time provided by the primary GPS receiver as follows: 
No synchronization indicates that the POS MV has not synchronized to GPS time. This is the 
case if the GPS receiver has not initialized and provided time recovery data to the POS MV. 
Synchronizing indicates that the POS MV is in the process of synchronizing to GPS time. This 
lasts on the order of 10-20 seconds as the POS MV establishes its internal clock offset and drift 
parameters. 
Fully synchronized indicates that the POS MV has established synchronization to GPS time 
with less than 10 microseconds error and is maintaining the synchronization once per second. 


18 


 
Using old offset indicates that the POS MV is using the last good clock offset to compute GPS 
times. The POS MV has either not received a PPS or time recovery message or has rejected 
erroneous GPS time synchronization data. 
This data provides for PPS time recovery of any of the time bases supported by the POS MV. It 
allows an external device to acquire GPS or UTC time, or to relate GPS time to POS MV time. 
Table 15: Group 7: PPS Time Recovery and Status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 7 N/A 
Byte count 2 ushort 36 bytes 
Time/Distance Fields 26 See Table 3 
PPS count 4 ulong [0, ) N/A 
Time synchronization status 1 byte 0 Not synchronized 
1 Synchronizing 
2 Fully synchronized 
3 Using old offset 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group End 2 char $# N/A 
Group 8: Reserved 
Group 9: GAMS Solution 
This group contains the GAMS solution and solution status. The following are descriptions of 
some of the group elements. 
The number of satellites field gives the number of satellites in the GAMS solution. The PDOP is 
the PDOP of the satellite constellation selected by GAMS. The computed antenna separation is 
the length of the baseline vector that GAMS computes. The solution status describes the status of 
the current GAMS solution. The PRN assignment fields give the satellite PRN assigned to each 
observables processing channel. The cycle slip flag identifies processing channels in which the 
ambiguity search algorithm has detected cycle slips. 


19 


 
The GAMS heading is the heading of the antenna baseline vector. The heading RMS error is 
estimated by GAMS based on the RMS uncertainties of the primary and secondary carrier phase 
measurements reported by the primary and secondary GPS receivers. 
Table 16: Group 9: GAMS Solution Status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 9 N/A 
Byte count 2 ushort 72 bytes 
Time/Distance Fields 26 See Table 3 
Number of satellites 1 ubyte N/A N/A 
A priori PDOP 4 float [0, 999] N/A 
Computed antenna separation 4 float [0, ) meters 
Solution Status 1 byte 0 fixed integer 
1 fixed integer test install data 
2 degraded fixed integer 
3 _floated ambiguity 
4 degraded floated ambiguity 
5 solution without install data 
6 solution from navigator attitude and install data 
7 no solution 
PRN assignment 12 byte Each byte contains 0-32 where 
0 = unassigned PRN 
1-40 = PRN assigned to channel 
Cycle slip flag 2 ushort Bits 0-11: (k-1) th bit set to 1 implies cycle slip 
in channel k. 
Example: Bit 3 set to 1 implies cycle slip in 
channel 4. 
Bits 12-15: not used. 


20 


 
Item Bytes Format Value Units 
GAMS heading 8 double [0,360) Degrees 
GAMS heading RMS error 8 double (0, ) Degrees 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 10: General Status and FDIR 
This group is used to output general and Fault Detection, Isolation and Reconfiguration (FDIR) 
status information. The POS Controller decodes and displays the sensor hardware status output 
in this group. The following is a brief description of group contents. 
General Status A contains bit-encoded status information from the following processes: 
integrated navigation, data logging and generic hardware. 
General Status B contains bit-encoded status information from the following processes: primary 
GPS data input, secondary GPS data input, auxiliary GPS data input, GAMS. 
General Status C contains bit-encoded information from the following processes: integrated 
navigation, gimbal data input, DMI data input, base GPS messages (RTCM, CMR, RTCA) input. 
FDIR Level 1, similar to a built-in test, reports problems in communications between the sensors 
and the PCS. 
FDIR Level 2, the direct reasonableness test, compares the sensor data against reasonable 
magnitude limits for the POS-instrumented Vessel. 
FDIR Level 3, the direct comparison test, compares IMU data against aiding sensor data and 
identifies unreasonable differences when they occur. 
FDIR Level 4, the residual test, monitors the measurement residuals from the Kalman filter and 
rejects measurements that fall outside a specified 95% confidence level. Consistent measurement 
rejection indicates a potential IMU or aiding sensor failure. 
FDIR Level 5, the indirect reasonableness test, monitors Kalman filter estimates of inertial 
sensor errors and installation errors. Soft sensor failures appear as slow increases in these errors. 
If a threshold is exceeded, a sensor failure is flagged. 


21 


 
Table 17: Group 10: General and FDIR status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10 N/A 
Byte count 2 ushort 56 Bytes 
Time/Distance Fields 26 See Table 3 
General Status A 4 ulong Coarse levelling active bit 0: set 
Coarse levelling failed bit 1: set 
Quadrant resolved bit 2: set 
Fine align active bit 3: set 
Inertial navigator initialised bit 4: set 
Inertial navigator alignment active bit 5: set 
Degraded navigation solution bit 6: set 
Full navigation solution bit 7: set 
Initial position valid bit 8: set 
Reference to Primary GPS Lever arms = 0 bit 9: set 
Reference to Sensor 1 Lever arms = 0 bit 10: set 
Reference to Sensor 2 Lever arms = 0 bit 11: set 
Logging Port file write error bit 12: set 
Logging Port file open bit 13: set 
Logging Port logging enabled bit 14: set 
Logging Port device full bit 15: set 
RAM configuration differs from NVM bit 16: set 
NVM write successful bit 17: set 
NVM write fail bit 18: set 
NVM read fail bit 19: set 
CPU loading exceeds 55% threshold bit 20: set 
CPU loading exceeds 85% threshold bit 21: set 
Spare bits: 22-31 


22 


 
Item Bytes Format Value Units 
General Status B 4 ulong User attitude RMS performance bit 0: set 
User heading RMS performance bit 1: set 
User position RMS performance bit 2: set 
User velocity RMS performance bit 3: set 
GAMS calibration in progress bit 4: set 
GAMS calibration complete bit 5: set 
GAMS calibration failed bit 6: set 
GAMS calibration requested bit 7: set 
GAMS installation parameters valid bit 8: set 
GAMS solution in use bit 9: set 
GAMS solution OK bit 10: set 
GAMS calibration suspended bit 11: set 
GAMS calibration forced bit 12: set 
Primary GPS navigation solution in use bit 13: set 
Primary GPS initialisation failed bit 14: set 
Primary GPS reset command sent bit 15: set 
Primary GPS configuration file sent bit 16: set 
Primary GPS not configured bit 17: set 
Primary GPS in C/A mode bit 18: set 
Primary GPS in Differential mode bit 19: set 
Primary GPS in float RTK mode bit 20: set 
Primary GPS in wide lane RTK mode bit 21: set 
Primary GPS in narrow lane RTK mode bit 22: set 
Primary GPS observables in use bit 23: set 
Secondary GPS observables in use bit 24: set 
Auxiliary GPS navigation solution in use bit 25: set 
Auxiliary GPS in P-code mode bit 26: set 
Auxiliary GPS in Differential mode bit 27: set 


23 


 
Item Bytes Format Value Units 
Auxiliary GPS in float RTK mode bit 28: set 
Auxiliary GPS in wide lane RTK mode bit 29: set 
Auxiliary GPS in narrow lane RTK mode bit 30: set 
Primary GPS in P-code mode bit 31: set 
General Status C 4 ulong Gimbal input ON bit 0: set 
Gimbal data in use bit 1: set 
DMI data in use bit 2: set 
ZUPD processing enabled bit 3: set 
ZUPD in use bit 4: set 
Position fix in use bit 5: set 
RTCM differential corrections in use bit 6: set 
RTCM RTK messages in use bit 7: set 
RTCA RTK messages in use bit 8: set 
CMR RTK messages in use bit 9: set 
IIN in DR mode bit 10: set 
IIN GPS aiding is loosely coupled bit 11: set 
IIN in C/A GPS aided mode bit 12: set 
IIN in RTCM DGPS aided mode bit 13: set 
IIN in code DGPS aided mode bit 14: set 
IIN in float RTK aided mode bit 15 set 
IIN in wide lane RTK aided mode bit 16: set 
IIN in narrow lane RTK aided mode bit 17: set 
Received RTCM Type 1 message bit 18: set 
Received RTCM Type 3 message bit 19: set 
Received RTCM Type 9 message bit 20: set 
Received RTCM Type 18 messages bit 21: set 
Received RTCM Type 19 messages bit 22: set 
Received CMR Type 0 message bit 23: set 


24 


 
Item Bytes Format Value Units 
Received CMR Type 1 message bit 24: set 
Received CMR Type 2 message bit 25: set 
Received CMR Type 94 message bit 26 set 
Received RTCA SCAT-1 message bit 27: set 
Spare bit: 28-31 
FDIR Level 1 status 4 ulong IMU-POS checksum error bit 0: set 
IMU status bit set by IMU bit 1: set 
Successive IMU failures bit 2: set 
IIN configuration mismatch failure bit 3: set 
Primary GPS not in Navigation mode bit 5: set 
Primary GPS not available for alignment bit 6: set 
Primary data gap bit 7: set 
Primary GPS PPS time gap bit 8: set 
Primary GPS time recovery data not received bit 9: set 
Primary GPS observable data gap bit 10: set 
Primary ephemeris data gap bit 11: set 
Primary GPS excessive lock-time resets bit 12: set 
Primary GPS missing ephemeris bit 13: set 
Primary GPS SNR failure bit 16: set 
Base GPS data gap bit 17: set 
Base GPS parity error bit 18: set 
Base GPS message rejected bit 19: set 
Secondary GPS data gap bit 20: set 
Secondary GPS observable data gap bit 21: set 
Secondary GPS SNR failure bit 22: set 
Secondary GPS excessive lock-time resets bit 23: set 
Auxiliary GPS data gap bit 25: set 
GAMS ambiguity resolution failed bit 26: set 


25 


 
Item Bytes Format Value Units 
Gimbal data gap bit 27: set 
DMI failed or is offline bit 28: set 
IIN WL ambiguity error bit 30: set 
IIN NL ambiguity error bit 31: set 
Spare bits: 4, 14, 
15, 24, 29 
FDIR Level 1 IMU failures 2 ushort Shows number of FDIR Level 1 Status IMU failures 
(bits 0 or 1) = Bad IMU Frames 
FDIR Level 2 status 2 ushort Inertial speed exceeds max bit 0: set 
Primary GPS velocity exceeds max bit 1: set 
Primary GPS position error exceeds max bit 2: set 
Auxiliary GPS position error exceeds max bit 3: set 
DMI speed exceeds max bit 4: set 
Spare bits: 5-15 
FDIR Level 3 status 2 ushort Spare bits: 0-15 
FDIR Level 4 status 2 ushort Primary GPS position rejected bit 0: set 
Primary GPS velocity rejected bit 1: set 
GAMS heading rejected bit 2: set 
Auxiliary GPS data rejected bit 3: set 
DMI data rejected bit 4: set 
Primary GPS observables rejected bit 5: set 
Spare bits: 6-15 
FDIR Level 5 status 2 ushort X accelerometer failure bit 0: set 
Y accelerometer failure bit 1: set 
Z accelerometer failure bit 2: set 
X gyro failure bit 3: set 
Y gyro failure bit 4: set 
Z gyro failure bit 5: set 
Excessive GAMS heading offset bit 6: set 


26 


 
Item Bytes Format Value Units 
Excessive primary GPS lever arm error bit 7: set 
Excessive auxiliary 1 GPS lever arm error bit 8: set 
Excessive auxiliary 2 GPS lever arm error bit 9: set 
Excessive POS position error RMS bit10:set 
Excessive primary GPS clock drift bit11:set 
Spare bits: 12-15 
Pad 0 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
max = maximum 
Group 11: Secondary GPS Status 
This group contains status data from the secondary GPS receiver. The group length is variable, 
depending on the number of secondary GPS receiver channels that report data. This group 
assumes that the secondary GPS receiver contains up to 12 channels and therefore provides 12 
channel status fields. Each channel status field has the format given in Table 8. The GPS 
navigation message latency field contains the time between the PPS pulse and the start of the 
GPS navigation data output 
Table 18: Group 11: Secondary GPS status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 11 N/A 
Byte count 2 ushort 76 + 20 x (number of 
channels) 
Bytes 
Time/Distance Fields 26 See Table 3 
Navigation solution status 1 byte See Table 9 N/A 
Number of SV tracked 1 byte [0, 12] N/A 
Channel status byte count 2 ushort [0, 240] Bytes 
Channel status variable See Table 8 


27 


 
Item Bytes Format Value Units 
HDOP 4 float (0, ) N/A 
VDOP 4 float (0, ) N/A 
DGPS correction latency 4 float [0, 99.9] Seconds 
DGPS reference ID 2 ushort [0, 1023] N/A 
GPS/UTC week number 4 ulong [0, 1023] 0 if not available Week 
GPS/UTC time offset 8 double ( , 0] (GPS time - UTC time) Seconds 
GPS navigation message latency 4 float [0, ) Seconds 
Geoidal separation 4 float ( , ) Meters 
GPS receiver type 2 ushort See Table 11 N/A 
GPS status 4 ulong GPS summary status fields which depend 
on GPS receiver type. 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 12: Auxiliary 1 GPS Status 
This group contains data from an optional auxiliary 1 external GPS receiver. The group is 
variable in length because it is dependent upon the number of satellites that the auxiliary 1 GPS 
receiver is tracking. This group assumes that the auxiliary 1 GPS receiver contains up to 12 
channels and therefore provides 12 channel status fields. The centre section of this group grows 
with increasing number of satellites tracked. 
Group 13: Auxiliary 2 GPS Status 
This group contains data from an optional auxiliary 2 external GPS receiver. The group has the 
same format as Group 12. Table 19 specifies the format for both Groups 12 and 13 


28 


 
Table 19: Group 12/13: Auxiliary 1/2 GPS status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 12 or 13 N/A 
Byte count 2 ushort 72 + 20 x (number of 
channels) 
Bytes 
Time/Distance Fields 26 See Table 3 
Navigation solution status 1 byte See Table 9 N/A 
Number of SV Tracked 1 byte [0, 40] N/A 
Channel status byte count 2 ushort [0, ) Bytes 
Channel status variable See Table 8 
HDOP 4 float (0, ) N/A 
VDOP 4 float (0, ) N/A 
DGPS correction latency 4 float (0, ) Seconds 
DGPS reference ID 2 ushort [0, 1023] N/A 
GPS/UTC week number 4 ulong [0, 1023] 
0 if not available 
Week 
GPS time offset 8 double ( , 0] Seconds (GPS time - UTC time) 
GPS navigation message latency 4 float [0, ) Seconds 
Geoidal separation 4 float N/A Meters 
NMEA messages Received 2 ushort Bit (set) NMEA Message 
0 GGA (GPS position) 
1 GST (noise statistics) 
2 GSV (satellites in view) 
3 GSA (DOP & active SVs) 
4-15 Reserved 


29 


 
Item Bytes Format Value Units 
Aux 1/2 in Use 1 1 byte 0 Not in use 
1 In use 
N/A 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
1 Group 12/13 Aux in Use fields will not be set in use simultaneously. 
Group 14: Calibrated Installation Parameters 
This group lists the calibrated installation parameters that the POS MV computes during 
Navigate mode when the Calibrate function is active. The group includes a Figure of Merit 
(FOM) for each set of parameters that the user can choose to calibrate. The FOM ranges from 
0 to 100 and describes the percentage of a complete calibration that a calibration has achieved. A 
FOM equal to 0 indicates one of two possibilities: 
#  
A  parameter  is  not  being  calibrated  because  the  user  did  not  flag  the  parameter  for  
calibration in Message 57: Installation calibration control (see Section 0).  
#  
A parameter is not calibrated during a calibration of the parameter because the Vessel has  
not executed the required dynamics to effect the calibration.  
Table 20: Group 14: Calibrated installation parameters 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 14 N/A 
Byte count 2 ushort 116 Bytes 
Time/Distance Fields 26 See Table 3 
Calibration status 2 ushort See Table 21 for bitfield 
Reference to Primary GPS X lever arm 4 float ( , ) Meters 
Reference to Primary GPS Y lever arm 4 float ( , ) Meters 
Reference to Primary GPS Z lever arm 4 float ( , ) Meters 
Reference to Primary GPS lever arm calibration FOM 2 ushort [0, 100] N/A 
Reference to Auxiliary 1 GPS X lever arm 4 float ( , ) Meters 


30 


 
Item Bytes Format Value Units 
Reference to Auxiliary 1 GPS Y lever arm 4 float ( , ) Meters 
Reference to Auxiliary 1 GPS Z lever arm 4 float ( , ) Meters 
Reference to Auxiliary 1 GPS lever arm calibration FOM 2 ushort [0, 100] N/A 
Reference to Auxiliary 2 GPS X lever arm 4 float ( , ) Meters 
Reference to Auxiliary 2 GPS Y lever arm 4 float ( , ) Meters 
Reference to Auxiliary 2 GPS Z lever arm 4 float ( , ) Meters 
Reference to Auxiliary 2 GPS lever arm calibration FOM 2 ushort [0, 100] N/A 
Reference to DMI X lever arm 4 float ( , ) Meters 
Reference to DMI Y lever arm 4 float ( , ) Meters 
Reference to DMI Z lever arm 4 float ( , ) Meters 
Reference to DMI lever arm calibration FOM 2 ushort [0, 100] N/A 
DMI scale factor 4 float ( , ) % 
DMI scale factor calibration FOM 2 ushort [0, 100] N/A 
Reference to DVS X lever arm 4 float ( , ) Meters 
Reference to DVS Y lever arm 4 float ( , ) Meters 
Reference to DVS Z lever arm 4 float ( , ) meters 
Reference to DVS lever arm calibration 
FOM 
2 ushort [0, 100] N/A 
DVS scale factor 4 float ( , ) % 
DVS scale factor calibration FOM 2 ushort [0, 100] N/A 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 


31 


 
Table 21: IIN Calibration Status 
Bit Set Status Description 
0 Reference to Primary GPS lever arm calibration is in progress 
1 Reference to Auxiliary 1 GPS lever arm calibration is in progress 
2 Reference to Auxiliary 2 GPS lever arm calibration is in progress 
3 Reference to DMI lever arm calibration is in progress 
4 DMI scale factor calibration is in progress 
5 Reference to DVS lever arm calibration is in progress 
6 Reference to Position Fix lever arm calibration is in progress 
7 Reserved 
8 Reference to Primary GPS lever arm calibration is completed 
9 Reference to Auxiliary 1 GPS lever arm calibration is completed 
10 Reference to Auxiliary 2 GPS lever arm calibration is completed 
11 Reference to DMI lever arm calibration is completed 
12 DMI scale factor calibration is completed 
13 Reference to DVS lever arm calibration is completed 
14 Reference to Position Fix lever arm calibration is completed 
15 Reserved 
Group 15: Reserved 
Group 16: Reserved 
Group 17: User Time Status 
This group contains status information about user time synchronization. 
Table 22: Group 17: User Time Status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 17 N/A 


32 


 
Item Bytes Format Value Units 
Byte count 2 ushort 40 Bytes 
Time/Distance Fields 26 See Table 3 
Number of Time Synch message rejections 4 ulong [0, ) N/A 
Number of User Time resynchronizations 4 ulong [0, ) N/A 
User time valid 1 byte 1 or 0 N/A 
Time Synch message received 1 byte 1 or 0 N/A 
Pad 0 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 20: IIN Solution Status 
This group contains the IIN observables processing status and relevant data. The following are 
descriptions of some of the fields. 
The number of satellites field gives the number of satellites in the IIN solution. The a priori 
PDOP is the PDOP of the satellite constellation selected by IIN before processing. The baseline 
length is the computed distance between the primary GPS antenna and the reference GPS 
antenna. The IIN processing status describes the status of the current IIN solution. The 12 PRN 
assignment fields give the satellite PRN used in each observables processing channel in the IIN 
solution. The L1 cycle slip flag field contains a bit array whose bits when set, indicate an L1 
cycle slips in the observables processing channels. The L2 cycle slip flag field contains a bit 
array whose bits when set, indicate L2 cycle slips in observables processing channels. In each bit 
array, bit (k-1) indicates the cycle slip status of processing channel k. 
Table 23: Group 20: IIN solution status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 20 N/A 
Byte count 2 ushort 60 Bytes 
Time/Distance Fields 26 See Table 3 
Number of satellites 2 ushort [0, 12] N/A 
A priori PDOP 4 float [0, 999] N/A 


33 


 
Item Bytes Format Value Units 
Baseline length 4 float [0, ) Meters 
IIN processing status 2 ushort 1 Fixed Narrow Lane RTK 
2 Fixed Wide Lane RTK 
3 Float RTK 
4 Code DGPS 
5 RTCM DGPS 
6 Autonomous (C/A) 
7 GPS navigation solution 
8 No solution 
PRN assignment 12 12 byte Each byte contains 0-40 where 
0 = unassigned PRN 
1-40 = PRN assigned to channel 
L1 cycle slip flag 2 ushort Bits 0-11: (k-1) th bit set to 1 implies L1 cycle 
slip in channel k PRN. Example: 
Bit 3 set to 1 implies an L1 cycle 
slip in channel 4. 
Bits 12-15: not used. 
L2 cycle slip flag 2 ushort Bits 0-11: (k-1) th bit set to 1 implies L2 cycle 
slip in channel k PRN. Example: 
Bit 3 set to 1 implies an L2 cycle 
slip in channel 4. 
Bits 12-15: not used. 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 21: Base GPS 1 Modem Status 
The base GPS process may receive differential corrections from a base station via a modem 
connected to one of the POS MV serial ports. This group contains status information about the 
modem connected to the serial port associated with the Base GPS 1 input. 


34 


 
Group 22: Base GPS 2 Modem Status 
This group contains status information about the modem connected to the serial port associated 
with the Base GPS 2 input. 
Table 24: Group 21/22: Base GPS 1/2 Modem Status 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 21 or 22 N/A 
Byte count 2 ushort 116 Bytes 
Time/Distance Fields 26 See Table 3 
Modem response 16 char N/A N/A 
Connection status 48 char N/A N/A 
Number of redials per disconnect 4 ulong [0, ) N/A 
Maximum number of redials per disconnect 4 ulong [0, ) N/A 
Number of disconnects 4 ulong [0, ) N/A 
Data gap length 4 ulong [0, ) N/A 
Maximum data gap length 4 ulong [0, ) N/A 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 23: Auxiliary 1 GPS Display Data 
This group contains the auxiliary 1 GPS receiver data stream, containing the NMEA strings 
requested by the PCS from the receiver plus any other bytes that the receiver inserts into the 
stream. The length of this group is variable. It is identical to group 10007 except for the time2 
restriction and the fact it is intended for display only. 
Group 24: Auxiliary 2 GPS Display Data 
This group contains the auxiliary 2 GPS receiver data stream, containing the NMEA strings 
requested by the PCS from the receiver plus any other bytes that the receiver inserts into the 
stream. The length of this group is variable. It is identical to group 10008 except for the time2 
restriction and the fact it is intended for display only. 


35 


 
Table 25: Group 23/24: Auxiliary 1/2 GPS raw display data 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10007 or 10008 N/A 
Byte count 2 ushort variable Bytes 
Time/Distance Fields 26 See Table 3 
Reserved 6 byte N/A N/A 
Variable message byte count 2 ushort [0, ) Bytes 
Auxiliary GPS raw data variable char N/A N/A 
Pad 0-3 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 25: Reserved 
Group 26: Reserved 
Group 99: Versions and Statistics 
This group provides feedback of the current statistics and software and hardware version 
numbers of the POS MV. This group contains operational statistics such as total hours of 
operation, number of runs, average run length and longest run. 
Table 26: Group 99: Versions and statistics 
Item Bytes Format Value Units 
Group Start 4 char $GRP N/A 
Group ID 2 ushort 99 N/A 
Byte Count 2 ushort 332 Bytes 
Time/Distance Fields 26 See Table 3 
Table 3 
System version 120 char Product - Model, Version, 
Serial Number, 
Hardware version, 


36 


 
Item Bytes Format Value Units 
Software release version - Date, 
ICD release version, 
Operating system version, 
IMU type, 
Primary GPS type (Table 11), 
Secondary GPS type (Table 11), 
DMI type, 
Gimbal type 
[,Option mnemonic-expiry time] 
[,Option mnemonic-expiry time] 
..... 
Example: 
MV-320,VER4,S/N123,HW1.80-7, 
SW03.20-Aug3/05,ICD01.00, 
OS425B,IMU2,PGPS13,SGPS13, 
DMI0,GIM0,RTK-75 
N/A 
Primary GPS version 80 char Available information is displayed, eg: 
Model number 
Serial number 
Hardware configuration version 
Software release version 
Release date 
Secondary GPS version 80 char Available information is displayed, eg: 
Model number 
Serial number 
Hardware configuration version 
Software release version 


37 


 
Item Bytes Format Value Units 
Release date 
Total hours 4 float [0, ) 0.1 hour resolution Hours 
Number of runs 4 ulong [0, ) N/A 
Average length of run 4 float [0, ) 0.1 hour resolution Hours 
Longest run 4 float [0, ) 0.1 hour resolution Hours 
Current run 4 float [0, ) 0.1 hour resolution Hours 
Pad 2 short 0 N/A 
Checksum 2 ushort N/A N/A 
Group End 2 char $# N/A 
Group 102: Sensor 1 Position, Velocity, Attitude, Heave & Dynamics 
This group contains position, velocity, attitude, track, speed and dynamics data for the sensor 1 
position. 
Group 103: Sensor 2 Position, Velocity, Attitude, Heave & Dynamics 
This group contains position, velocity, attitude, track, speed and dynamics data for the sensor 2 
position. 
Table 27: Group 102/103: Sensor 1/2 Position, Velocity, Attitude, Heave & Dynamics 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 102 or 103 N/A 
Byte count 2 ushort 128 Bytes 
Time/Distance Fields 26 See Table 3 
Latitude 8 double (-90, 90] Deg 
Longitude 8 double (-180, 180] Deg 
Altitude 8 double ( , ) M 
Along track velocity 4 float ( , ) m/s 
Across track velocity 4 float ( , ) m/s 


38 


 
Item Bytes Format Value Units 
Down velocity 4 float ( , ) m/s 
Roll 8 double (-180, 180] Deg 
Pitch 8 double (-90, 90] Deg 
Heading 8 double [0, 360) Deg 
Wander angle 8 double (-180, 180] Deg 
Heave 1 4 float ( , ) M 
Angular rate about longitudinal axis 4 float ( , ) deg/s 
Angular rate about transverse axis 4 float ( , ) deg/s 
Angular rate about down axis 4 float ( , ) deg/s 
Longitudinal acceleration 4 float ( , ) m/s 2 
Transverse acceleration 4 float ( , ) m/s 2 
Down acceleration 4 float ( , ) m/s 2 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
1 Heave is output in the gravity direction from a local level frame located at the sensor 1 or 2 position. The Heave 
sign is positive down. 
Group 104: Sensor 1 Position, Velocity, and Attitude Performance Metrics 
This group contains sensor 1 position, velocity and attitude performance metrics. All data in this 
group are RMS values. 
Group 105: Sensor 2 Position, Velocity, and Attitude Performance Metrics 
This group contains sensor 2 position, velocity and attitude performance metrics. All data in this 
group are RMS values. 


39 


 
Table 28: Group 104/105: Sensor 1/2 Position, Velocity, and Attitude Performance Metrics 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 104 or 105 N/A 
Byte count 2 ushort 68 Bytes 
Time/Distance Fields 26 See Table 3 
N position RMS 4 float [0, ) M 
E position RMS 4 float [0, ) M 
D position RMS 4 float [0, ) M 
Along track velocity RMS error 4 float [0, ) m/s 
Across track velocity RMS error 4 float [0, ) m/s 
Down velocity RMS error 4 float [0, ) m/s 
Roll RMS error 4 float [0, ) Deg 
Pitch RMS error 4 float [0, ) Deg 
Heading RMS error 4 float [0, ) Deg 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 110: MV General Status & FDIR 
This group contains MV specific status bits. It is an extension of the Core group 10 information. 
Table 29: Group 110: MV General Status & FDIR 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 110 N/A 
Byte count 2 ushort 32 Bytes 


40 


 
Item Bytes Format Value Units 
Time/Distance Fields 26 See Table 3 
General Status 4 ulong User logged in bit 0: set -- doc error; said 2 byte ulong, but need 32 bits (4 byte ulong)  
reserved bit 1 to 9 
TrueZ Active bit 10: set 
TrueZ Ready bit 11: set 
TrueZ In Use bit 12: set 
Reserved bit 13 to 31 
Pad 2 byte 0 -- doc error, with general status as 4 then pad needs to be 2 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 111: Heave & True Heave Data 
This group contains data from the True Heave calculations (delayed in time), along with time- 
matched Heave (Real-time) data. Both the Real-Time and True Heave values are in the gravity 
direction from a local level frame located at the Sensor 1 position. The Heave sign is positive 
down. 
Table 30: Group 111: Heave & True Heave Data 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 111 N/A 
Byte count 2 ushort 76 Bytes 
Time/Distance Fields 26 See Table 3 
True Heave 4 float ( , ) M 
True Heave RMS 4 float [0, ) M 
Status 4 ulong True Heave Valid bit 0: set 
Real-time Heave Valid bit 1: set 
reserved bit 2 to 31 
Heave 4 float ( , ) M 
Heave RMS 4 float [0, ) M 


41 


 
Item Bytes Format Value Units 
Heave Time 1 8 double N/A Sec 
Heave Time 2 8 double N/A Sec 
Rejected IMU Data Count 4 ulong [0, ) N/A 
Out of Range IMU Data Count 4 ulong [0, ) N/A 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 112: NMEA Strings 
This group contains a copy of the NMEA strings output from the user selected COM port. This 
group will be available for output at the same rate selected for NMEA output on the COM port. 
Note that the user must select this group for output on the desired Data in order to receive the 
data. 
Table 31: Group 112: NMEA Strings 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 112 N/A 
Byte count 2 ushort variable Bytes 
Time/Distance Fields 26 See Table 3 
Variable group byte count 2 ushort [0, ) N/A- error in docs list this as 2 byte float, guessing it should be a ushort
NMEA strings variable char N/A N/A 
Pad 0-3 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 113: Heave & True Heave Performance Metrics 
This group contains quality data from the True Heave calculations. 


42 


 
Table 32: Group 113: Heave & True Heave Performance Metrics 
Item Byte 
s 
Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 113 N/A 
Byte count 2 ushort 68 Bytes 
Time/Distance Fields 26 See Table 3 
Heave Time 1 8 double N/A Sec 
Quality Control 1 8 double N/A N/A 
Quality Control 2 8 double N/A N/A 
Quality Control 3 8 double N/A N/A 
Status 4 ulong Quality Control 1 Valid bit 0: set 
Quality Control 2 Valid bit 1: set 
Quality Control 3 Valid bit 2: set 
Reserved bit 3 to 31 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 114: TrueZ & TrueTide Data 
This group contains altitude data from the delayed TrueZ and delayed TrueTide calculations 
along with the time-matched real-time data. The real-time TrueZ, delayed TrueZ and delayed 
TrueTide values are in the gravity direction from a local level frame located at the Sensor 1 
position. The real-time TrueTide values are in the gravity direction from a local level frame 
located at the Vessel position. 


43 


 
Table 33: Group 114: TrueZ & TrueTide Data 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 114 N/A 
Byte count 2 ushort 76 Bytes 
Time/Distance Fields 26 See Table 3 
Delayed TrueZ 4 float ( , ) M 
Delayed TrueZ RMS 4 float [0, ) M 
Delayed TrueTide 4 float ( , ) M 
Status 4 ulong Delayed TrueZ Valid bit 0: set 
Real-time TrueZ Valid bit 1: set 
Reserved bit 2 to 31 
TrueZ 4 float ( , ) M 
TrueZ RMS 4 float [0, ) M 
TrueTide 4 float ( , ) M 
TrueZ Time 1 8 double N/A Sec 
TrueZ Time 2 8 double N/A Sec 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
3.3.2 Raw Data Groups 
Group 10001: Primary GPS Data Stream 
This group contains the primary GPS receiver data as output by the receiver. The length of this 
group is variable. The GPS data stream is packaged into the group as it is received, irrespective 
of GPS message boundaries. The messages contained in this group depends on the primary GPS 
receiver that the POS MV uses. If a data extraction process concatenates the data components 
from these groups into a single file, then the resulting file will be the same as a file of data 
recorded directly from the primary GPS receiver. 


44 


 
Table 34: Group 10001: Primary GPS data stream 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10001 N/A 
Byte count 2 ushort variable Bytes 
Time/Distance Fields 26 See Table 3 
GPS receiver type 2 ushort See Table 11 N/A 
Reserved 4 long N/A N/A 
Variable message byte count 2 ushort [0, ) Bytes 
GPS Receiver raw data variable char N/A N/A 
Pad 0-3 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 10002: Raw IMU Data 
This group contains the IMU data as output by the IMU directly. The length of this group is 
variable. 
The IMU header field contains 6 characters of which the first 4 are ``$IMU'' and the last two are 
the IMU type number in ASCII format (example: ``$IMU01'' identifies IMU type 1). The Data 
checksum is a 16-bit sum of the IMU data. The POS MV provides this checksum in addition to 
the possible IMU-generated checksums in the IMU data field. U.S. and Canadian export control 
laws prevent the publication of the IMU data field formats for the different IMU's that the 
POS MV supports. 
Table 35: Group 10002: Raw IMU LN200 data 
Item Bytes Forma 
t 
Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10002 N/A 
Byte count 2 ushort Variable Bytes 
Time/Distance Fields 26 See Table 3 
IMU header 6 char $IMUnn where nn identifies the IMU 
type.


45 


 
Item Bytes Forma 
t 
Value Units 
Variable message byte count 2 ushort [0, ) Bytes 
X delta velocity  2  short  2-14 metres/sec/pulse count  pulse counts  
Yneg delta velocity  2  short  2-14 metres/sec/pulse count  pulse counts  
Zneg delta velocity  2  short  2-14 metres/sec/pulse count  pulse counts  
X delta theta  2  short  2-18 radians/pulse count  pulse counts  
Yneg delta theta  2  short  2-18 radians/pulse count  pulse counts  
Zneg delta theta  2  short  2-18 radians/pulse count  pulse counts  
IMU Status Summary  2  short  N/A  N/A  
Mode bit/MUX ID  2  short  N/A  N/A  
MUX data word  2  short  N/A  N/A  
X raw gyro count  2  short  1 pulse/pulse count  pulse counts  
Y raw gyro count  2  short  1 pulse/pulse count  pulse counts  
Z raw gyro count  2  short  1 pulse/pulse count  pulse counts  
IMU Checksum  2  short  N/A  N/A  
Data Checksum 2 short N/A N/A 
Pad 0 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 10003: Raw PPS 
This group contains the raw PPS data that the POS MV generates. The time of the PPS is given 
in the Time/Distance fields. 
Table 36: Group 10003: Raw PPS 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10003 N/A 
Byte count 2 ushort 36 Bytes 
Time/Distance Fields 26 See Table 3 
PPS pulse count 4 Ulong [0, ) N/A 
Pad 2 Byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 10004: Raw Event 1 
This group contains the raw Event 1 data that the POS MV generates. The time of the event 
pulse count is given in the Time/Distance fields. 
Group 10005: Raw Event 2 
This group contains the raw Event 2 data that the POS MV generates. The time of the event 
pulse count is given in the Time/Distance fields. 


46 


 
Table 37: Group 10004/10005: Raw Event 1/2 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10004 or 10005 N/A 
Byte count 2 ushort 36 Bytes 
Time/Distance Fields 26 See Table 3 
Event 1 pulse count 4 ulong [0, ) N/A 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 10006: Reserved 
Group 10007: Auxiliary 1 GPS Data Stream 
This group contains the auxiliary 1 GPS receiver data stream, containing the NMEA strings 
requested by the PCS from the receiver plus any other bytes that the receiver inserts into the 
stream. The length of this group is variable. If a data extraction process concatenates the data 
components from these groups into a single file, then the resulting file will be the same as an 
ASCII file of NMEA strings recorded directly from the auxiliary 1 GPS receiver. 
Group 10008: Auxiliary 2 GPS Data Stream 
This group contains the auxiliary 2 GPS receiver data stream, containing the NMEA strings 
requested by the PCS from the receiver plus any other bytes that the receiver inserts into the 
stream. The length of this group is variable. If a data extraction process concatenates the data 
components from these groups into a single file, then the resulting file will be the same as an 
ASCII file of NMEA strings recorded directly from the auxiliary 2 GPS receiver. 
Table 38: Group 10007/10008: Auxiliary 1/2 GPS data streams 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10007 or 10008 N/A 
Byte count 2 ushort variable Bytes 
Time/Distance Fields 26 See Table 3 
reserved 2 byte N/A N/A 


47 


 
Item Bytes Format Value Units 
reserved 4 long N/A N/A 
Variable message byte count 2 ushort [0, ) Bytes 
Auxiliary GPS raw data variable char N/A N/A 
Pad 0-3 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 10009: Secondary GPS Data Stream 
This group contains the secondary GPS receiver data as output by the receiver. The length of this 
group is variable. The GPS data stream is packaged into the group as it is received, irrespective 
of GPS message boundaries. The messages contained in this group depends on the secondary 
GPS receiver that the POS MV uses. If a data extraction process concatenates the data 
components from these groups into a single file, then the resulting file will be the same as a file 
of data recorded directly from the secondary GPS receiver. 
Table 39: Group 10009: Secondary GPS data stream 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10009 N/A 
Byte count 2 ushort Variable Bytes 
Time/Distance Fields 26 See Table 3 
GPS receiver type 2 ushort See Table 11 N/A 
Reserved 4 byte N/A N/A 
Variable message byte count 2 ushort [0, ) Bytes 
GPS Receiver Message variable char N/A N/A 
Pad 0-3 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 
Group 10010: Reserved 


48 


 
Group 10011: Base GPS 1 Data Stream 
This group contains the message data stream the POS MV receives as differential corrections. 
The length of this group is variable and dependent on the messages received by the PCS. If a 
data extraction process concatenates the data components from this group into a single file, then 
the resulting file will be the same as a file of data captured from the serial data stream connected 
to a differential corrections port. 
Group 10012: Base GPS 2 Data Stream 
This group contains the message data stream the POS MV receives as differential corrections. 
The length of this group is variable and dependent on the messages received by the PCS. If a 
data extraction process concatenates the data components from this group into a single file, then 
the resulting file will be the same as a file of data captured from the serial data stream connected 
to a differential corrections port. 
Table 40: Group 10011/10012: Base GPS 1/2 data stream 
Item Bytes Format Value Units 
Group start 4 char $GRP N/A 
Group ID 2 ushort 10011 or 10012 N/A 
Byte count 2 ushort variable Bytes 
Time/Distance Fields 26 See Table 3 
reserved 6 byte N/A N/A 
Variable message byte count 2 ushort [0, ) Bytes 
Base GPS raw data variable byte N/A N/A 
Pad 0-3 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Group end 2 char $# N/A 


49 


 
4 Message Input and Output 
4.1 Introduction 
The POS MV uses the Control Port to receive control messages from the POS Controller, (a 
user's custom software application or MV POSView), and to acknowledge successful receipt of 
the messages. The Control Port is bi-directional and uses the TCP/IP protocol to communicate 
with the control and display software. 
Each message sent to POS MV causes an action to be initiated. When POS MV receives and 
validates a message, it replies to the POS Controller by sending an `Acknowledge' message, 
Message ID 0, on the Control Port over which it received the message. The Acknowledge 
message protocol is defined below. The purpose of the Acknowledge message is to inform the 
POS Controller that the POS MV has received a message and has either accepted or rejected it. 
In addition, POS MV also outputs a message echo on each of the Display and Data ports to 
indicate the current system state, regardless of whether the action was successful or not. 
4.2 Message Output Data Rates 
The POS MV periodically generates copies (echos) of received control message or internally 
generated messages at maximum frequencies described in Table 41. This output allows a POS 
Controller to monitor the current state of the configuration of the POS MV. The content of the 
output messages reflects the current state of thePOS MV. Thus, if the state of the system 
changes, as part of the normal operations, it is reflected in the next set of echo messages from the 
POS MV. 
4.2.1 Message Numbering Convention 
All POS products use the following message numbering convention. POS MV outputs the 
message categories shown. Reserved message numbers are assigned to other products or 
previous versions of POS products. In particular, POS MV V3 core messages occupy the 
namespace range 1-19. 
0 Core - Acknowledge message 
1 - 19 Core - Reserved 
20 - 49 Core - Installation parameter set-up messages 
50 - 79 Core - Processing control messages 
80 - 89 Core - Reserved 
90 - 99 Core - Program control override messages 
100 - 199 POS MV specific messages 
200 - 19999 Reserved 


50 


 
20000 - 20099 Core - Diagnostic messages 
20100 - 20199 POS MV specific diagnostic messages 
20200 - 29999 Reserved 
The Acknowledge message is the message that POS MV sends as a reply to a message from the 
POS Controller. It is described in detail in Section 0 of this document. 
Installation parameter set-up messages comprise all messages that the user sends via the POS 
Controller to implement a particular installation of the POS MV. The POS Controller would not 
normally send these messages once the installation is completed. Messages 20-29 are signal 
processing parameter set-up messages. These specify sensor installation parameters and user 
accuracies. Messages 30-49 are hardware control messages. These specify communication 
control parameters and real-time message selections. 
Processing control messages comprise all messages that the user requires to control and 
monitor POS MV during a navigation session. These include navigation mode control, data 
acquisition control and possibly initialization of navigation quantities if no GPS signal is 
available. 
Program control override messages permits the user to directly control functions that POS MV 
normally performs automatically. The user would send a program control override message only 
under special circumstances. For example, the user may believe that the primary or secondary 
GPS receiver has lost its configuration and chooses to manually command the POS MV to re- 
configure the receiver. This message category also includes control messages that alter the 
normal operation or output of POS MV for diagnosis purposes. The actions induced by these 
messages are not part of the normal POS MV operation and should be interpreted only by 
qualified Applanix service personnel. 
Table 41: Control messages output data rates 
Display Port (Hz) Real-Time Data Port 
(Hz) 
Logging Data Port 
(Hz) 
Message Contents 
Stby Nav Stby Nav Stby Nav 
0 Acknowledge - - - - - - 
Installation Parameter Set-up Messages 
20 General installation parameters 1 1.0 1.0 0.1 0.1 0.1 0.1 
21 GAMS installation parameters 1 1.0 1.0 0.1 0.1 0.1 0.1 
22 Reserved 
23 Reserved 
24 User accuracy specifications 1 1.0 1.0 0.1 0.1 0.1 0.1 
25 Reserved 
30 Primary GPS set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 


51 


 
Display Port (Hz) Real-Time Data Port 
(Hz) 
Logging Data Port 
(Hz) 
Message Contents 
Stby Nav Stby Nav Stby Nav 
31 Secondary GPS set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
32 Set POS IP address 1.0 1.0 0.1 0.1 0.1 0.1 
33 Event discretes set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
34 COM port set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
35 See message 135 
36 See message 136 
37 Base GPS 1 Set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
38 Base GPS 2 Set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
40 Reserved - - - - - - 
41 Reserved - - - - - - 
Processing Control Messages 
50 Navigation mode control 1.0 1.0 1.0 0.1 0.1 0.1 
51 Display Port control 1 1.0 1.0 1.0 0.1 0.1 0.1 
52 Real-Time Data Port control 1 1.0 1.0 1.0 0.1 0.1 0.1 
53 Reserved - - - - - - 
54 Save/restore parameters command - - - - - - 
55 Time synchronization control 1.0 1.0 1.0 0.1 0.1 0.1 
56 General data 1.0 1.0 1.0 0.1 0.1 0.1 
57 Installation calibration control - - - - - - 
58 GAMS calibration control - - - - - - 
60 Reserved - - - - - - 
61 Logging Data Port control 1 1.0 1.0 1.0 0.1 0.1 0.1 
Program Control Override Messages 
90 Program control - - - - - - 
91 GPS control - - - - - - 
92 Reserved - - - - - - 
93 Reserved - - - - - - 
POS MV Specific Messages 
105 Analog port set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
106 Heave filter set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
111 Password control - - - - - - 


52 


 
Display Port (Hz) Real-Time Data Port 
(Hz) 
Logging Data Port 
(Hz) 
Message Contents 
Stby Nav Stby Nav Stby Nav 
120 Sensor parameter set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
121 Vessel Installation parameters 1 1.0 1.0 0.1 0.1 0.1 0.1 
135 NMEA output set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
136 Binary output set-up 1 1.0 1.0 0.1 0.1 0.1 0.1 
POS MV Specific Diagnostic Control Messages 
20102 Binary output diagnostics set-up 1.0 1.0 0.1 0.1 0.1 0.1 
20103 Analog port diagnostics set-up 1.0 1.0 0.1 0.1 0.1 0.1 
1 Message is saved in NVM 
4.2.2 Compatibility with Previous POS Products 
The compatibility of POS MV V4 messages with POS MV V3 products is given as follows: 
# 
The POS MV V4 message format is the same as that of POS MV V3 products. 
# 
The POS MV V4 Message 0 is the same as that of POS MV V3 products. 
# 
The POS MV V4 message namespace occupies 20-98, which does not intersect the core 
message namespace for POS MV V3 products. Several POS MV V4 messages either are 
the same or command similar actions or functions as POS MV V3 core messages in the 
namespace 1-19. This separation of the message namespace allows for the unrestricted 
re-organization of the POS MV V4 messages and re-design of their content without 
creating compatibility problems. 
4.3 Message Format 
4.3.1 Introduction 
All control messages have the format described in Table 42. The messages consist of a header, 
message body and footer. The next section describes the specific message formats. 
Table 42: Message format 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort Message dependent N/A 
Byte count 2 ushort Message dependent N/A 


53 


 
Item Bytes Format Value Units 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Message body Message dependent format and content. 
Pad 0 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
The header consists of the following components: 
# 
an ASCII string ($MSG) 
# 
unique message identifier 
# 
byte count 
# 
transaction number 
The byte count is a short unsigned integer that includes the number of bytes in all fields in the 
message except the Message start ASCII delimiter, the Message ID and the byte count. 
Therefore, the byte count is always 8 bytes less than the length of the complete message. 
The transaction number is a number that is attached to the input message by the client. POS MV 
returns this number to the user in the Acknowledge message (ID 0). This mechanism permits the 
client to know which message the POS MV is responding to; the number must be between 0 and 
65532 when sent to POS. The transaction numbers 65533 to 65535 are used by POS when 
outputting the echo copy of the messages. 
The message body falls between the header and footer. While many messages have a message 
body, it is not a requirement of the protocol. Message without bodies may in themselves act as 
events, or messages may use the body to command a particular state. 
Messages end with a footer that contains a pad, a checksum and an ASCII delimiter ($#). 
The pad is used to make each message length a multiple of four bytes. The checksum is 
calculated so that short (16 bit) integer addition of sequential groups of two bytes results in a net 
sum of zero. 
Parameters flagged as default are the factory settings. 
The byte, short, ushort, long, ulong, float and double formats are defined in Appendix A: Data 
Format Description. 
The ranges of valid values for message fields that contain numbers are specified in the same way 
as for numerical group fields. 


54 


 
Message fields that contain numerical values may contain invalid numbers. Invalid byte, short, 
ushort, long, ulong, float and double values are defined in Table 82 (Appendix A: Data Format 
Description). POS MV ignores invalid values that it receives in fields containing numerical 
values. This does not apply to fields containing bit settings. 
4.4 Messages Tables 
4.4.1 General Messages 
The following tables list the format that POS MV expects for each message input and provides 
for each message output. 
Message 0: Acknowledge 
POS MV responds to a user control message with the Acknowledge message in three possible 
ways described below: 
1. The control message from the POS Controller triggers a change of state within the POS MV. 
Some changes of state such as navigation mode transitions may require several seconds to 
complete. POS MV sends Message 0: Acknowledge indicating that the transition is in 
progress but not necessarily complete. For example, POS MV replies to a message 
commanding the POS MV to transition to Navigate mode as soon as the mode transition 
begins. 
2. The control message from the POS Controller contains new POS MV installation or set-up 
parameters that replace the parameters currently used by the POS MV. The Acknowledge 
message then indicates whether the POS MV has received and begun to use the new 
parameters. POS MV responds with Message 0: Acknowledge only when it has begun to use 
the new parameters. 
3. The control message from the POS Controller starts the transmission of one or more groups 
of data. The Acknowledge message indicates the successful completion of the requested 
action. The POS MV subsequently transmits the requested groups on the Display and/or Data 
ports. If the data for one or more of the requested groups are not current at the time of 
request, the P POS MV outputs the group(s) with stale fields set to invalid values as 
described in Table 82. Message 0: Acknowledge indicates if the data for a requested group is 
available (not yet implemented). 
The New Parameters Status field indicates if the message being acknowledged has changed the 
parameters. This allows a POS Controller to prompt the user to direct the POS MV to save the 
parameters to non-volatile memory if the user has not already done so before commanding a 
Standby mode transition or system shutdown. 
POS MV sets the Parameter Name to the name of a parameter that it has rejected or to a null 
string if it did not reject any parameters. 


55 


 
Table 43: Message 0: Acknowledge 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 0 N/A 
Byte count 2 ushort 44 N/A 
Transaction number 2 ushort Transaction number sent by 
client. 
N/A 
ID of received message 2 ushort Any valid message number. N/A 
Response code 2 ushort See Table 44 N/A 
New parameters status 1 byte Value Message 
0 No change in parameters 
1 Some parameters changed 
2-255 Reserved 
N/A 
Parameter name 32 char Name of rejected parameter on 
parameter error only 
N/A 
Pad 1 bytes 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Table 44: Message response codes 
Field 
Value 
Field Name Description 
0 Not applicable The message is not applicable to the POS MV. 
1 Message accepted POS MV has properly accepted the message from 
the POS Controller. 
2 Message accepted - 
too long 
POS MV has accepted the messaged from the POS 
Controller. This is a warning that the POS MV 
expected a shorter message than the one received. 
This could be caused if the POS MV and the POS 
Controller have different ICD versions. 


56 


 
Field 
Value 
Field Name Description 
3 Message accepted - 
too short 
POS MV has accepted the messaged from the POS 
Controller. This is a warning that the POS MV 
expected a longer message than the one received. 
This could be caused if the POS MV and the POS 
Controller have different ICD versions. 
4 Message parameter error The message contains one or more parameter 
errors. 
5 Not applicable in current 
state 
POS MV cannot process the message or cannot 
output data requested in its current state. 
6 Data not available The requested data is not available from POS MV. 
7 Message start error The message does not have the proper header 
``$MSG''. 
8 Message end error The message does not have the proper footer ``$#''. 
9 Byte count error The byte count of the message is too large for 
POS MV's internal buffer. 
10 Checksum error The message checksum validation failed. 
11 User not logged in Password protection feature is in effect, and user 
must enter password before sending the command. 
This should only occur if an incompatible 
Controller or Controller version is being used. 
12 Password incorrect User was prompted for password and entered 
incorrect password. 
13-65535 Reserved Reserved 
4.4.2 Installation Parameter Set-up Messages 
Message 20: General Installation and Processing Parameters 
This message contains general installation parameters that POS MV requires to correctly process 
sensor data and output the computed navigation data. The POS MV accepts this message at any 
time. The parameters contained in this message become part of the processing parameters 
(referred to as ``settings'') that POS MV saves to NVM. 
The following are brief descriptions of the parameters that this message contains. 


57 


 
Time Tag Selection 
The Time Tag Type field selects the time tag types used for Time 1, Time 2 and Distance fields 
in the Time/Distance fields in each group (see Table 3). The user can select POS, GPS or UTC 
time for Time 1 and POS, GPS, UTC or User time for Time 2. 
Selection of GPS time directs POS MV to set the selected Time 1 or Time 2 field in all groups to 
the GPS seconds of the current week. The GPS week number can be obtained from Group 3: 
Primary GPS status. 
Selection of UTC time directs POS MV to set the selected Time 1 or Time 2 field in all groups 
to the UTC seconds of the current week. UTC seconds of the week will lag GPS seconds of the 
week by the accumulated leap seconds since the startup of GPS at which time the two times were 
synchronized. 
AutoStart Selection 
The Select/Deselect Autostart field directs POS MV to enable or disable the AutoStart function. 
When AutoStart is enabled POS MV enters Navigate mode immediately on power-up using the 
parameters stored in its NVM. When Autostart is disabled, POS MV enters Standby mode on 
power-up. The user must explicitly command a transition to Navigate mode. 
Lever Arms and Mounting Angles 
This message contains a series of fields that contain lever arm components and mounting angles. 
These define the positions and orientations of the IMU and aiding sensors (GPS antennas) with 
respect to user-defined reference and Vessel coordinate frames. These coordinate frames and the 
installation data contained in this message are defined for an IMU that is rigidly mounted to the 
Vessel. 
The Vessel frame is a right-handed coordinate frame that is fixed to the Vessel whose navigation 
solution the POS MV computes. The X-Y-Z axes are directed along the forward, right and down 
directions of the Vessel. These are the forward along beam, starboard and vertical directions. 
The reference frame is a user-defined coordinate frame that is co-aligned with the Vessel frame, 
but which may be at a location that allows easier measurement of lever arms. It is also the 
coordinate frame in which the relative positions and orientations of the IMU and aiding sensors 
are measured. Its origin does not necessarily coincide with the Vessel frame origin, however it is 
aligned with the Vessel frame. 
The IMU frame is a right-handed coordinate frame whose X-Y-Z axes coincide with the inertial 
sensor input axes. The IMU delivers inertial data resolved in the IMU frame to the PCS. The 
position and orientation of the IMU frame is fixed with respect to the Vessel frame when the user 
mounts the IMU. Practical considerations may limit the choices in IMU location, in which case 
the actual position and orientation of the IMU frame may differ from a desired position and 
orientation. 


58 


 
The interpretations of the lever arm and orientation fields are as follows: 
Reference to IMU lever arm components 
These are the X-Y-Z distances from the user-defined reference frame origin to the IMU 
inertial sensor assembly origin, resolved in the reference frame. 
Note: When MV POSView is used to send this message to the POS MV, the lever arm 
measurement entered in MV POSView should be to the target painted on the top of the IMU 
enclosure. MV POSView automatically adds the correct IMU enclosure to the IMU sensing 
centre offsets (including mounting angles) when constructing the message. The echo message 
output by POS MV on the Display and Data ports contain the lever arm to the sensing centre 
parameters. Prior to displaying the lever arm value, MV POSView applies the inverse offset 
to the Reference to IMU lever arm. If a user wishes to write a POS Controller application, the 
appropriate offsets can be supplied upon request. 
Reference to Primary GPS lever arm components 
These are the X-Y-Z distances measured from the user-defined reference frame origin to the 
phase centre of the primary GPS antenna, resolved in the reference frame. 
Reference to Auxiliary 1 GPS lever arm components 
These are the X-Y-Z distances measured from the user-defined reference frame origin to the 
phase centre of the auxiliary 1 GPS antenna, resolved in the reference frame. POS MV uses 
these lever arm components whenever it processes data from an optional auxiliary 1 GPS 
receiver. If POS MV does not receive the auxiliary 1 GPS data, then it does not use these 
parameters. 
Reference to Auxiliary 2 GPS lever arm components 
These are the X-Y-Z distances measured from the user-defined reference frame origin to the 
phase centre of the auxiliary 2 GPS antenna, resolved in the reference frame. POS MV uses 
these lever arm components whenever it processes data from an optional auxiliary 2 GPS 
receiver. If POS MV does not receive the auxiliary 2 GPS data, then it does not use these 
parameters. 
IMU with respect to Reference frame mounting angles 
These are the angular offsets ( # x ,  # y ,  # z  )  of  the  IMU  frame with  respect  to  the  reference  
frame when the IMU is rigidly mounted to the Vessel. The angles define the Euler sequence  
of  rotations  that  bring  the  reference  frame  into  alignment with  the  IMU  frame. The angles  
follow the Tate-Bryant sequence of rotation, given as follows:  
right-hand screw rotation of #z about the z axis  
right-hand screw rotation of #y about the once rotated y axis  
right-hand screw rotation of # x about the twice rotated x axis  


59 


 
The angles # x , # y and # z may be thought of as the roll, pitch and yaw of the IMU body frame  
with respect to the user IMU frame.  
Reference Frame with respect to Vessel Frame mounting angles  
Although these X-Y-Z fields are part of Core message 20 they are not used in the POS MV  
product.  POS MV  assumes  the  reference  frame  and  the  Vessel  frame  are  co-aligned.  
MV POSView does not provide data entry fields for these values.  
Multipath Setting 
The Multipath Environment field directs POS MV to set its processing parameters for one of 
three multipath levels impinging on primary, secondary and auxiliary GPS antennas. These are 
LOW, MEDIUM and HIGH multipath. This field allows the user to select the multipath 
environment which best describes the present multipath conditions. POS uses this information to 
scale the RMS errors on the position and velocity outputs reported to the user to ensure that the 
reported errors are reasonable. If the user selects LOW, POS MV assumes virtually no multipath 
error in the primary, secondary and auxiliary GPS data. If the user selects MEDIUM or HIGH, 
POS MV assumes, respectively, moderate or severe multipath errors and accounts for these in its 
GPS processing algorithms. 
Table 45: Message 20: General Installation and Processing Parameters 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 20 N/A 
Byte count 2 ushort 84 N/A 
Transaction Number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Time types 1 byte Value (bits 0-3) Time type 1 
0 POS time 
1 GPS time (default) 
2 UTC time 
3-16 Reserved 
Value (bits 4-7) Time type 2 
0 POS time (default) 
1 GPS time 
2 UTC time 
3 User time 


60 


 
Item Bytes Format Value Units 
4-16 Reserved 
Distance type 1 byte Value State 
0 N/A 
1 POS distance (default) 
2 DMI distance 
3-255 Reserved 
Select/deselect AutoStart 1 byte Value State 
0 AutoStart disabled (default) 
1 AutoStart enabled 
2-255 Reserved 
Reference to IMU X lever arm 4 float ( , ) default = 0 meters 
Reference to IMU Y lever arm 4 float ( , ) default = 0 meters 
Reference to IMU Z lever arm 4 float ( , ) default = 0 meters 
Reference to Primary GPS X lever arm 4 float ( , ) default = 0 meters 
Reference to Primary GPS Y lever arm 4 float ( , ) default = 0 meters 
Reference to Primary GPS Z lever arm 4 float ( , ) default = 0 meters 
Reference to Auxiliary 1 GPS X lever arm 4 float ( , ) default = 0 meters 
Reference to Auxiliary 1 GPS Y lever arm 4 float ( , ) default = 0 meters 
Reference to Auxiliary 1 GPS Z lever arm 4 float ( , ) default = 0 meters 
Reference to Auxiliary 2 GPS X lever arm 4 float ( , ) default = 0 meters 
Reference to Auxiliary 2 GPS Y lever arm 4 float ( , ) default = 0 meters 


61 


 
Item Bytes Format Value Units 
Reference to Auxiliary 2 GPS Z lever arm 4 float ( , ) default = 0 meters 
X IMU wrt Reference frame mounting angle 4 float [-180, +180] default = 0 degrees 
Y IMU wrt Reference frame mounting angle 4 float [-180, +180] default = 0 degrees 
Z IMU wrt Reference frame mounting angle 4 float [-180, +180] default = 0 degrees 
X Reference frame wrt Vessel frame mounting angle 4 float [-180, +180] default = 0 degrees 
Y Reference frame wrt Vessel frame mounting angle 4 float [-180, +180] default = 0 degrees 
Z Reference frame wrt Vessel frame mounting angle 4 float [-180, +180] default = 0 degrees 
Multipath environment 1 byte Value Multipath 
0 Low 
1 Medium 
2 High (default) 
3-255 Reserved 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 21: GAMS Installation Parameters 
This message contains the GAMS installation parameters. POS MV accepts this message at any 
time. The parameters contained in this message become part of the processing parameters 
(referred to as ``settings'') that POS MV saves to NVM. 


62 


 
The following are brief descriptions of the parameters that this message contains. 
The Primary-Secondary Antenna Separation field contains the separation between the primary 
and secondary antenna centres as measured by the user. This value must have an accuracy of one 
centimetre or better in order for it to be useful to the algorithm. POS MV flags any value smaller 
than 10 centimetres as invalid. The default value is zero. 
The Baseline Vector X-Y-Z Component fields contain the components of the primary-secondary 
antenna baseline vector resolved in the IMU frame. The user is usually not able to measure these 
and hence may insert the components that the POS MV computed in a previous GAMS 
calibration. POS MV computes the vector length and flags any length smaller than 10 
centimetres as invalid. It replaces a user-entered primary-secondary antenna separation with a 
valid length. The default is a zero vector. Only an experienced user should use this message, as a 
wrong value will disable the GAMS algorithm and a re-calibration will be necessary. 
The Maximum Heading Error RMS For Calibration field contains the maximum navigation 
solution heading error RMS that the POS MV uses for executing a GAMS baseline calibration. If 
the current heading error RMS exceeds the specified maximum when the user commands a 
GAMS calibration, then POS MV defers the calibration until the heading error RMS drops to 
below the specified maximum. 
The Heading Correction field contains a user-entered azimuth error in the primary-secondary 
antenna baseline vector. POS MV computes a new baseline vector that has been rotated so that 
the POS MV computed heading changes by the specified heading correction when GAMS is on- 
line. 
Note: POS MV echos this message with the updated Baseline Vector and the Heading Correction 
field cleared. The user should not enter another Heading Correction without also restoring the 
original calibrated Baseline Vector. 
Table 46: Message 21: GAMS installation parameters 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 21 N/A 
Byte count 2 ushort 32 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Primary-secondary antenna separation 4 float [0, ) default = 0 Meters 
Baseline vector X component 4 float ( , ) default = 0 Meters 
Baseline vector Y component 4 float ( , ) default = 0 meters 


63 


 
Item Bytes Format Value Units 
Baseline vector Z component 4 float ( , ) default = 0 meters 
Maximum heading error RMS for calibration 4 float [0, ) default = 3 degrees 
Heading correction 4 float ( , ) default = 0 degrees 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 22: Reserved 
Message 23: Reserved 
Message 24: User Accuracy Specifications 
This message sets the user accuracy specifications for full navigation status. POS MV declares 
Full Navigation status on the front panel LED's and through the POS Controller when the 
position, velocity, attitude and heading error RMS have all dropped to or below these accuracy 
specifications. 
POS MV accepts this message at anytime. The parameters contained in this message become 
part of the processing parameters (referred to as ``settings'') that POS MV saves to NVM. 
Table 47: Message 24: User accuracy specifications 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 24 N/A 
Byte count 2 ushort 24 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: 65533 to 65535 
N/A 
User attitude accuracy 4 float (0, ) default = 0.05 degrees 
User heading accuracy 4 float (0, ) default = 0.05 degrees 
User position accuracy 4 float (0, ) default = 2 meters 
User velocity accuracy 4 float (0, ) default = 0.5 meters/second 


64 


 
Item Bytes Format Value Units 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 25: Reserved 
Message 30: Primary GPS Setup 
This message contains the setup parameters for the primary GPS receiver. POS MV accepts this 
message at anytime. The parameters contained in this message become part of the processing 
parameters (referred to as ``settings'') that POS MV saves to NVM. 
The Select/Deselect GPS AutoConfig field directs POS MV to reconfigure the primary GPS 
receiver if the POS MV detects that the primary GPS configuration is incorrect. If the user 
chooses to disable auto-configuration, then the user must configure the primary GPS receiver 
manually. 
The Primary GPS COM1 Output Message Rate field specifies the rate at which the primary GPS 
receiver outputs its raw observables messages over its COM1 port to the POS MV. POS MV 
only process 1 Hz observables, however, selecting a higher output rate will allow more data to be 
logged which may be useful for a post processed solution. 
The Primary GPS COM2 Port Control directs the primary GPS receiver to accept RTCM 
differential corrections, RTCA Type 18/19 corrections, CMR corrections or commands over its 
COM2 port. This message assumes that the user can access the GPS receiver COM2 port directly 
and connect either a source of RTCM differential corrections or a PC-compatible computer 
running control software that is compatible with the primary GPS receiver. The POS MV V4 
hardware connects the GPS 1 port on the PCS back panel directly to the Primary GPS COM2 
port. The Primary GPS COM2 port must not be confused with the COM2 port on the PCS. 
POS MV V4 processes raw GPS observables and corrections so there is no need to feed 
corrections directly to the Primary GPS receiver. The GPS 1 port on the PCS read panel is 
primarily to allow GPS receiver firmware upgrades. 
Note: GPS Autoconfig will be turned off upon receipt of an Accept Command message and will 
be turned on again when either an Accept RTCM or a GPS reconfigure message is issued. 
The Primary GPS COM2 Communication Protocol fields are elaborated in Table 49. They 
specify the COM2 RS-232 communication protocol settings. 


65 


 
Table 48: Message 30: Primary GPS Setup 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 30 N/A 
Byte count 2 ushort 16 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Select/deselect GPS AutoConfig 1 byte Value State 
0 AutoConfig disabled 
1 AutoConfig enabled (default) 
2-255 Reserved 
Primary GPS COM1 port message output rate 1 byte Value Rate (Hz) 
1 1 (default) 
2 2 
3 3 
4 4 
5 5 
10 10 
11-255 Reserved 
Primary GPS COM2 port control 1 byte Value Operation 
0 Accept RTCM (default) 
1 Accept commands 
2 Accept RTCA 
3-255 Reserved 
Primary GPS COM2 communication protocol 4 See Table 49 
Default: 9600 baud, no parity, 8 data bits, 
1 stop bit, none 


66 


 
Item Bytes Format Value Units 
Antenna frequency 1 byte Value Operation 
0 Accept L1 only 
1 Accept L1/L2 
2 Accept L2 only 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Table 49: RS-232/422 communication protocol settings 
Item Bytes Format Value 
RS-232/422 port baud rate 1 byte Value Rate 
0 2400 
1 4800 
2 9600 
3 19200 
4 38400 
5 57600 
6 76800 
7 115200 
8-255 Reserved 
Parity 1 byte Value Parity 
0 no parity 
1 even parity 
2 odd parity 
3-255 Reserved 


67 


 
Item Bytes Format Value 
Data/Stop Bits 1 byte Value Data/Stop Bits 
0 7 data, 1 stop 
1 7 data, 2 stop 
2 8 data, 1 stop 
3 8 data, 2 stop 
4-255 Reserved 
Flow Control 1 byte Value Flow Control 
0 none 
1 hardware 
2 XON/XOFF 
3-255 Reserved 
Message 31: Secondary GPS Setup 
This message contains the set-up parameters for the secondary GPS receiver. POS MV accepts 
this message at anytime. The parameters contained in this message become part of the processing 
parameters (referred to as ``settings'') that POS MV saves to NVM. 
The Select/Deselect GPS AutoConfig field directs POS MV to reconfigure the secondary GPS 
receiver if the POS MV detects that the secondary GPS configuration is incorrect. If the user 
chooses to disable auto-configuration, then the user must configure the secondary GPS receiver 
manually. 
The Secondary GPS COM1 Output Message Rate field specifies the rate at which the secondary 
GPS receiver outputs messages over its COM1 port to POS MV. 
The Secondary GPS COM2 Port Control directs the secondary GPS receiver to accept RTCM 
differential corrections, RTCA Type 18 corrections or commands over its COM2 port. This 
message assumes that the user can access the GPS receiver COM2 port directly and connect 
either a source of RTCM differential corrections or a PC-compatible computer running control 
software that is compatible with the secondary GPS receiver. The current POS MV hardware 
connects the GPS 2 port on the PCS back panel directly to the Secondary GPS COM2 port. The 
Secondary GPS COM2 port must not be confused with the COM2 port on the PCS. POS MV V4 
processes raw GPS observables and corrections so there is no need to feed corrections directly to 
the Secondary GPS receiver. The GPS 1 port on the PCS read panel is primarily to allow GPS 
receiver firmware upgrades. 
The Secondary GPS COM2 Communication Protocol fields are elaborated in Table 49. They 
specify the COM2 RS-232 communication protocol settings. 


68 


 
Table 50: Message 31: Secondary GPS Setup 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 31 N/A 
Byte count 2 ushort 16 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Select/deselect GPS AutoConfig 1 byte Value State 
0 AutoConfig disabled 
1 AutoConfig enabled (default) 
2-255 Reserved 
Secondary GPS COM1 port message output rate 1 byte Value Rate (Hz) 
1 1 (default) 
2 2 
3 3 
4 4 
5 5 
10 10 
11-255 Reserved 
Secondary GPS COM2 port control 1 byte Value Operation 
0 Accept RTCM (default) 
1 Accept commands 
2 Accept RTCA 
3-255 Reserved 
Secondary GPS COM2 communication protocol 4 See Table 49 
Default: 9600 baud, no parity, 8 data bits, 
1 stop bit, none 


69 


 
Item Bytes Format Value Units 
Antenna frequency 1 byte Value Operation 
0 Accept L1 only 
1 Accept L1/L2 
2 Accept L2 only 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 32: Set POS IP Address 
This message installs a new IP address and subnet mask in POS MV. POS MV accepts this 
message at anytime. The parameters contained in this message become part of the processing 
parameters (referred to as ``settings''), POS MV does not save it to NVM but changes OS setup 
file. 
When POS MV is installed the new IP address, it will disconnect from any connected controller 
and begin using the new IP address. The changes take effect immediately upon receipt of the 
message. 
Table 51: Message 32: Set POS IP Address 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 32 N/A 
Byte count 2 ushort 16 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
IP address Network part 1 1 byte [128, 191] Class B, subnet mask 
255.255.0.0 
[192, 232] Class C, subnet mask 
255.255.255.0 
default = 129 
N/A 


70 


 
Item Bytes Format Value Units 
IP address Network part 2 1 byte [0, 255] default = 100 N/A 
IP address Host part 1 1 byte [0, 255] default = 0 N/A 
IP address Host part 2 1 byte [1, 253] default = 219 N/A 
Subnet mask Network part 1 1 byte [255] default = 255 
Subnet mask Network part 2 1 byte [255] default = 255 
Subnet mask Host part 1 1 byte [0, 255] default = 255 
* see conditions below 
Subnet mask Host part 2 1 byte [0, 254] default = 0 
* see conditions below 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
* Not only must the host parts of the subnet mask be within the ranges specified, but if the 2 host 
fields are considered as one 16 bit word, then any bit that is set may not have a cleared bit to its 
left. This results in the following valid subnet masks: 
255.255.0.0 255.255.128.0 255.255.192.0 
255.255.224.0 255.255.240.0 255.255.248.0 
255.255.252.0 255.255.254.0 255.255.255.0 
255.255.255.128 255.255.255.192 255.255.255.224 
255.255.255.224 255.255.255.240 255.255.255.248 
255.255.255.252 255.255.255.254 


71 


 
Message 33: Event Discrete Setup 
This message directs POS MV to set the senses of the signals for the Event 1 and 2 discrete 
triggers. The user can select either positive or negative edge trigger for each event. POS MV 
accepts this message at anytime. The parameters contained in this message become part of the 
processing parameters (referred to as ``settings'') that POS MV saves to NVM. 
Table 52: Message 33: Event Discrete Setup 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 33 N/A 
Byte count 2 ushort 8 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Event 1 trigger 1 byte Value Command 
0 Positive edge (default) 
1 Negative edge 
2-255 Reserved 
Event 2 trigger 1 byte Value Command 
0 Positive edge (default) 
1 Negative edge 
2-255 Reserved 
Pad 0 short 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 34: COM Port Setup 
This message sets up the communication protocol and selects the input and output content for all 
available COM ports. It is a variable length message to accommodate POS hardware with 
varying numbers of COM ports. 
When this message is sent to POS it may contain parameters for 1 to 10 COM ports. Any COM 
port can be assigned. If an assigned COM port is not present it will be ignored. Any COM port or 
ports can be specified as long as they are listed in ascending order and the Port Mask field has 
bits set corresponding to each COM port entry. All input selections and the Base GPS output 


72 


 
selections must be uniquely assigned to a COM port. NMEA and Real-time Binary outputs may 
be assigned to any number of COM ports. 
When this message is output from POS it always contains parameters for all n COM ports 
available for that particular system, with the current protocol and input/output selections. 
Table 53: Message 34: COM Port Setup 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 34 N/A 
Byte count 2 ushort 12 + 8 x nPorts N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Number of COM ports 2 ushort [1,10] 
Number (nPorts) of COM ports 
assigned by this message. 
N/A 
COM Port Parameters variable See Table 54 One set of parameters for each of nPorts COM port. 
Port mask 2 ushort Input: 
Bit positions indicate which port parameters 
are in message (port parameters must appear 
in order of increasing port number). 
Bit 0 ignored 
Bit n set COMn parameter in message 
Bit n clear COMn parameter not in message 
Output: 
Bit positions indicate which port numbers 
are available on the PCS for I/O 
configuration. 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 


73 


 
Table 54: COM port parameters 
Item Bytes Format Value Units 
Communication protocol 4 See Table 49 
Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none 
Input select 2 ushort Value Input 
0 No input 
1 Auxiliary 1 GPS 
2 Auxiliary 2 GPS 
3 Reserved 
4 Base GPS 1 
5 Base GPS 2 
6-255 No input 
Output select 2 ushort Value Output 
0 No output 
1 NMEA messages 
2 Real-time binary 
3 Base GPS 1 
4 Base GPS 2 
5-255 No output 
Message 35: See Message 135 
Message 36: See Message 136 
Message 37: Base GPS 1 Setup 
This message selects the message types assigned to the Base GPS 1 port identified in Message 
34. If POS MV is connected to a Hayes compatible telephone modem, then this message directs 
POS MV's configuration of the modem. 


74 


 
Message 38: Base GPS 2 Setup 
This message selects the message types assigned to the Base GPS 2 port identified in Message 
34. If POS MV is connected to a Hayes compatible telephone modem, then this message directs 
POS MV's configuration of the modem. 
The connection control field will always be set to NO_ACTION when sent by POS MV except 
when the message sent by the client had modem control set to AUTOMATIC and the connection 
control set to CONNECT. The reason for this is to prevent manual or command actions from 
getting saved in NVM and being inadvertently activated when POS MV is started. The 
AUTOMATIC-CONNECT combination is the only one that a user may want to save to NVM. 
Table 55: Message 37/38: Base GPS 1/2 Setup 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 37/38 N/A 
Byte count 2 ushort 240 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Select Base GPS input type 2 ushort Value Operation 
0 Do not accept base GPS messages 
1 Accept RTCM 1/9 (default) 
2 Accept RTCM 3, 18/19 
3 Accept CMR/CMR+ 
4 Accept RTCA 
5-65535 Reserved 
Line control 1 byte Value Operation 
0 Line used for Serial (default) 
1 Line used for Modem 
2-255 Reserved 


75 


 
Item Bytes Format Value Units 
Modem control 1 byte Value Operation 
0 Automatic control (default) 
1 Manual control 
2 Command control 
3-255 Reserved 
Connection control 1 byte Value Operation 
0 No action (default) 
1 Connect 
2 Disconnect/Hang-up 
3 Send AT Command 
4-255 No action 
Phone number 32 char N/A N/A 
Number of redials 1 byte [0, ) default = 0 N/A 
Modem command string 64 char N/A N/A 
Modem initialization string 128 char N/A N/A 
Data timeout length 2 ushort [0, 255] default = 0 seconds 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 40: Reserved 
Message 41: Reserved 
4.4.3 Processing Control Messages 
Message 50: Navigation Mode Control 
This message directs POS MV to transition to a specified navigation mode. The two basic 
navigation modes are Standby and Navigate. 


76 


 
Table 56: Message 50: Navigation mode control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 50 N/A 
Byte count 2 ushort 8 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Navigation mode 1 byte Value Mode 
0 No operation (default) 
1 Standby 
2 Navigate 
3-255 Reserved 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 51: Display Port Control 
This message directs POS MV to output specified groups on the Display Port primarily for the 
purpose of display of data on the POS Controller. 
The Number of Groups field contains the number n of groups that this message selects. 
Thereafter follow n Display Port Output Group Identification fields, each of which identifies one 
selected group to be output on the Display Port. 
The POS MV always outputs Groups 1, 2, 3, 10 and 110 on the Display Port to provide a 
minimal set of data for the POS Controller. These cannot be de-selected by omission from this 
message. 
POS MV accepts this message at anytime. The parameters contained in this message become 
part of the processing parameters (referred to as ``settings'') that POS MV saves to NVM. 
When MV POSView is connected to a POS MV Control port, it immediately sends message 51 
requesting the groups it requires to populate all its currently open windows. Whenever the user 
opens a new display window, MV POSView automatically sends message 51 requesting the 
additional group(s) that are required. Hence there is no user setup window for the Display port in 
MV POSView. 


77 


 
Table 57: Message 51: Display Port Control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 51 N/A 
Byte count 2 ushort 10 + 2 x number of groups 
(+2 if pad bytes are required) 
N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Number of groups selected for Display Port 2 ushort [4, 70] default = 4 
(Groups 1,2,3,10 are always output on 
Display Port) 
N/A 
Display Port output group identification variable ushort Group ID to output 
[1, 65534] 
N/A 
Reserved 2 ushort 0 N/A 
Pad 0 or 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 52: Real-Time Data Port Control 
This message directs POS MV to output specified groups on the Real-Time Data Port at a 
specified rate. 
The Number of Groups field contains the number n of groups that this message selects. 
Thereafter follow n Data Port Output Group Identification fields, each of which identifies one 
selected group to be output on the Data Port. 
The Data Port Output Rate field selects the output rates of all specified groups from one of 
several available discrete output rates. POS MV outputs a selected group at the lesser of the user- 
specified rate or the internal update rate; this depends on the selected group. If the user selects a 
group to be output at maximum available rate when the internal update rate of the group data is 1 


78 


 
Hz, then POS MV outputs the selected group at 1 Hz. An exception is Group 4: Time-tagged 
IMU, which the POS MV outputs at the IMU data rate regardless of the user-specified data rate. 
POS MV accepts this message at anytime. The parameters contained in this message become 
part of the processing parameters (referred to as ``settings'') that POS MV saves to NVM. 
Table 58: Message 52/61: Real-Time/Logging Data Port Control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 52 or 61 N/A 
Byte count 2 ushort 10 + 2 x number of groups 
(+2 if pad bytes are required) 
N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Number of groups selected for Data Port 2 ushort [0, 70] default = 0 N/A 
Data Port output group identification variable ushort Group ID to output 
[1, 65534] 
N/A 
Data Port output rate 2 ushort Value Rate (Hz) 
1 1 (default) 
2 2 
10 10 
20 20 
25 25 
50 50 
100 100 
200 200 
other values Reserved 
Pad 0 or 2 byte 0 N/A 


79 


 
Item Bytes Format Value Units 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 53: Reserved 
Message 54: Save/Restore Parameters Control 
This message directs POS MV to save the current configuration to non-volatile memory (NVM) 
or to retrieve the currently saved parameters from NVM. POS MV accepts this message at 
anytime. 
If the Control field is set to any value other than 1-3, this message has no effect. If the Control 
field is set to 1, POS MV saves the current parameters to NVM, thereby overwriting the 
previously saved parameters. If the Control field is set to 2, POS MV retrieves the currently 
saved parameters into the active parameters for the current navigation session. If the Control 
field is set to 3, POS MV resets the active parameters to the factory default settings. The 
previously active parameters are overwritten. 
Table 59: Message 54: Save/restore parameters control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 54 N/A 
Byte count 2 ushort 8 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Control 1 byte Value Operation 
0 No operation 
1 Save parameters in NVM 
2 Restore user settings from NVM 
3 Restore factory default settings 
4-255 No operation 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 


80 


 
Message 55: User Time Recovery 
This message specifies the time of the last PPS in user time to POS MV. It directs POS MV to 
synchronize its User Time with the time specified in the User PPS Time field. POS MV accepts 
this message at anytime at a maximum rate of once per second. 
To establish user time synchronization, the user must send the user time of last PPS to POS MV 
with this message after the PPS has occurred. The resolution of time synchronization is one 
microsecond. 
Table 60: Message 55: User time recovery 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 55 N/A 
Byte count 2 ushort 24 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
User PPS time 8 double [0, ) default = 0.0 seconds 
User time conversion factor 8 double [0, ) default = 1.0 #/seconds  
Pad  2  short  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  
 
Message 56: General Data  
This  message  provides  POS MV with  an  initial  time,  position,  distance  and  attitude  fix  when  
either  the  primary  GPS  receiver  is  unable  to  provide  this  information  within  a  maximum  
initialization time. The data in this message allows a stationary POS MV to complete the coarse  
leveling algorithm and begin operating in Navigate mode. POS MV can also be commanded to  
start  (or  continue)  in  an  alignment  status  beyond  coarse  leveling  should  the  accuracy  of  
prescribed  initial  conditions warrant. The  initial horizontal position CEP describes  the circular  
error  probability  of  the  initial  position.  The  initial  altitude  standard  deviation  describes  the  
uncertainty in the initial altitude. These can be used to re-align POS MV at a last known position  
following an integration failure when GPS is unavailable.  
POS MV accepts this message at any time. It will only use the data in this message if GPS data  
remains unavailable for longer than 120 seconds after receipt of this message. It will supersede  


81 


 
this general data with GPS position data as soon as the GPS data becomes available. POS MV 
does not save this message to NVM, hence the user must provide this message during every 
POS MV start-up where the general data are required. 
Table 61: Message 56: General data 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 56 N/A 
Byte count 2 ushort 80 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Time of day: Hours 1 byte [0, 23] default = 0 hours 
Time of day: Minutes 1 byte [0, 59] default = 0 minutes 
Time of day: Seconds 1 byte [0, 59] default = 0 seconds 
Date: Month 1 byte [1, 12] default = 1 month 
Date: Day 1 byte [1, 31] default = 1 day 
Date: Year 2 ushort [0, 65534] default = 0 year 
Initial alignment status 1 byte See Table 5 N/A 
Initial latitude 8 double [-90, +90] default = 0 degrees 
Initial longitude 8 double [-180, +180] default = 0 degrees 
Initial altitude 8 double [-1000, +10000] default = 0 meters 
Initial horizontal position CEP 4 float [0, ) default = 0 meters 
Initial altitude RMS uncertainty 4 float [0, ) default = 0 meters 
Initial distance 8 double [0, ) default = 0 meters 
Initial roll 8 double [-180, +180] default = 0 degrees 
Initial pitch 8 double [-180, +180] default = 0 degrees 
Initial heading 8 double [0, 360) default = 0 degrees 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 


82 


 
Item Bytes Format Value Units 
Message end 2 char $# N/A 
Message 57: Installation Calibration Control 
This message controls the POS MV function of self-calibration of primary installation 
parameters. POS MV accepts this message at any time. The primary installation parameters 
exclude the GAMS installation parameters, which are handled by a separate calibration function 
and controlled separately by Message 58: GAMS Calibration Control. 
The calibration is done assuming that the IMU Frame is the Reference Frame. If it is desirable to 
have the IMU and Reference Frames non-coincident, then the user must apply additional offsets 
consistently to all sensor frames to define a non-coincident Reference Frame. 
The calibration action byte specifies a calibration action. The calibration select byte identifies 
installation parameter sets on which the calibration action is applied. POS MV executes the 
specified calibration action as soon as it receives this message. The following are calibration 
actions available to the user: 
# 
start an auto-calibration or a manual calibration of selected installation parameters 
# 
stop an ongoing calibration 
# 
perform normal transfer of selected calibrated parameters following manual calibration 
# 
perform forced transfer of selected calibrated parameters following manual calibration 
The user selects one or more installation parameter sets for calibration by setting the bits in the 
calibration select byte corresponding to the parameter sets to be calibrated to 1. The user starts a 
calibration of the selected installation parameters by setting the calibration action byte to 2 for a 
manual calibration or 3 for an auto-calibration. POS MV restarts the Navigate mode with the 
calibration option set. It then computes corrected versions of the selected installation parameters 
and reports these with corresponding calibration figures of merit (FOM) in Group 14: Calibrated 
installation parameters. A calibration of a selected set of installation parameters is completed 
when the corresponding FOM reaches 100. 
The user stops all calibrations by setting the calibration action byte to 1. POS MV restarts the 
Navigate mode without the calibration option and abandons any previous calibration actions. 
In an auto-calibration, POS MV replaces the existing set of installation parameters and issues a 
corresponding Message 20: General Installation and Processing Parameters or Message 22: 
Aiding Sensor Installation Parameters when the calibration is completed. POS MV resets its 
Kalman filter and restarts the normal Navigate mode with the updated installation parameters 
when all selected calibrations are completed. 


83 


 
In a manual calibration, POS MV continues the calibration and displays the final values in Group 
14: Calibrated installation parameters until it receives a user command to stop the calibration or 
transfer the calibrated parameters. 
In a normal transfer of calibrated parameters, POS MV replaces the existing set of installation 
parameters selected by the calibration select byte with the corrected parameters displayed in 
Group 14: Calibrated installation parameters and having a FOM of 100. POS MV resets its 
Kalman filter and restarts the normal Navigate mode with the possibly updated installation 
parameters. 
In a forced transfer of calibrated parameters, POS MV replaces the existing set of installation 
parameters selected by the calibration select byte with the corrected parameters displayed in 
Group 14: Calibrated installation parameters and having a FOM greater than 0. POS MV resets 
its Kalman filter and restarts the normal Navigate mode with the updated installation parameters. 
Table 62: Message 57: Installation calibration control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 57 N/A 
Byte count 2 ushort 8 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Calibration action 1 byte Value Command 
0 No action (default) 
1 Stop all calibrations 
2 Manual calibration 
3 Auto-calibration 
4 Normal calibrated parameter transfer 
5 Forced calibrated parameter transfer 
6-255 No action 
Calibration select 1 byte Bit (set) Command 
0 Calibrate primary GPS lever arm 
1 Calibrate auxiliary 1 GPS lever arm 
2 Calibrate auxiliary 2 GPS lever arm 
3 - 7 reserved 


84 


 
Item Bytes Format Value Units 
Pad 0 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 58: GAMS Calibration Control 
This message controls the operation of the GAMS calibration function. POS MV accepts this 
message at any time. 
The GAMS Calibration Control field directs POS MV to do the following: 
# 
stop a current nalibration in progress 
# 
begin a new calibration or resume a suspended calibration 
# 
suspend a current calibration in progress or 
# 
force a calibration to start without regard to the current navigation solution attitude 
accuracy 
POS MV returns Message 21: GAMS Installation Parameters containing the new GAMS 
installation parameters when the calibration is completed. 
Table 63: Message 58: GAMS Calibration Control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 58 N/A 
Byte count 2 ushort 8 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
GAMS calibration control 1 byte Value Command 
0 Stop calibration (default) 
1 Begin or resume calibration 
2 Suspend calibration 
3 Force calibration 
4-255 No action 
Pad 1 byte 0 N/A 


85 


 
Item Bytes Format Value Units 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 60: Reserved 
Message 61: Logging Data Port Control 
This message directs the POS MV to output specified groups on the Logging Data Port at a 
specified rate. The format and content of the message is the same as that of Message 52 and is 
given by Table 58. 
POS MV accepts this message at anytime. The parameters contained in this message become 
part of the processing parameters (referred to as ``settings'') that POS MV saves to NVM. 
4.4.4 Program Control Override Messages 
Message 90: Program Control 
This message controls the operational status of POS MV. POS MV accepts this message at any 
time. 
POS MV interprets the values in the message as follows. 
000 The connected POS Controller is alive and the TCP/IP connection is good. 
001 Terminate the TCP/IP connection. This allows the POS Controller to disconnect as 
controller and re-connect later. 
100 Reset the GAMS algorithm to clear any pending problems. 
101 Reset POS to clear pending problems. All parameters will be loaded from NVM after 
a reset. 
102 Shutdown POS in preparation for power-off. This function allows POS to 
synchronize its files before the user disconnects the power. The user should ensure 
that POS settings are saved before beginning the shutdown procedure. 
POS MV continuously monitors the TCP/IP connection between itself and the POS Controller. 
POS MV expects to receive at least one message from the POS Controller every 30 seconds or it 
will automatically terminate the TCP/IP connection. The purpose of this function is for the 
POS MV to determine if the POS Controller has failed, in which case it can reset the TCP/IP 
port. This message can be used with a value of 0 as a no operation (NOP) message when no other 
messages need to be sent to POS MV. 


86 


 
Table 64: Message 90: Program Control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 90 N/A 
Byte count 2 ushort 8 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Control 2 ushort Value Command 
000 Controller alive 
001 Terminate TCP/IP connection 
100 Reset GAMS 
101 Reset POS 
102 Shutdown POS 
all other values are reserved 
Pad 0 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 91: GPS Control 
This message directs POS MV to configure or reset its internal GPS receivers. POS MV accepts 
this message at any time. 
The Control Command field when set to Send GPS configuration (0) directs POS MV to 
reconfigure the GPS receivers. POS MV then sends the configuration script messages to the 
receivers in the same way as it does during initialization following power-up. The user would use 
this command if he suspected that an internal GPS receiver had not initialized correctly or had 
lost its configuration. 
The Control Command field when set to Send reset command (1) directs POS MV to send ``cold 
reset'' commands to the GPS receivers. This directs an internal GPS receiver to revert to the 
factory default configurations. The user would use this command to establish a starting point for 
troubleshooting problems with a GPS receiver. 


87 


 
Table 65: Message 91: GPS control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 91 N/A 
Byte count 2 ushort 8 N/A 
Transaction number 2 ushort Input: Transaction number 
Output: [65533, 65535] 
N/A 
Control command 1 byte Value Command 
0 Send primary GPS configuration 
1 Send primary GPS reset command 
2 Send secondary GPS configuration 
3 Send secondary GPS reset command 
4-255 No action 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 92: Reserved 
Message 93: Reserved 
4.4.5 POS MV Specific Messages 
Message 105: Analog Port Set-up 
This message allows the user to configure the analog port to communicate with other equipment. 
For the analog port, the user is able to configure the output message format, the scale factor and 
the parameter sense required. 
Table 66: Message 105: Analog Port Set-up 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 105 N/A 


88 


 
Item Bytes Format Value Units 
Byte count 2 ushort 24 N/A 
Transaction # 2 ushort Input: Transaction number set by client 
Output: [65533, 65535] 
N/A 
Roll Scale Factor 4 float # = (0, )  
(default = 1.0)  N/A  
Pitch Scale Factor 4  float  # = (0, )  (default = 1.0)  N/A  
Heave Scale Factor 4  float  # = (0, )  
(default = 1.0)  N/A  
Roll Sense  1  byte  Value  Analog +ve  
0  port up  (default)  
1  starboard up  
N/A  
Pitch Sense  1  byte  Value  Analog +ve  
0  bow up  (default)  
1  stern up  
N/A  
Heave Sense  1  byte  Value  Analog +ve  
0  up  (default)  
1  down  
N/A  
Analog Formula Select 1  byte  Value  Formula  
0  (Tate-Bryant Trig)  
roll = ##10sin#  
pitch = ##10sin#  
heave = ##heave  
1  (Tate-Bryant Linear)  
roll = ###  
pitch = ###  
heave = ##heave  
2 (default)  (TSS Trig)  
roll = ##10(sin#cos#)  
pitch = ##10sin#  
heave = ##heave  
3  (TSS Linear)  
roll = ##sin -1 (sin#cos#)  
pitch = ###  
volts  


89 


 
Item Bytes Format Value Units 
heave = ##heave  
4  (RPH)  
roll = ###  
pitch = ###  
heading = ###  
Analog Output  1  byte  Value  Condition  
0  analog off  
1  analog on (default)  
N/A  
Frame of Reference 1  byte  Value  Condition  
0  sensor 1 (default)  
1  sensor 2  
N/A  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  
 
Message 106: Heave Filter Set-up  
This message allows the user to set the cut-off frequency and damping ratio of the heave filter.  
Also, the message is accepted at anytime and may be saved.  
Table 67: Message 106: Heave Filter Set-up  
Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  106  N/A  
Byte count  2  ushort  16  N/A  
Transaction #  2  ushort  Input:  Transaction number set by client  
Output:  [65533, 65535]  
N/A  
Heave Corner Period 4  float  (10.0, ) (default = 200.0)  seconds  
Heave Damping Ratio 4  float  (0, 1.0) (default = 0.707)  N/A  
Pad  2  byte  0  N/A  


90 


 
Item Bytes Format Value Units 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 111: Password Protection Control 
This command ``Logs in'' the user, or changes the password used for user login. 
The message is accepted anytime, but is redundant if ``Login'' (Password Control) is sent when 
``user logged in'' condition exists (see Table 29: Group 110: MV General Status & FDIR). This is 
the case when the user has logged in within the last 10 minutes, and has not disconnected or 
terminated the connection to the PCS, since the login. 
The message is not saved to NVM, when sent (and accepted) with Password Control equal to 
``Change Password''. The new password is, however, immediately saved in the operating 
system's configuration file. The message is not echoed nor output to any of Display or Data 
Ports. 
Table 68: Message 111: Password Protection Control 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 111 N/A 
Byte count 2 ushort 48 N/A 
Transaction # 2 ushort Input: Transaction number set by 
client 
Output: [65533, 65535] 
N/A 
Password Control 1 byte Value Command 
0 Login 
1 Change Password 
N/A 
Password 20 char String value of current Password, 
terminated by ``null'' if less than 20 
characters, or 20 (non-null) characters. 
Default: pcsPasswd 
N/A 


91 


 
Item Bytes Format Value Units 
New Password 20 char If Password Control = 0: N/A 
If Password Control = 1: String value 
of new (user-selected) Password, 
terminated by ``null'' if less than 20 
characters, or 20 (non-null) characters. 
N/A 
Pad 1 byte 0 N/A -- doc error; said one short, but pad normally in bytes and one byte here for message size to be a multiple of 4 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 120: Sensor Parameter Set-up 
This message contains data that is sent to POS to define the installation parameters of sensors 1 
and 2 and the heave lever arm. 
The interpretation of the items in this message is as follows: 
Sensor(s) wrt Reference frame mounting angle: 
Physical angular offsets of the sensor(s) body frame with respect to the user defined 
reference frame. The reference frame is defined as the right-handed orthogonal co-ordinate 
system with its origin defined at any point the user wishes. The axes are fixed to the 
reference frame, with the x axis in the forward going direction, the y axis perpendicular to the 
x axis and pointing to the right (starboard side), and the z axis pointing down. The sensor(s) 
body frame is defined as the right-handed orthogonal co-ordinate system with its origin at the 
sensing centre of the sensor. These axes are fixed to the sensor. 
The angles define the Euler sequence of rotations that bring the reference frame into 
alignment with the sensor body frame. The angles follow the Tate-Bryant sequence of 
rotation given as follows: right-hand screw rotation of # z  about  the  z  axis  followed  by  a  
rotation  of  # y  about  the  once  rotated  y  axis  followed  by  a  rotation  of  # x  about  the  twice  
rotated x axis. The angles # x , # y , and # z may be thought of as the roll, pitch, and yaw of the  
sensor body frame with respect to the reference frame.  
Reference to Sensor(s) Lever arms:  
Distances  measured  from  the  reference  frame  origin  to  the  sensing  centre  of  the  sensors  
resolved  in  the  reference  frame.  Since  the  reference  frame  is  always  aligned  to  the  vessel  
frame (by design), then from the reference frame origin, x is positive towards the bow, y is  
positive towards the starboard side of the vessel, and z is positive down (Right-Hand Rule).  


92 


 
Reference to Centre of Rotation Lever arms: 
This set of lever arms allows the user to enter the lever arms between the reference frame 
origin and the point on the vessel that experiences vertical motion due only to heave, without 
roll and/or pitch induced vertical motion. The lever arms are defined as the distances 
measured from the reference frame origin to the centre of rotation (CoR) resolved in the 
reference frame. Since the reference frame is always aligned to the vessel frame (by design), 
then from the reference frame origin, x is positive towards the bow, y is positive towards the 
starboard side of the vessel, and z is positive down (Right-Hand Rule). 
Vertical acceleration data from the IMU is transformed to the centre of vessel rotation 
(specified by the lever arms), double integrated and passed through the high-pass heave filter 
and then transformed back to the sensor positions. If this parameter is not entered, heave is 
calculated at the IMU location and then transformed to the sensor positions. 
Table 69: Message 120: Sensor Parameter Set-up 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 120 N/A 
Byte count 2 ushort 68 N/A 
Transaction # 2 ushort Input: Transaction number set by 
client 
Output: [65533, 65535] 
N/A 

X Sensor 1 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle 
Y Sensor 1 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle
Z Sensor 1 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle
X Sensor 2 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle
Y Sensor 2 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle


93 


 
Item Bytes Format Value Units 
Z Sensor 2 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle 
Reference to Sensor 1 X lever arm 4 float ( , ) default = 0 m 
Reference to Sensor 1 Y lever arm 4 float ( , ) default = 0 m 
Reference to Sensor 1 Z lever arm 4 float ( , ) default = 0 m 
Reference to Sensor 2 X lever arm 4 float ( , ) default = 0 m 
Reference to Sensor 2 Y lever arm 4 float ( , ) default = 0 m 
Reference to Sensor 2 Z lever arm 4 float ( , ) default = 0 m 
Reference to CoR X lever arm 4 float ( , ) default = 0 m 
Reference to CoR Y lever arm 4 float ( , ) default = 0 m 
Reference to CoR Z lever arm 4 float ( , ) default = 0 m 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
wrt = with respect to 


94 


 
Message 121: Vessel Installation Parameter Set-up 
This message contains data that is sent to POS to define the installation parameters of the vessel. 
The interpretation of the items in this message is as follows: 
Reference to Vessel Lever Arms: 
This set of lever arms allows the user to define a different point at which the position and 
velocity data is valid for the vessel than the point to which all lever arms are measured. 
Thus, it is possible to have position valid at the vessel bridge, but measure all sensor lever 
arms to some conveniently accessible reference point. 
The lever arm distances are measured from the user defined reference frame origin to 
vessel position of interest resolved in the reference frame. 
Table 70: Message 121: Vessel Installation Parameter Set-up 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 121 N/A 
Byte count 2 ushort 20 N/A 
Transaction # 2 ushort Input: Transaction number set by client 
Output: [65533, 65535] 
N/A 
Reference to Vessel X lever arm 4 float ( , ) default = 0 m 
Reference to Vessel Y lever arm 4 float ( , ) default = 0 m 
Reference to Vessel Z lever arm 4 float ( , ) default = 0 m 
Pad 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 


95 


 
Message 135: NMEA Output Set-up 
This message allows the user to configure Nmea output on one or more COM ports. The COM 
ports on which the Nmea output appears is controlled by message 34. 
Note that this is a MV specific version of the Core message 35. 
The ZDA, UTC and PPS output strings are fixed at 1 Hz (if selected) and synchronized to the 
GPS PPS. They may be combined with other outputs at higher rates. 
Table 71: Message 135: NMEA Output Set-up 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 135 N/A 
Byte count 2 ushort For even #ports (16 + #ports x 10) 
For odd #ports (18 + #ports x 10) 
N/A 
Transaction # 2 ushort Input: Transaction number set by client 
Output: [65533, 65535] 
N/A 
Reserved 9 byte N/A N/A 
Number of Ports 1 byte [0, 10] N/A 
NMEA Port Definitions variable See Table 72: NMEA Port Definition #ports x 10 
Pad 0 or 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Pad size is 0 bytes if number of ports is even, size is 2 bytes if number of ports is odd. 
Table 72: NMEA Port Definition 
Port Number 1 byte [1, 10] N/A 
Nmea Formula Select 4 ulong Bit (set) Format Formula 
0 $xxGST NMEA (pseudorange 
measurement noise stats) 
1 (default)$xxGGA NMEA (Global Position 
System Fix) 
2 $xxHDT NMEA (heading) 
N/A 


96 


 
3 $xxZDA NMEA (date & time) 
4,5 reserved 
6 $xxVTG NMEA (track and speed) 
7 $PASHR NMEA (attitude (Tate- 
Bryant)) 
8 $PASHR NMEA (attitude (TSS)) 
9 $PRDID NMEA (attitude (Tate- 
Bryant) 
10 $PRDID NMEA (attitude (TSS) 
11 $xxGGK NMEA (Global Position 
System Fix) 
12 $UTC UTC date and time 
13 reserved 
14 $xxPPS UTC time of PPS pulse 
xx - is substituted by the Talker ID 
Nmea output rate 1 ubyte Value Rate (Hz) 
0 N/A 
1 1 (default) 
2 2 
5 5 
10 10 
20 20 
25 25 
50 50 
Hz 
Talker ID 1 byte Value ID 
0 IN (default) 
1 GP 
N/A 
Roll Sense 1 byte Value Digital +ve 
0 port up (default) 
1 starboard up 
N/A 
Pitch Sense 1 byte Value Digital +ve 
0 bow up (default) 
1 stern up 
N/A 
Heave Sense 1 byte Value Digital +ve 
0 up (default) 
1 down 
N/A 


97 


 
Message 136: Binary Output Set-up 
This message allows the user to configure the real-time binary output on one or more COM 
ports. The COM ports on which the binary output appears is controlled by message 34. 
Note that this is a MV specific version of the Core message 36. 
Table 73: Message 136: Binary Output Set-up 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 136 N/A 
Byte count 2 ushort For even #ports (16 + #ports x 10) 
For odd #ports (14 + #ports x 10) 
N/A 
Transaction # 2 ushort Input: Transaction number set by client 
Output: [65533, 65535] 
N/A 
Reserved 7 byte N/A N/A 
Number of Ports 1 byte [0, 10] N/A 
Binary Port Definitions variable See Table 74: Binary Port Definition #ports x 10 
Pad 0 or 2 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Pad size is 2 bytes if number of ports is even, size is 0 bytes if number of ports is odd. 
Table 74: Binary Port Definition 
Port Number 1 byte [1, 10] N/A 
Formula Select 4 ushort Value Format Formula 
0 - 2 reserved 
3 Simrad1000 header 
(Tate-Bryant) roll = #  
pitch = #  
heave = heave  
heading = #  
4  Simrad1000  header  
N/A  


98 


 
(TSS) roll = sin-1(sin#cos#)  
pitch = #  
heave = heave  
heading = #  
5  Simrad3000  header  
 (Tate-Bryant) roll = #  
pitch =  #  
heave = heave  
heading = #  
6  Simrad3000  header  
 (TSS)  roll = sin-1(sin#cos#)  
pitch = #  
heave = heave  
heading = #  
7  TSS (Format 1) header  
 (default)  horizontal acceleration  
vertical acceleration  
heave = heave  
status  
roll = sin-1(sin#cos#)  
pitch = #  
<CR><LF>  
8  TSM 5265  header  
 (Tate-Bryant)  time tag  
roll = #  
pitch =  #  
heave = heave  
heading = #  
vel (long, trans, down)  
9  TSM 5265  time tag  
 (TSS)  roll = sin-1(sin#cos#)  
pitch = #  
heave = heave  
heading = #  
vel (long, trans, down)  
10  Atlas  header  
 (TSS)  roll = sin-1(sin#cos#)  


99 


 
pitch = #  
heave = heave  
status  
footer  
11 - 15 reserved  
16  PPS  header  
GPS seconds of week  
week number  
UTC offset  
PPS count  
checksum  
17  TM1B  header  
checksum  
byte count  
week number  
GPS seconds of week  
clock offset  
clock offset std. dev.  
UTC offset  
clock model status  
Message Update Rate 2 ushort  Value  Rate (Hz)  
0  N/A  
1  1  
2  2  
5  5  
10  10  
20  20  
25  25 (default)  
50  50  
100  100  
200  200  
Hz  
Roll Sense 1 byte  Value  Digital +ve  
0  port up (default)  
1  starboard up  
N/A  
Pitch Sense 1 byte  Value  Digital +ve  
0  bow up (default)  
1  stern up  
N/A  


100 


 
Heave Sense 1 byte Value Digital +ve 
0 up (default) 
1 down 
N/A 
Sensor Frame Output 1 byte Value Frame of Reference 
0 sensor 1 frame (default) 
1 sensor 2 frame 
N/A 
4.4.6 POS MV Specific Diagnostic Control Messages 
Message 20102: Binary Output Diagnostics 
This message is used to set selected output values for the real-time binary output port. This is 
used to allow POS to generate user selectable constant outputs to test the communications 
interface between POS and the sensor. 
Note that this message must be sent again to disable the fixed output. 
Table 75: Message 20102: Binary Output Diagnostics 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 20102 N/A 
Byte count 2 ushort 24 N/A 
Transaction # 2 ushort Input: Transaction number set by client 
Output: [65533, 65535] 
N/A 
Operator roll input 4 float (-180, 180] default = 0 deg 
Operator pitch input 4 float (-180, 180] default = 0 deg 
Operator heading input 4 float [0, 360) default = 0 deg 
Operator heave input 4 float [-100 to 100] default = 0 m 


101 


 
Item Bytes Format Value Units 
Output Enable 1 byte Value Command 
0 Disabled (default) 
Output navigation solution data 
1 Enabled 
Output operator specified fixed 
values 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 
Message 20103: Analog Port Diagnostics 
This message is used to set the output values for the analog port. This is used to allow POS to 
generate user selectable constant sensor attitude inputs to test the communications interface 
between POS and the sensor. 
Note that this message must be sent again to disable the fixed output. 
Table 76: Message 20103: Analog Port Diagnostics 
Item Bytes Format Value Units 
Message start 4 char $MSG N/A 
Message ID 2 ushort 20103 N/A 
Byte count 2 ushort 20 N/A 
Transaction # 2 ushort Input: Transaction number set by client 
Output: [65533, 65535] 
N/A 
Operator roll input 4 float (-180, 180] default = 0 deg 
Operator pitch input 4 float (-180, 180] default = 0 deg 
Operator heave input 4 float [-100, 100] default = 0 m 


102 


 
Item Bytes Format Value Units 
Output Enable 1 byte Value Command 
0 Disabled (default) 
Output navigation solution data 
1 Enabled 
Output operator specified fixed 
values 
Pad 1 byte 0 N/A 
Checksum 2 ushort N/A N/A 
Message end 2 char $# N/A 


103 


 
5 Appendix A: Data Format Description 
5.1 Data Format 
The data format for byte, short, long, float and double as used in POS are defined as follows: 
Byte or Character 
Table 77: Byte Format 
MSBit LSBit 
7 6 5 4 3 2 1 0 
Short Integer 
The short integer format of the POS data is the INTEL style byte order as follows: 
Table 78: Short Integer Format 
MSB LSB 
15 8 7 0 
Byte #: 1 0 
Long Integer 
The long integer format of the POS data is the INTEL style byte order as follows: 
Table 79: Long Integer Format 
MSB LSB 
31 
24 
23 
16 
15 
8 
7 
0 
Byte #: 3 2 1 0 
Float and Double 
The floating point format of the POS data is the INTEL byte order from the IEEE-754 floating 
point representation standard as follows: 
Table 80: Single-Precision Real Format 
Single-Precision Data format 
31 30 23 22 0 
s e f 


104 


 
Single-Precision Data format 
Field Size in Bits 
Sign (s) 1 
Biased Exponents (e) 8 
Fraction (f) 23 
Total 32 
Interpretation of Sign 
Positive Fraction s=0 
Negative Fraction s=1 
Normalised Numbers 
Bias of Biased Exponent +127 ($7F) 
Range of Biased Exponent [0, 255] ($FF) 
Range of Fraction zero or nonzero 
Fraction 1.f (where f=bit 22 
-1 +bit 21 
-2 ...+bit 0 
-23 ) 
Relation to Representation of Real Numbers (-1) s x2 e-127 x1.f 
Approximate Ranges 
Maximum Positive Normalised 3.4x10 38 
Minimum Positive Normalised 1.2x10 -38 
Table 81: Double-Precision Real Format 
Double-Precision Data format 
63 62 52 51 0 
s e f 
Field Size in Bits 
Sign (s) 1 
Biased Exponents (e) 11 
Fraction (f) 52 
Total 64 


105 


 
Double-Precision Data format 
Interpretation of Sign 
Positive Fraction s=0 
Negative Fraction s=1 
Normalised Numbers 
Bias of Biased Exponent +1023 ($3FF) 
Range of Biased Exponent [0, 2047] ($7FF) 
Range of Fraction zero or nonzero 
Fraction 1.f (where f=bit 51 
-1 +bit 50 
-2 ...+bit 0 
-52 ) 
Relation to Representation of Real Numbers (-1) s x2 e-1023 x1.f 
Approximate Ranges 
Maximum Positive Normalized 1.8x10 308 
Minimum Positive Normalized 2.2x10 -308 
5.2 Invalid Data Values 
Since there are several fields in each group or message, it is possible that one or more numerical 
fields will be invalid when the group or message is output. The following numerical values 
should be interpreted as invalid if they are output in any group or message. This does not apply 
to single or multiple byte fields that are comprised of bit sub-fields. 
The hexadecimal value describes the contents of the bytes that represent the invalid decimal 
value for the type. The invalid values for all integer types are the maximum positive values that 
the integer types can take. 
The invalid value for the floating-point types is any value in the range of NaN (Not a Number) or 
INF (Infinity) defined by IEEE-754. The value NaN is by definition any float or double having a 
mantissa set to any nonzero value and an exponent whose bits are all set to 1. POS MV assigns 
an invalid float or double in any group by setting all bits representing the float or double set to 1. 
POS MV rejects any message that contains any of the invalid integer values in Table 82 or any 
value in the range of NaN or INF. 


106 


 
Table 82: Invalid data values 
Data Type Hexadecimal Value Decimal Value 
Byte FF 255 (=2 8 -- 1) 
Short 7F FF 32767 (=2 15 -- 1) 
Unsigned short (ushort) FF FF 65535 (=2 16 -- 1) 
Long 7F FF FF FF 2147483647 (=2 31 -- 1) 
Unsigned long (ulong) FF FF FF FF 4294967295 (=2 32 -- 1) 
Float FF FF FF FF NaN 
Double FF FF FF FF FF FF FF FF NaN 


107 


 
6 Appendix B: Glossary of Acronyms 
AGC automatic gain control 
AutoConfig auto configure 
Aux auxiliary 
C/A course acquisition 
char character 
COM(1) communications port 1 
COM(2) communications port 2 
COM(3) communications port 3 
D down 
D/A Digital-to-Analog 
dB decibels 
DCM direction cosine matrix 
deg degrees 
deg/s degrees/second 
DGPS differential global positioning system 
DMI distance measurement indicator 
double double precision floating point 
DSP digital signal processor 
E East 
FDIR Fault Detection, Isolation and Reconfiguration 
float floating-point precision 
GAMS GPS Azimuth Measurement Subsystem 
GPS Global Positioning System 
H/W hardware 
HDOP Horizontal Dilution of Precision 
Hz Hertz 
I/O input and output 
ICD interface control document 
IMU Inertial Measurement Unit 
IP Internet Protocol 
KF Kalman filter 
lat latitude 
long longitude 
LSB least significant bit 
m metres 
m/s metres/second 
m/s 2 metres/second/second 
ms millisecond 
MSB most significant bit 
N North 
N/A not applicable 
NOP No Operation 
NVM non-volatile Memory 


108 


 
PCS POS Computer System 
POS Position and Orientation System 
POSPAC Applanix POSPAC post-processing software package 
PPS Pulse per Second 
PRN Pseudo Random Noise 
RAM random access memory 
RF radio frequency 
RMS root-mean-square 
RTK real-time kinematic 
RX receive data 
S/D Strapdown 
SCSI Small Computer Systems Interface 
sec second 
SV space vehicle (GPS satellites) 
TCP Transmission Control Protocol 
UDP User Datagram Protocol 
ulong unsigned long 
ushort unsigned short 
UTC Universal Coordinated Time 
VDOP Vertical Dilution of Precision 
wrt with respect to 

"""