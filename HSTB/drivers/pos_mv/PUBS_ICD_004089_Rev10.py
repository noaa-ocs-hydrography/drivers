Contents = """
POS MV V5 User Interface Control Document 
Document # : PUBS-ICD-004089 Revision: 10 Date: 23 August 2017 
The information contained herein is proprietary to Applanix corporation. Release to third parties of this publication or of information contained herein is prohibited without the prior written consent of Applanix Corporation. Applanix reserves the right to change the specifications and information in this document without notice. A record of the changes made to this document is contained in the Revision History sheet. 
 
 

Table of Contents Page 
1 SCOPE .................................................................................................................................................. 1 
2 ETHERNET AND DATA ACQUISITION INTERFACES................................................................ 1 
3 OUTPUT GROUPS .............................................................................................................................. 3 
3.1 Introduction.................................................................................................................................... 3 
3.2 Output Group Specification ............................................................................................................ 3 
3.2.1 Group Data Rates .................................................................................................................... 3 
3.2.2 Group Classification and Numbering Convention .................................................................. 3 
3.2.3 Group Format .......................................................................................................................... 5 
3.2.4 Compatibility with Previous POS Products ............................................................................ 8 
3.3 Output Group Tables ...................................................................................................................... 8 
3.3.1 POS Data Groups.................................................................................................................... 8 Group 1: Vessel Position, Velocity, Attitude & Dynamics ................................................................ 8 Group 2: Vessel Navigation Performance Metrics .......................................................................... 10 Group 3: Primary GNSS Status........................................................................................................ 11 Group 4: Time-tagged IMU Data ..................................................................................................... 14 Group 5: Event 1 .............................................................................................................................. 15 Group 6: Event 2 .............................................................................................................................. 15 Group 7: PPS Time Recovery and Status ........................................................................................ 15 Group 8: Logging Parameters and Status ......................................................................................... 16 Group 9: GAMS Solution ................................................................................................................ 17 Group 10: General Status and FDIR ................................................................................................ 19 Group 11: Secondary GNSS Status .................................................................................................. 24 Group 12: Auxiliary 1 GPS Status ................................................................................................... 25 Group 13: Auxiliary 2 GPS Status ................................................................................................... 26 Group 14: Calibrated Installation Parameters .................................................................................. 27 Group 17: User Time Status............................................................................................................. 29 Group 20: IIN Solution Status .......................................................................................................... 29 Group 21: Base GPS 1 ModemStatus ............................................................................................. 31 Group 22: Base GPS 2 ModemStatus ............................................................................................. 31 Group 23: Auxiliary 1 GPS Display Data ........................................................................................ 31 Group 24: Auxiliary 2 GPS Display Data ........................................................................................ 32 Group 29: GNSS Receiver MarineSTAR Status.............................................................................. 32 Group 99: Versions and Statistics .................................................................................................... 35 Group 102: Sensor 1 Position, Velocity,Attitude, Heave & Dynamics .......................................... 36 Group 103: Sensor 2 Position, Velocity,Attitude, Heave & Dynamics .......................................... 36 Group 104: Sensor 1 Position, Velocity,and Attitude Performance Metrics .................................. 38 
ii 
 
 
Group 105: Sensor 2 Position, Velocity,and Attitude Performance Metrics .................................. 38 Group 110: MV General Status & FDIR ......................................................................................... 39 Group 111: Heave & True Heave Data ............................................................................................ 39 Group 112: NMEA Strings .............................................................................................................. 40 Group 113: Heave & True Heave Performance Metrics .................................................................. 41 Group 114: TrueZ & TrueTide Data ................................................................................................ 41 
3.3.2 Raw Data Groups.................................................................................................................. 42 Group 10001: Primary GPS Data Stream ........................................................................................ 42 Group 10002: Raw IMU Data .......................................................................................................... 43 Group 10003: Raw PPS................................................................................................................... 44 Group 10007: Auxiliary 1 GPS Data Stream ................................................................................... 44 Group 10008: Auxiliary 2 GPS Data Stream ................................................................................... 44 Group 10009: Secondary GPS Data Stream .................................................................................... 45 Group 10011: Base GPS 1 Data Stream .......................................................................................... 46 Group 10012: Base GPS 2 Data Stream .......................................................................................... 46 
MESSAGE INPUT AND OUTPUT................................................................................................... 47 
4.1 Introduction.................................................................................................................................. 47 
4.2 Message Output Data Rates .......................................................................................................... 47 
4.2.1 Message Numbering Convention .......................................................................................... 47 
4.2.2 Compatibility with Previous POS Products .......................................................................... 49 
4.3 Message Format ........................................................................................................................... 50 
4.3.1 Introduction ........................................................................................................................... 50 
4.4 Messages Tables ........................................................................................................................... 51 
4.4.1 General Messages .................................................................................................................. 51 Message 0: Acknowledge................................................................................................................ 51 
4.4.2 Installation Parameter Set-up Messages ................................................................................ 53 Message 20: General Installation and Processing Parameters......................................................... 53 Message 21: GAMS Installation Parameters ................................................................................... 58 Message 24: User Accuracy Specifications ..................................................................................... 60 Message 30: Primary GPS Setup ..................................................................................................... 60 Message 31: Secondary GPS Setup ................................................................................................. 63 Message 32: Set POS IP Address ..................................................................................................... 65 Message 33: Event Discrete Setup ................................................................................................... 67 Message 34: COM Port Setup .......................................................................................................... 69 Message 35: See Message 135 ......................................................................................................... 72 Message 36: See Message 136 ......................................................................................................... 72 Message 37: Base GPS 1 Setup ....................................................................................................... 72 Message 38: Base GPS 2 Setup ....................................................................................................... 72 
iii 
 
 
Message 39: Aux GNSS Setup ........................................................................................................ 74 Message 41: Primary GPS Receiver Integrated DGPS Source Control........................................... 75 
4.4.3 Processing Control Messages ................................................................................................ 77 Message 50: Navigation Mode Control........................................................................................... 77 Message 51: Display Port Control ................................................................................................... 78 Message 52: Real-Time Data Port Control ...................................................................................... 79 Message 53: Logging PortControl.................................................................................................. 81 Message 54: Save/Restore Parameters Control ................................................................................ 83 Message 55: User Time Recovery ................................................................................................... 84 Message 56: General Data............................................................................................................... 84 Message 57: Installation Calibration Control................................................................................... 86 Message 58: GAMS Calibration Control ......................................................................................... 88 Message 61: Logging Data Port Control.......................................................................................... 89 
4.4.4 Program Control Override Messages .................................................................................... 90 Message 90: Program Control .......................................................................................................... 90 Message 91: GPS Control ................................................................................................................ 91 
4.4.5 POS MV Specific Messages ................................................................................................. 92 Message 106: Heave Filter Set-up ................................................................................................... 92 Message 111: Password Protection Control ..................................................................................... 93 Message 120: Sensor Parameter Set-up........................................................................................... 94 Message 121: Vessel Installation Parameter Set-up ........................................................................ 96 Message 135: NMEA Output Set-up............................................................................................... 97 Message 136: Binary Output Set-up ................................................................................................ 99 
4.4.6 POS MV Specific Diagnostic Control Messages ................................................................ 102 Message 20102: BinaryOutput Diagnostics .................................................................................. 102 
5 APPENDIX A: DATA FORMAT DESCRIPTION ......................................................................... 104 
5.1 Data Format ................................................................................................................................ 104 
5.2 Invalid Data Values .................................................................................................................... 106 
6 APPENDIX B: GLOSSARY OF ACRONYMS ................................................................................... 1 
iv 
 
 

List of Tables 
Table 1: Output Group Data Rates ................................................................................................................ 4 Table 2: Group format .................................................................................................................................. 5 Table 3: Time and distance fields ................................................................................................................. 6 Table 4: Group 1: Vessel position, velocity, attitude & dynamics ............................................................... 9 Table 5: Group 1 alignment status .............................................................................................................. 10 Table 6: Group 2: Vessel navigation performance metrics ......................................................................... 10 Table 7: Group 3: Primary GNSS status ..................................................................................................... 11 Table 8: GNSS receiver channel status data ............................................................................................... 12 Table 9: GNSS navigation solution status .................................................................................................. 13 Table 10: NAVCOM navigation solution status ......................................................................................... 13 Table 11: GNSS channel status ................................................................................................................... 14 Table 12: GNSS receiver type .................................................................................................................... 14 Table 13: Group 4: Time-tagged IMU data ................................................................................................ 15 Table 14: Group 5/6: Event 1/2 .................................................................................................................. 15 Table 15: Group 7: PPS Time Recovery and Status ................................................................................... 16 Table 16: Group 8: Logging Information ................................................................................................... 17 Table 17: Group 9: GAMS Solution Status ................................................................................................ 18 Table 18: Group 10: General and FDIR status ........................................................................................... 19 Table 19: Group 11: Secondary GNSS status ............................................................................................. 24 
Table 20: Group 12/13: Auxiliary 1/2GPS status ...................................................................................... 26 Table 21: Group 14: Calibrated installation parameters ............................................................................. 27 Table 22: IIN Calibration Status ................................................................................................................. 28 Table 23: Group 17: User Time Status ....................................................................................................... 29 Table 24: Group 20: IIN solution status ...................................................................................................... 30 Table 25: Group 21/22: Base GPS 1/2 ModemStatus................................................................................ 31 Table 26: Group 23/24: Auxiliary 1/2GPS raw displaydata ..................................................................... 32 Table 27: Group 29: GNSS Receiver MarineSTAR Status ........................................................................ 32 Table 28: Group 99: Versions and statistics ............................................................................................... 35 Table 29: Group 102/103:Sensor 1/2 Position, Velocity, Attitude, Heave & Dynamics ........................... 37 Table 30: Group 104/105:Sensor 1/2 Position, Velocity, and Attitude Performance Metrics ................... 38 Table 31: Group 110: MVGeneral Status & FDIR .................................................................................... 39 Table 32: Group 111: Heave & True Heave Data....................................................................................... 39 Table 33: Group 112: NMEA Strings ......................................................................................................... 40 Table 34: Group 113: Heave & True Heave Performance Metrics............................................................. 41 Table 35: Group 114: TrueZ & TrueTide Data ........................................................................................... 42 
v 
 
 
Table 36: Group 10001: Primary GPS data stream ..................................................................................... 42 Table 37: Group 10002: Raw IMU data ..................................................................................................... 43 Table 38: Group 10003: Raw PPS .............................................................................................................. 44 Table 39: Group 10007/10008: Auxiliary 1/2 GPS data streams ............................................................... 44 Table 40: Group 10009: Secondary GPS data stream ................................................................................. 45 Table 41: Group 10011/10012: Base GPS 1/2 data stream ......................................................................... 46 Table 42: Control messages output data rates ............................................................................................. 48 Table 43: Message format........................................................................................................................... 50 Table 44: Message 0: Acknowledge ........................................................................................................... 52 Table 45: Message response codes............................................................................................................. 52 Table 46: Message 20: General Installation and Processing Parameters .................................................... 56 Table 47: Message 21: GAMS installation parameters............................................................................... 59 Table 48: Message 24: User accuracy specifications .................................................................................. 60 Table 49: Message 30: Primary GPS Setup ................................................................................................ 61 Table 50: RS-232/422 communication protocol settings ............................................................................ 62 Table 51: Message 31: Secondary GPS Setup ............................................................................................ 64 Table 52: Message 32: Set POS IP Address............................................................................................... 65 Table 53: Message 33: Event Discrete Setup .............................................................................................. 68 Table 54: Message 34: COM Port Setup .................................................................................................... 70 Table 55: COM port parameters................................................................................................................. 71 Table 56: Message 37/38: Base GPS 1/2 Setup .......................................................................................... 73 Table 57: Message 39: Aux GNSS Setup ................................................................................................... 74 Table 58: Message 41: Primary GPS Receiver Integrated DGPS Source Control..................................... 75 Table 59: Message 50: Navigation mode control ....................................................................................... 77 Table 60: Message 51: Display Port Control .............................................................................................. 78 Table 61: Message 52 Real-Time/Logging Data Port Control................................................................... 80 Table 62: Message 53: Logging Port Control ............................................................................................. 82 Table 63: Message 54: Save/restore parameters control ............................................................................. 83 Table 64: Message 55: User time recovery ................................................................................................. 84 Table 65: Message 56: General data ........................................................................................................... 85 Table 66: Message 57: Installation calibration control ............................................................................... 87 Table 67: Message 58: GAMS Calibration Control .................................................................................... 88 Table 68: Message 61: Second Data PortControl...................................................................................... 89 Table 69: Message 90: Program Control .................................................................................................... 90 Table 70: Message 91: GPS control ............................................................................................................ 91 Table 71: Message 106: Heave Filter Set-up .............................................................................................. 92 Table 72: Message 111: Password Protection Control............................................................................... 93 Table 73: Message 120: Sensor Parameter Set-up ...................................................................................... 95 Table 74: Message 121: Vessel Installation Parameter Set-up ................................................................... 96 
vi 
 
 
Table 75: Message 135: NMEA Output Set-up .......................................................................................... 97 Table 76: NMEA Port Definition................................................................................................................ 98 Table 77: Message 136: BinaryOutput Set-up ........................................................................................... 99 Table 78: BinaryPort Definition .............................................................................................................. 100 Table 79: Message 20102: Binary Output Diagnostics ............................................................................. 103 Table 80: Byte Format .............................................................................................................................. 104 Table 81: Short Integer Format ................................................................................................................. 104 Table 82: Long Integer Format ................................................................................................................. 104 Table 83: Single-Precision Real Format ................................................................................................... 104 Table 84: Double-Precision Real Format .................................................................................................. 105 Table 85: Invalid data values .................................................................................................................... 106 
vii 
 
"""

Structures = """
 

1 Scope 
This document presents the functional specification of the POS MV Control, Display and Data Ports and data structures used by the POS Computer System (PCS) to communicate with the user over its Control, Display and Data Ports. The document is separated into specifications of output data groups and input and output control messages that are relevant to the user. 
This document describes the data structures that are implemented in the V5 systemversion of POS MV. POS MV V5 shall hereafter be refered to as POS MV or simply POS. 

2 Ethernet and DataAcquisition Interfaces 
The POS MV provides a mechanismfor control and data exchange in the formof control messages and data groups. Control messages direct POS MV to execute a well-defined action such as mode transition, or start or stop of data acquisition. Data groups contain the data output by the POS MV for the purpose of display on a control computer, recording to a mass storage device, or for real-time processing by another subsystem. POS MV exchanges all control messages with a user via the POS's Control Port. It outputs all data groups on the Display and Data Logging Ports. 
Applanix provides a programcalled MV POSView with the POS MV to run on the user's PC-compatible computer running Microsoft Windows XP/Vista/7. The user's PC is called the client computer and is used to both control the system and allow the user to view POS data via the control messages and data groups specified in this document. The user can create custom control and display software that implements similar functionality. In either case, the program that provides the control and display functions on the client computer will hereafter be referred to as the POS Controller. 
POS MV provides one physical Ethernet interface that has four logical communications ports 
called the Display Port, the Control Port, the Real-Time Data Port and the Logging Data Port. POS MV outputs data in specified group formats defined in the body of this document. Messages are used to both change and describe the systemconfiguration. Both message and group data are output on three ports: Display, Real-Time Data and Logging Data. Messages are input on the Control Port. 
The Display Port is a low rate UDP output port that is designed to broadcast low rate data and status information for display. The POS Controller reads the message and group data fromthis port for display purposes. POS MV is designed to allow multiple POS Controller programs running on different computers to receive and display data from the PCS. However, only one POS Controller at any time can be designated as the master controller and be capable of sending commands to the PCS via the Control Port. This arrangement prevents conflicting controller information from being received by the PCS. 
The port address for the Display Port is 5600. The subnet mask is 255.255.255.255. The Real-Time Data Port is a high rate UDP output port that is designed to output multiple data 
1 
 
 
groups at high data rates with minimal latency. Since there is no handshaking implemented in UDP there is a possibility that the client may not receive all data packets. The Real-Time Data Port design emphasizes real-time delivery of the data without the overhead of ensuring totally reliable data transfer. Toreceive data fromthe Real-Time Data Port, a computer must listen to the port using the UDP socket protocol. Several computers may be connected to the Real-Time Data Port at any one time. MV POSView uses this port to obtain some higher rate data from POS MV that is required for display plots. 
The Logging Data Port is a high rate TCP/IP output port that is designedto output multiple data groups at high data rates. The emphasis is on reliable and efficient data transfer to the client computer. The Logging Data Port implements several buffers to store data in the event the TCP/IP connection between POS and the client computer becomes bogged down or requires retransmission of packets. To receive data fromthe Logging Data Port, a computer must connect to it using the TCP/IP socket protocol. Only one computer may be connected to the Logging Data Port at any one time. MV POSView can log this data to the client computer's hard drive. 
The port address for the Real-Time Data Port is 5602 and 5603 for the Logging Data Port. The 
IP subnet mask is 255.255.255.255. The user is able to select, fromseveral different options, the data required for output. Each port can be configured to output different data than the other ports. POS MV accepts changes to the output options of the Display, Data and Logging ports at any time. MV POSView automatically sends the Display Port control message to output the data groups that it requires to populate the display windows as the user opens them. 
The Control Port is designed to receive set-up and control commands fromthe POS Controller and to acknowledge the commands to indicate successful reception of each message. The Control Port is bi-directional and uses the TCP/IP protocol to communicate with the POS Controller. 
The port address for the Control Port is 5601. The IP subnet mask is 255.255.255.255. 
2 
 
 

3 Output Groups 
3.1 Introduction 
POS MV organizes the data going to the Display and Data ports into output groups. Each group contains a block of related data at a specified group rate. The user directs POS MV via Control Port messages generated by the POS Controller to include a group or groups containing data items of interest in the Display and Data port data streams. The output groups have been designed to allow simple parsing and decoding of the output data streams into the selected groups. All groups are framed by ASCII delimiters and have identifiers that uniquely identify each group. 
The output data rate on the Display Port is typically once per second or less. This output is intended for updating the POS Controller display; hence a higher data output rate is not required. The output data rate on the Data Ports is group dependent and has a range from1Hz to an IMU rate. For certain output groups, it is possible to select, from several options, the output data rate of choice on the Data ports. 

3.2 Output Group Specification 
3.2.1 Group Data Rates 
There are several output groups defined for the Display and Data ports. The user can select any of these groups and may select different groups for the Display Port, Real-Time Data Port and Logging Data Port. The Standby and Navigate modes shown in Table 1 are defined in POS MV  User Guide. 

3.2.2 Group Classification and Numbering Convention 
All POS products use the following group numbering convention. POS MV outputs the group categories shown. Reserved group numbers are assigned to other products. 0 - 99 POS Core User data groups 100 - 199 POS MV User data groups 200 - 9999 Reserved 10000 - 10099 POS Core Raw data groups 10100 - 10199 POS MV Raw data groups 10200 - 19999 Reserved 20000 POS Core User diagnostic group 20001 - 20099 Reserved 
20100 POS MV User diagnostic group Core User data groups and MV User data groups comprise groups that contain real-time operational data. During normal operation, these are the only groups that a user would require for observing or recording relevant POS MV data. 
3 
 
 
Core Rawdata groups and POS MV Raw data groups comprise the unaltered data streams from the navigation sensors received by the PCS. POS MV packages the sensor data into the specified group formats and outputs the groups. These groups are typically used for post-mission processing and analysis. 

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
Group  Contents  Display Port Output Rate (Hz)  Real-Time Data Port Output Rate (Hz)  Logging Data Port Output Rate (Hz)  
Standby  Navigate  Standby  Navigate  Standby  Navigate  
POS Data Groups  
1  Vessel position, velocity, attitude & dynamics in vessel frame  - 11  - 1-2003  - 1-2003  
2  Vessel navigation performance metrics  - 11  - 1  - 1  
3  Primary GPS status  11  11  1  1  1  1  
4  Time-tagged IMU data  1  1  2003  2003  2003  2003  
5  Event 1 data2  1  1  1-500  1-500  1-500  1-500  
6  Event 2 data2  1  1  1-500  1-500  1-500  1-500  
7  PPS data2  1  1  1  1  1  1  
8  Reserved  - - - - - - 
9  GAMS solution status  - 1  - 1  - 1  
10  General and FDIR status  11  11  1  1  1  1  
11  Secondary GPS status  1  1  1  1  1  1  
12  Auxiliary 1 GPS status  1  1  1  1  1  1  
13  Auxiliary 2 GPS status  1  1  1  1  1  1  
14  Calibrated installation parameters  - 1  - 1  - 1  
15  Reserved  - - - - - - 
16  Reserved  - - - - - - 
17  User time status  1  1  1  1  1  1  
20  IIN solution status  - 1  - 1  - 1  
21  Base 1 GPS modem status  1  1  1  1  1  1  
22  Base 2 GPS modem status  1  1  1  1  1  1  
23  Auxiliary 1 GPS display data2  1  1  1  1  1  1  
24  Auxiliary 2 GPS display data2  1  1  1  1  1  1  
25  Reserved  - - - - - - 
26  Reserved  - - - - - - 
29  GNSS Receiver Marinestar Status  1  1  - - - - 
99  Versions and statistics  1  1  1  1  1  1  
102  Sensor 1 position, velocity, attitude, heave & dynamics  - 1  - 1-2003  - 1-2003  
103  Sensor 2 position, velocity, attitude, heave & dynamics  - 1  - 1-2003  - 1-2003  
104  Sensor 1 position, velocity & attitude performance metrics  - 1  - 1  - 1  

4 
 
 
Group  Contents  Display Port Output Rate (Hz)  Real-Time Data Port Output Rate (Hz)  Logging Data Port Output Rate (Hz)  
Standby  Navigate  Standby  Navigate  Standby  Navigate  
105  Sensor 2 position, velocity & attitude performance metrics  - 1  - 1  - 1  
110  MV general status & FDIR  1  1  1  1  1  1  
111  Heave & True Heave  - 1  - 25  - 25  
112  NMEA strings  - 1  - 1-50  - 1-50  
113  Heave performance metrics  - 1  - 25  - 25  
114  TrueZ and TrueTide altitude  - 1  - 25  - 25  
Raw Data Groups  
10001  Primary GPS data stream  - - 1-10  1-10  1-10  1-10  
10002  IMU data stream  - - 2003  2003  2003  2003  
10003  PPS data  - - 1  1  1  1  
10007  Auxiliary 1 GPS data stream  1-10  1-10  1-10  1-10  
10008  Auxiliary 2 GPS data stream  1-10  1-10  1-10  1-10  
10009  Secondary GPS data stream  - - 1-10  1-10  1-10  1-10  
10010  Reserved  - - - - - - 
10011  Base 1 GPS data stream  - - 0-1  0-1  0-1  0-1  
10012  Base 2 GPS data stream  - - 0-1  0-1  0-1  0-1  

Note: When POS is in Navigation mode but not aligned then the output rate is implementation dependent. 
1 These groups are the minimum output of the Display Port for driving the POS View display and cannot be deselected. 2 Groups are only posted when data were available. 3 Maximum output rate for WaveMaster is 100 Hz 

3.2.3 Group Format 
The structure of each output group is defined in this section. The group structure is the same for all groups and consists of a header, data and footer. Table 2 presents the complete groups format, showing the header and footer separated by the data. The next section specifies the data for each group. 
Table 2: Group format 
Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  Group number  N/A  
Byte count  2  ushort  Group dependent  bytes  
Time/Distance Fields  26  See Table 3  
Data  Group dependent size and format  
Pad  0 to 3  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  

5 
 
 
Item  Bytes  Format  Value  Units  
Group end  2  char  $#  N/A  

Table 3: Time and distance fields 
Item  Bytes  Format  Value  Units  
Time 1  8  double  N/A  seconds  
Time 2  8  double  N/A  seconds  
Distance tag  8  double  N/A  meters  
Time types  1  byte  Time 1 Select Value in bits 0-3, Time 2 Select Value in bits 4-7  
Time 1: POS time 0 Time 1: GPS time 1 Time 1: UTC time 2 (default) 
Time 2: POS time 0 (default) Time 2: GPS time 1 Time 2: UTC time 2 Time 2: User time 3  
Distance type  1  byte  Distance Select Value N/A 0 POS distance 1 (default) DMI distance 2  

The header consists of the following components: 
. ASCII group start ($GRP) 
. group identification (Group ID) number 
. byte count 
. time/distance fields 
The group identification or Group ID is a short unsigned integer equal to the group number 
having the group numbering convention described in Section 3.2.2. The byte count is a short unsigned integer that includes all fields in the group except the $GRP delimiter, the Group ID and the byte count. Therefore, the byte count is always 8 bytes less than the length of the group. 
The time/distance fields are shown in Table 3. These occupy 26 bytes and have the same format across all groups. They comprise the following: 
. Time 1 
6 
 
 
. Time 2 . Distance tag and time and distance type flags. Time 1 is the POS MV systemtime of validity of the data in the group, given in one of the 
following time bases: . POS time (time in seconds since power-on) . GPS seconds of the week . UTC seconds of the week 
The user can select any of these times for Time 1. Time 1 is set to POS time on power-up and changes to the user selected time base once the primary GPS receiver has locked on to a sufficient number of satellites to compute a time solution. 
Time 2 is the POS MV systemtime of validity of the data in the group, given in one of the following time bases: . POS time (time in seconds since power-on) . GPS seconds of the week . UTC seconds of the week 
. User time User time is specified by the user, with the procedure to set user time described in the POS MV User Guide. It allows the groups to be time tagged with an external computer's time clock. The Time 2 field is always set to POS time for the raw(10000) series of data groups. 
Distance tag is the distance of validity of the data in the group as determined by one of the following distance measurement sources: . distance traveled derived from the POS MV blended navigation solution 
. DMI (distance measurement index) distance tag The group data follows the header. Its format is dependent on the particular group. Some group data lengths are fixed, whereas others may vary. For variable length groups the byte count is always updated to reflect the actual length of the group. 
The group is terminated by the footer, which consists of the following components: . a pad (if required) . checksum . ASCII group end delimiter ($#). 
The pad is used to make the total lengths of all groups a multiple of four bytes. The checksum is calculated so that the sum of byte pairs cast as short (16 bit) integers over the complete group results in a net sum of zero. 
The byte, short, ushort, long, ulong, float and double formats are defined in Appendix A: Data Format Description. 
7 
 
 
The ranges of valid values for group fields that contain numbers are specified using the 
following notation. [a, b] implies the range a to b including the range lower and upper boundaries. A value x that falls in this range will respect theinequality a . x . b. 
(a, b) implies the range a to b excluding the range lower and upper boundaries. A value x 
that falls in this range will respect theinequality a . x . b. (a, b] implies the range a to b excluding the lower boundary and including the upper boundary. A value x that falls in this range will respect the inequality a . x . b. 
[a, b) implies the range a to b excluding the range lower and upper boundaries. A value x that falls in this range will respect theinequality a . x . b. If a value a or b is not given, then there is no corresponding lower or upper boundary. The following are special cases: (0, ) represents all positive numbers (excludes 0) [0, ) represents all non-negative numbers (includes 0) ( , 0) represents all negative numbers (excludes 0) ( , 0] represents all non-positive numbers (includes 0) 
( , ) represents all numbers in the range of valid numbers. Group fields that contain numerical values may contain invalid numbers. Invalid byte, short, ushort, long, ulong, float and double values are defined in Table 85 in Appendix A: Data Format Description. POS MV outputs invalid values in fields containing numerical values for which POS MV has no valid data. This does not apply to fields containing bit settings. 

3.2.4 Compatibility with Previous POS Products 
The compatibility of POS MV groups with POS MV V4 products is given as follows: 
The POS MV V5 group format and group content is the same as that of the POS MV V4 products. 


3.3 Output Group Tables 
3.3.1 POS Data Groups 
Group 1: Vessel Position, Velocity, Attitude & Dynamics 
The POS MV group 1 contains data valid for the position defined by the user-entered reference to vessel lever arms (see Message 121: Vessel Installation Parameter Set-up). POS MV assumes the vessel and reference frames are co-aligned, therefore the reference to vessel mounting angles (see Message 20: General Installation and Processing Parameters) should be zero. 
8 
 
 
The roll, pitch and heading data contained in this group are provided using the Tate-Bryant sequence. That is, pitch is provided with respect to local level, and roll is output with respect to the pitched X-Y plane. See the POS MV User Guide page 2-29 for a fuller explanation. 
Table 4: Group 1: Vessel position, velocity, attitude & dynamics 
Item  Bytes  Format  Value  Units  
Group start  4  Char  $GRP  N/A  
Group ID  2  Ushort  1  N/A  
Byte count  2  Ushort  132  bytes  
Time/Distance Fields  26  See Table 3  
Latitude  8  double  (-90, 90]  degrees  
Longitude  8  double  (-180, 180]  degrees  
Altitude  8  double  ( , )  meters  
North velocity  4  float  ( , )  meters/second  
East velocity  4  float  ( , )  meters/second  
Down velocity  4  float  ( , )  meters/second  
Vessel roll  8  double  (-180, 180]  degrees  
Vessel pitch  8  double  (-90, 90]  degrees  
Vessel heading  8  double  [0, 360)  degrees  
Vessel wander angle  8  double  (-180, 180]  degrees  
Vessel track angle  4  float  [0, 360)  degrees  
Vessel speed  4  float  [0, )  meters/second  
Vessel angular rate about longitudinal axis  4  float  ( , )  degrees/second  
Vessel angular rate about transverse axis  4  float  ( , )  degrees/second  
Vessel angular rate about down axis  4  float  ( , )  degrees/second  
Vessel longitudinal acceleration  4  float  ( , )  meters/second2  
Vessel transverse acceleration  4  float  ( , )  meters/second2  
Vessel down acceleration  4  float  ( , )  meters/second2  
Alignment status  1  byte  See Table 5  N/A  
Pad  1  byte  0  N/A  

9 
 
 
Item  Bytes  Format  Value  Units  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Table 5: Group 1 alignment status 
Group 1 Status  Description  
0  Full navigation (User accuracies are met)  
1  Fine alignment is active (RMS heading error is less than 15 degrees)  
2  GC CHI 2 (alignment with GPS, RMS heading error is greater than 15 degrees)  
3  PC CHI 2 (alignment without GPS, RMS heading error is greater than 15 degrees)  
4  GC CHI 1 (alignment with GPS, RMS heading error is greater than 45 degrees)  
5  PC CHI 1 (alignment without GPS, RMS heading error is greater than 45 degrees)  
6  Coarse leveling is active  
7  Initial solution assigned  
8  No valid solution  

Group 2: Vessel Navigation Performance Metrics This group contains vessel position, velocity and attitude performance metrics. The data in this group is valid for the position defined by the user-entered reference vessel lever arms. All data items in this group are given in RMS values. 
Table 6: Group 2: Vessel navigation performance metrics 
Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  2  N/A  
Byte count  2  ushort  80  bytes  
Time/Distance Fields  26  See Table 3  
North position RMS error  4  float  [0, )  meters  
East position RMS error  4  float  [0, )  meters  
Down position RMS error  4  float  [0, )  meters  
North velocity RMS error  4  float  [0, )  meters/second  
East velocity RMS error  4  float  [0, )  meters/second  
Down velocity RMS error  4  float  [0, )  meters/second  

10 
 
 
Item  Bytes  Format  Value  Units  
Roll RMS error  4  float  [0, )  degrees  
Pitch RMS error  4  float  [0, )  degrees  
Heading RMS error  4  float  [0, )  degrees  
Error ellipsoid semi-major  4  float  [0, )  meters  
Error ellipsoid semi-minor  4  float  [0, )  meters  
Error ellipsoid orientation  4  float  (0, 360]  degrees  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 3: Primary GNSS Status 
This group contains status data fromthe primary GNSS receiver. The group length is variable, depending on the number of primary GNSS receiver channels that report data. The primary GNSS receiver supports a large number of channels (>200 but not all active at the same time) and therefore group 3 provides up to 60 channel status fields. Each channel status field has the format given in Table 8. The GNSS receiver type field identifies the primary GNSS receiver in POS MV from among the GNSS receiver types listed in Table 12 that POS MV supports. The GNSS status field comprises a 4-byte array of status bits whose format depends on the GNSS receiver type. 
Table 7: Group 3: Primary GNSS status 
Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  3  N/A  
Byte count  2  ushort  76 + 20 x (number of channels)  bytes  
Time/Distance Fields  26  See Table 3  
Navigation solution status  1  byte  See Table 9  N/A  
Number of SV tracked  1  byte  [0, 60]  N/A  
Channel status byte count  2  ushort  [0, 1200]  bytes  
Channel status  variable  See Table 8  
HDOP  4  float  ( , )  N/A  
VDOP  4  float  ( , )  N/A  
DGPS correction latency  4  float  [0, 999.9]  seconds  
DGPS reference ID  2  ushort  [0, 1023]  N/A  

11 
 
 
Item  Bytes  Format  Value  Units  
GPS/UTC week number  4  ulong  [0, 9999) 0 if not available  week  
GPS/UTC time offset (GPS time - UTC time)  8  double  ( , )  seconds  
GNSS navigation message latency  4  float  Number of seconds from the PPS pulse to the start of the GNSS navigation data output  seconds  
Geoidal separation  4  float  ( , )  meters  
GNSS receiver type  2  ushort  See Table 12  N/A  
GNSS status  4  ulong  GNSS summary status fields which depend on GNSS receiver type.  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Table 8: GNSS receiver channel status data 
Item  Bytes  Format  Value  Units  
SV PRN  2  ushort  [1, 138]  N/A  
Channel tracking status  2  ushort  See Table 11  N/A  
SV azimuth  4  float  [0, 360)  degrees  
SV elevation  4  float  [0, 90]  degrees  
SV L1 SNR  4  float  [0, )  dB  
SV L2 SNR  4  float  [0, )  dB  

SV PRN is encoded as follows: GPS: 1 - 37  GLONASS: 52 - 75, offset 51 BeiDou: 76 - 105, offset 75 SBAS: 120 - 138  QZSS: 193 - 197  Galileo: 201 - 252, offset 200 
12 
 
 
Table 9: GNSS navigationsolution status 
Status Value  Description  Expected Accuracy  
-1  Unknown  N/A  
0  No data from Receiver  N/A  
1  Horizontal C/A mode (unconstrained vertical position)  75 meters  
2  3-dimension C/A mode  75 meters  
3  Horizontal DGPS mode (unconstrained vertical position)  1 meter  
4  3-dimension DGPS mode  1 meter  
5  Float RTK mode  0.25 meters  
6  Integer wide lane RTK mode  0.2 meters  
7  Integer narrow lane RTK mode  0.02 meters  
8  P-Code mode  10 meters  
9  HP (Marinestar) mode  0.1 meters  
10  HPXP (Marinestar) mode  0.1 meters  
11  HPG2 (Marinestar) mode  0.1 meters  
12  XP (Marinestar) mode  0.2 meters  
13  VBS mode  1 meter  
15  G2 (Marinestar) mode  0.2 meters  
Table 10: NAVCOM navigation solution status 


C-Nav / NAVCOM Solution ID (DGPS Ref ID)  Description  Expected Accuracy  
06  StarFire RTG Single Frequency (no TA)  0.25 meters  
11  StarFire RTG Dual Frequency (no TA)  0.25 meters  
24  StarFire TG Single Frequency (TA)  0.25 meters  
25  Starfire RTG Dual Frequency (TA)  0.25 meters  
26  Starfire RTK Extend  0.25 meters  
33  StarFire GNSS RTG Single Frequency (no TA)  0.25 meters  
34  Aux StarFire GNSS RTG Dual Frequency (no TA)  0.25 meters  
35  StarFire GNSS RTG Single Frequency (TA)  0.25 meters  
36  Aux StarFire GNSS RTG Dual Frequency (TA)  0.25 meters  

13 
 
 
Any other C-Nav / NAVCOM Solution ID other than those explicitly identified above shall map to the appropriate auxiliary aiding mode based on the standard NMEA solution status flag (field 6 in the $xxGGA message) and (if available) the aux. GST message. 
Table 11: GNSS channel status 

Channel Status  Description  
0  L1 Idle  
1  Reserved  
2  L1 acquisition  
3  L1 Code lock  
4  Reserved  
5  L1 Phase lock (full performance tracking for L1-only receiver)  
6  L2 Idle  
7  Reserved  
8  L2 acquisition  
9  L2 Code lock  
10  Reserved  
11  L2 phase lock (full performance for L1/L2 receiver)  

Table 12: GNSS receiver type 
GNSS type  Description  
0  No receiver  
1 to 15  Reserved  
16  Trimble BD960  
17  Trimble BD982  
17 and up  Reserved  

Group 4: Time-tagged IMU Data 
This group consists of the time-tagged IMU data that is suitable for import by POSPAC, Applanix' post-processing software package. U.S. and Canadian export control laws prohibit publication of the IMU data format. 
14 
 
 
Table 13: Group 4: Time-tagged IMU data 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  4  N/A  
Byte count  2  ushort  60  bytes  
Time/Distance Fields  26  See Table 3  
IMU Data  29 byte  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 5: Event 1 
The time and distance fields in this group indicate the time and distance of Event 1 discrete signals that the POS MV receives. A client can use this message to attach GPS/UTC time to external events. 
Group 6: Event 2 
The time and distance fields in this group indicate the time and distance of Event 2 discrete signals that the POS MV receives. A client can use this message to attach GPS/UTC time to external events. 
Table 14: Group 5/6: Event 1/2 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  5 or 6  N/A  
Byte count  2  ushort  36  bytes  
Time/Distance Fields  26  See Table 3  
Event pulse number  4  ulong  [0, )  N/A  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 7: PPS Time Recovery and Status 
The time and distance fields in this group indicate the time and distance of the PPS fromthe primary GPS receiver. The PPS count is the number of PPS messages since power-up and 
15 
 
 
initialization of the GPS receivers. The time synchronization status field indicates the status of 
POS MV synchronization to the PPS time provided by the primary GPS receiver as follows: No synchronization indicates that the POS MV has not synchronized to GPS time. This is the case if the GPS receiver has not initialized and provided time recovery data to the POS MV. 
Synchronizing indicates that the POS MV is in the process of synchronizing to GPS time. This lasts on the order of 10-20 seconds as the POS MV establishes its internal clock offset and drift parameters. 
Fully synchronized indicates that the POS MV has established synchronization to GPS time 
with less than 10 microseconds error and is maintaining the synchronization once per second. Using old offset indicates that the POS MV is using the last good clock offset to compute GPS times. The POS MV has either not received a PPS or time recovery message or has rejected erroneous GPS time synchronization data. 
This data provides for PPS time recovery of any of the time bases supported by the POS MV where the time refers to the previous 1PPS signal. It allows an external device to acquire GPS or UTC time, or to relate GPS time to POS MV time. 
Table 15: Group 7: PPS Time Recovery and Status 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  7  N/A  
Byte count  2  ushort  36  bytes  
Time/Distance Fields  26  See Table 3  
PPS count  4  ulong  [0, )  N/A  
Time synchronization status  1  byte  0 1 2 3  Not synchronized Synchronizing Fully synchronized Using old offset  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group End  2  char  $#  N/A  

Group 8: Logging Parameters and Status 
This group describes the status of internal data logging through the logging port. This information allows the user to determine the amount of disk space and time used and remaining. 
16 
 
 
Table 16: Group 8: Logging Information 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  8  N/A  
Byte count  2  ushort  4848  N/A  
Time/Distance Fields  26  See Table 3  
Disk Kbytes remaining  4  ulong  [0, )  Kbytes  
Disk Kbytes logged  4  ulong  [0, )  Kbytes  
Disk logging time remaining  4  float  [0, )  Seconds  
Disk Kbytes total  4  ulong  [0, )  Kbytes  
Logging State  1  byte  0 Standby 1 Logging 2 Buffering 255 Invalid  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group End  2  char  $#  N/A  

Group 9: GAMS Solution 
This group contains the GAMS solution and solution status. The following are descriptions of 
some of the group elements. The number of satellites field gives the number of satellites in the GAMS solution. The PDOP is the PDOP of the satellite constellation selected by GAMS. The computed antenna separation is the length of the baseline vector that GAMS computes. The solution status describes the status of the current GAMS solution. The PRN assignment fields give the satellite PRN assigned to each observables processing channel. The cycle slip flag identifies processing channels in which the ambiguity search algorithm has detected cycle slips. 
The GAMS heading is the heading of the antenna baseline vector. The heading RMS error is estimated by GAMS based on the RMS uncertainties of the primary and secondary carrier phase measurements reported by the primary and secondary GPS receivers. 
17 
 
 
Table 17: Group 9: GAMS Solution Status 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  9  N/A  
Byte count  2  ushort  72  bytes  
Time/Distance Fields  26  See Table 3  
Number of satellites  1  ubyte  N/A  N/A  
A priori PDOP  4  float  [0, 999]  N/A  
Computed antenna separation  4  float  [0, )  meters  
Solution Status  1  byte  0 fixed integer 1 fixed integer test install data 2 degraded fixed integer 3 floated ambiguity 4 degraded floated ambiguity 5 solution without install data 6 solution from navigator attitude and install data 7 no solution  
PRN assignment  12  byte  Each byte contains 0-32 where 0 = unassigned PRN 1-40 = PRN assigned to channel  
Cycle slip flag  2  ushort  Bits 0-11: (k-1)th bit set to 1 implies cycle slip in channel k. Example: Bit 3 set to 1 implies cycle slip in channel 4. Bits 12-15: not used.  
GAMS heading  8  double  [0,360)  Degrees  
GAMS heading RMS error  8  double  (0, )  Degrees  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

18 
 
 
Group 10: General Status and FDIR 
This group is used to output general and Fault Detection, Isolation and Reconfiguration (FDIR) status information. The POS Controller decodes and displays the sensor hardware status output in this group. The following is a brief description of group contents. 
General Status A contains bit-encoded status information from the following processes: 
integrated navigation, data logging and generic hardware. General Status B contains bit-encoded status information from the following processes: primary GPS data input, secondary GPS data input, auxiliary GPS data input, GAMS. 
General Status C contains bit-encoded information fromthe following processes: integrated 
navigation, gimbal data input, DMI data input, base GPS messages (RTCM, CMR, RTCA) input. FDIR Level 1, similar to a built-in test, reports problems in communications between the sensors and the PCS. 
FDIR Level 2, the direct reasonableness test, compares the sensor data against reasonable magnitude limits for the POS-instrumented Vessel. 
FDIR Level 3, Reserved. FDIR Level 4, the residual test, monitors the measurement residuals from the Kalman filter and rejects measurements that fall outside a specified 95% confidence level. Consistentmeasurement rejection indicates a potential IMU or aiding sensor failure. 
FDIR Level 5, the indirect reasonableness test, monitors Kalman filter estimates of inertial sensor errors and installation errors. Soft sensor failures appear as slow increases in these errors. If a threshold is exceeded, a sensor failure is flagged. 
Extended Status contains bit-encoded status information from the following processes: primary and aux. GNSS data input (Marinestar modes). 
Table 18: Group 10: General and FDIR status 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  10  N/A  
Byte count  2  ushort  60  Bytes  
Time/Distance Fields  26  See Table 3  
General Status A  4  ulong  Coarse levelling active Coarse levelling failed Quadrant resolved Fine align active Inertial navigator initialised Inertial navigator alignment active  bit 0: set bit 1: set bit 2: set bit 3: set bit 4: set bit 5: set  

19 
 
 
Item  Bytes  Format  Value  Units  
Degraded navigation solution bit 6: set Full navigation solution bit 7: set Initial position valid bit 8: set Reference to Primary GPS Lever arms = 0 bit 9: set Reference to Sensor 1 Lever arms = 0 bit 10: set Reference to Sensor 2 Lever arms = 0 bit 11: set Logging Port file write error bit 12: set Logging Port file open bit 13: set Logging Port logging enabled bit 14: set Logging Port device full bit 15: set RAM configuration differs from NVM bit 16: set NVM write successful bit 17:  set NVM write fail bit 18: set NVM read fail bit 19: set CPU loading exceeds 55% threshold bit 20: set CPU loading exceeds 85% threshold bit 21: set Reserved bits: 22-31  
General Status  4  ulong  User attitude RMS performance bit 0: set  
B  User heading RMS performance bit 1: set  
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
Primary GPS initialization failed bit 14: set  
Primary GPS reset command sent bit 15: set  
Primary GPS configuration file sent bit 16: set  
Primary GPS not configured bit 17: set  

20 
 
 
Item  Bytes  Format  Value  Units  
Primary GPS in C/A mode bit 18: set Primary GPS in Differential mode bit 19: set Primary GPS in float RTK mode bit 20: set Primary GPS in wide lane RTK mode bit 21: set Primary GPS in narrow lane RTK mode bit 22: set Primary GPS observables in use bit 23: set Secondary GPS observables in use bit 24: set Auxiliary GPS navigation solution in use bit 25: set Auxiliary GPS in P-code mode bit 26: set Auxiliary GPS in Differential mode bit 27: set Auxiliary GPS in float RTK mode bit 28: set Auxiliary GPS in wide lane RTK mode bit 29: set Auxiliary GPS in narrow lane RTK mode bit 30: set Primary GPS in P-code mode bit 31: set  
General Status  4  ulong  Gimbal input ON bit 0: set  
C  Gimbal data in use bit 1: set  
DMI data in use bit 2: set  
ZUPD processing enabled bit 3:  set  
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
Received RTCM Type 1 message  bit 18: set  
Received RTCM Type 3 message  bit 19: set  
Received RTCM Type 9 message  bit 20: set  

21 
 
 
Item  Bytes  Format  Value  Units  
Received RTCM Type 18 messages  bit 21: set Received RTCM Type 19 messages  bit 22: set Received CMR Type 0 message  bit 23: set Received CMR Type 1 message bit 24: set Received CMR Type 2 message bit 25: set Received CMR Type 94 message bit 26 set Received RTCA SCAT-1 message  bit 27: set Reserved bit: 28-31  
FDIR Level 1  4  ulong  IMU-POS checksum error bit 0: set  
status  IMU status bit set by IMU bit 1: set  
Successive IMU failures bit 2: set  
IIN configuration mismatch failure bit 3: set  
Primary GPS not in Navigation mode bit 5: set  
Primary GPS not available for alignment bit 6: set  
Primary data gap bit 7: set  
Primary GPS PPS time gap bit 8: set  
Primary GPS time recovery data not received bit 9: set  
Primary GPS observable data gap bit 10: set  
Primary ephemeris data gap bit 11: set  
Primary GPS missing ephemeris bit 13: set  
Secondary GPS data gap bit 20: set  
Secondary GPS observable data gap bit 21: set  
Auxiliary GPS data gap bit 25: set  
GAMS ambiguity resolution failed bit 26: set  
IIN WL ambiguity error bit 30: set  
IIN NL ambiguity error bit 31: set  
Reserved bits: 4, 12  
14-19, 22- 
24, 27-29  
FDIR Level 1 IMU failures   2  ushort  Shows number of FDIR Level 1 Status IMU failures (bits 0 or 1) = Bad IMU Frames  
FDIR Level 2  2  ushort  Inertial speed exceeds max bit 0: set  
status  Primary GPS velocity exceeds max bit 1: set  
Primary GPS position error exceeds max bit 2: set Auxiliary GPS position error exceeds max bit 3: set  

22 
 
 
Item  Bytes  Format  Value  Units  
Reserved bits: 4-15  
FDIR Level 3 status  2  ushort  Reserved bits: 0-15  
FDIR Level 4  2  ushort  Primary GPS position rejected bit 0: set  
status  Primary GPS velocity rejected bit 1: set  
GAMS heading rejected bit 2: set  
Auxiliary GPS data rejected bit 3: set  
Reserved bit 4: set  
Primary GPS observables rejected bit 5: set  
Reserved bits: 6-15  
FDIR Level 5  2  ushort  X accelerometer failure bit 0: set  
status  Y accelerometer failure bit 1: set  
Z accelerometer failure bit 2: set  
X gyro failure bit 3: set  
Y gyro failure bit 4: set  
Z gyro failure bit 5: set  
Excessive GAMS heading offset bit 6: set  
Excessive primary GPS lever arm error bit 7: set  
Excessive auxiliary 1 GPS lever arm error bit 8: set   
Excessive auxiliary 2 GPS lever arm error bit 9: set   
Excessive POS position error RMS bit10:set  
Excessive primary GPS clock drift bit11:set  
Reserved bits: 12-15  

23 
 
 
Item  Bytes  Format  Value  Units  
Extended Status  4  ulong  Primary GPS in Marinestar HP mode Primary GPS in Marinestar XP mode Primary GPS in Marinestar VBS mode Primary GPS in PPP mode Aux. GPS in Marinestar HP mode Aux. GPS in Marinestar XP mode Aux. GPS in Marinestar VBS mode Aux. GPS in PPP mode Primary GPS in Marinestar G2 mode Primary GPS in Marinestar HPXP mode Primary GPS in Marinestar HPG2 mode Reserved  bit 0: set bit 1: set bit 2: set bit 3: set bit 4: set bit 5: set bit 6: set bit 7: set bit 12:set bit 14:set bit 15:set bits: 8-11 13,16-31  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

max = maximum 
Group 11: Secondary GNSS Status 
This group contains status data fromthe secondary GNSS receiver. The group length is variable, depending on the number of secondary GNSS receiver channels that report data. This group assumes that the secondary GNSS receiver supports a large number of channels (>200 but not all active at the same time) and therefore provides 60 channel status fields. Each channel status field has the format given in Table 8. The GNSS navigation message latency field contains the time between the PPS pulse and the start of the GNSS navigation data output. 
Table 19: Group 11: Secondary GNSS status 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  11  N/A  
Byte count  2  ushort  76 + 20 x (number of channels)  Bytes  
Time/Distance Fields  26  See Table 3  

24 
 
 
Item  Bytes  Format  Value  Units  
Navigation solution status  1  byte  See Table 9  N/A  
Number of SV tracked  1  byte  [0, 60]  N/A  
Channel status byte count  2  ushort  [0, 1200]  Bytes  
Channel status  variable  See Table 8  
HDOP  4  float  (0, )  N/A  
VDOP  4  float  (0, )  N/A  
DGPS correction latency  4  float  [0, 99.9]  Seconds  
DGPS reference ID  2  ushort  [0, 1023]  N/A  
GPS/UTC week number  4  ulong  [0, 9999) 0 if not available  Week  
GPS/UTC time offset (GPS time - UTC time)  8  double  ( , 0]  Seconds  
GNSS navigation message latency  4  float  [0, )  Seconds  
Geoidal separation  4  float  ( , )  Meters  
GNSS receiver type  2  ushort  See Table 12  N/A  
GNSS status  4  ulong  GNSS summary status fields which depend on GNSS receiver type.  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 12: Auxiliary 1 GPS Status 
This group contains data from an optional auxiliary 1 external GPS receiver. The group is variable in length because it is dependent upon the number of satellites that the auxiliary 1 GPS receiver is tracking. This group assumes that the auxiliary 1 GPS receiver  supports a large number of channels and therefore provides 60 channel status fields. The centre section of this group grows with increasing number of satellites tracked. 
When using C-NAV/NAVCOM as the auxiliary receiver, the aiding mode is mapped based on the DGPS reference ID, refer to Table 10 for details. 
25 
 
 
Group 13: Auxiliary 2 GPS Status This group contains data from an optional auxiliary 2 external GPS receiver. The group has the same format as Group 12. Table 20 specifies the format for both Groups 12 and 13 

Table 20: Group 12/13: Auxiliary 1/2GPS status 
Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  12 or 13  N/A  
Byte count  2  ushort  72 + 20 x (number of channels)  Bytes  
Time/Distance Fields  26  See Table 3  
Navigation solution status  1  byte  See Table 9 (See Table 10 when using NAVCOM)  N/A  
Number of SV Tracked  1  byte  [0, 60]  N/A  
Channel status byte count  2  ushort  [0, 1200]  Bytes  
Channel status  variable  See Table 8  
HDOP  4  float  (0, )  N/A  
VDOP  4  float  (0, )  N/A  
DGPS correction latency  4  float  (0, )  Seconds  
DGPS reference ID  2  ushort  [0, 1023]  N/A  
GPS/UTC week number  4  ulong  [0, 9999) 0 if not available  Week  
GPS time offset (GPS time - UTC time)  8  double  ( , 0]  Seconds  
GPS navigation message latency  4  float  [0, )  Seconds  
Geoidal separation  4  float  N/A  Meters  
NMEA messages Received  2  ushort  Bit (set) NMEA Message 0 GGA (GPS position) 1 GST (noise statistics) 2 GSV (satellites in view) 3 GSA (DOP & active SVs) 4-15 Reserved  
Aux 1/2 in Use1  1  byte  0 Not in use 1 In Use  N/A  

26 
 
 
Item  Bytes  Format  Value  Units  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group12/13Aux in Use fields will not be set in use simultaneously. 
Group 14: Calibrated Installation Parameters 
This group lists the calibrated installation parameters that the POS MV computes during Navigate mode when the Calibrate function is active. The group includes a Figure of Merit (FOM) for each set of parameters that the user can choose to calibrate. The FOM ranges from 0 to 100 and describes the percentage of a complete calibration that a calibration has achieved. A FOM equal to 0 indicates one of two possibilities: 
. A parameter is not being calibrated because the user did not flag the parameter for calibration in Message 57: Installation calibration control (see Section 0). 
. A parameter is not calibrated during a calibration of the parameter because the Vessel has not executed the required dynamics to effect the calibration. 
Table 21: Group 14: Calibrated installation parameters 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  14  N/A  
Byte count  2  ushort  128  Bytes  
Time/Distance Fields  26  See Table 3  
Calibration status  2  ushort See Table 22  
Reference to Primary GPS X lever arm  4  float  ( , )  Meters  
Reference to Primary GPS Y lever arm  4  float  ( , )  Meters  
Reference to Primary GPS Z lever arm  4  float  ( , )  Meters  
Reference to Primary GPS lever arm calibration FOM  2  ushort  [0, 100]  N/A  
Reference to Auxiliary 1 GPS X lever arm  4  float  ( , )  Meters  
Reference to Auxiliary 1 GPS Y lever arm  4  float  ( , )  Meters  
Reference to Auxiliary 1 GPS Z lever arm  4  float  ( , )  Meters  
Reference to Auxiliary 1 GPS lever arm calibration FOM  2  ushort  [0, 100]  N/A  
Reference to Auxiliary 2 GPS X lever arm  4  float  ( , )  Meters  
Reference to Auxiliary 2 GPS Y lever arm  4  float  ( , )  Meters  
Reference to Auxiliary 2 GPS Z lever arm  4  float  ( , )  Meters  

27 
 
 
Item  Bytes  Format  Value  Units  
Reference to Auxiliary 2 GPS lever arm calibration FOM  2  ushort  [0, 100]  N/A  
Reference to DMI X lever arm  4  float  ( , )  Meters  
Reference to DMI Y lever arm  4  float  ( , )  Meters  
Reference to DMI Z lever arm  4  float  ( , )  Meters  
Reference to DMI lever arm calibration FOM  2  ushort  [0, 100]  N/A  
DMI scale factor  4  float  ( , )  %  
DMI scale factor calibration FOM  2  ushort  [0, 100]  N/A  
Reference to DVS X lever arm  4  float  ( , )  Meters  
Reference to DVS Y lever arm  4  float  ( , )  Meters  
Reference to DVS Z lever arm  4  float  ( , )  meters  
Reference to DVS lever arm calibration FOM  2  ushort  [0, 100]  N/A  
DVS scale factor  4  float  ( , )  %  
DVS scale factor calibration FOM  2  ushort  [0, 100]  N/A  
Primary to Secondary GPS X lever arm  4  float  ( , )  meters  
Primary to Secondary GPS Y lever arm  4  float  ( , )  meters  
Primary to Secondary GPS Z lever arm  4  float  ( , )  meters  
Primary to Secondary GPS lever arm calibration FOM  2  ushort  [0, 100]  N/A  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  
Table 22: IIN Calibration Status 


Bit Set  Status Description  
0  Reference to Primary GPS lever arm calibration is in progress  
1  Reference to Auxiliary 1 GPS lever arm calibration is in progress  
2  Reference to Auxiliary 2 GPS lever arm calibration is in progress  
3  Reference to DMI lever arm calibration is in progress  
4  DMI scale factor calibration is in progress  
5  Reference to DVS lever arm calibration is in progress  
6  Reference to Position Fix lever arm calibration is in progress  
7  Primary to Secondary GNSS Lever lever arm calibration is in progress  

28 
 
 
Bit Set  Status Description  
8  Reference to Primary GPS lever arm calibration is completed  
9  Reference to Auxiliary 1 GPS lever arm calibration is completed  
10  Reference to Auxiliary 2 GPS lever arm calibration is completed  
11  Reference to DMI lever arm calibration is completed  
12  DMI scale factor calibration is completed  
13  Reference to DVS lever arm calibration is completed  
14  Reference to Position Fix lever arm calibration is completed  
15  Primary to Secondary GNSS Lever lever arm calibration is completed  

Group 17: User Time Status This group contains status information about user time synchronization. 
Table 23: Group 17: User Time Status 
Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  17  N/A  
Byte count  2  ushort  40  Bytes  
Time/Distance Fields  26  See Table 3  
Number of Time Synch message rejections  4  ulong  [0, )  N/A  
Number of User Time resynchronizations  4  ulong  [0, )  N/A  
User time valid  1  byte  1 or 0  N/A  
Time Synch message received  1  byte  1 or 0  N/A  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 20: IIN Solution Status 
This group contains the IIN observables processing status and relevant data. The following are 
descriptions of some of the fields. The number of satellites field gives the number of satellites in the IIN solution. The a priori PDOP is the PDOP of the satellite constellation selected by IIN before processing. The baseline length is the computed distance between the primary GPS antenna and thereference GPS 
29 
 
 
antenna. The IIN processing status describes the status of the current IIN solution. The 12 PRN assignment fields give the satellite PRN used in each observables processing channel in the IIN solution. The L1 cycle slip flag field contains a bit array whose bits when set, indicate an L1 cycle slips in the observables processing channels. The L2 cycle slip flag field contains a bit array whose bits when set, indicate L2 cycle slips in observables processing channels.In each bit array, bit (k-1) indicates the cycle slip status of processing channel k. 
Table 24: Group 20: IIN solution status 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  20  N/A  
Byte count  2  ushort  60  Bytes  
Time/Distance Fields  26  See Table 3  
Number of satellites  2  ushort  [0, 12]  N/A  
A priori PDOP  4  float  [0, 999]  N/A  
Baseline length  4  float  [0, )  Meters  
IIN processing status  2  ushort  0 Fixed Narrow Lane RTK 1 Fixed Wide Lane RTK 2 Float RTK 3 Code DGPS 4 RTCM DGPS 5 Autonomous (C/A) 6 GPS navigation solution 7 No solution  
PRN assignment  12  12 byte  Each byte contains 0-40 where 0 = unassigned PRN 1-40 = PRN assigned to channel  
L1 cycle slip flag  2  ushort  Bits 0-11: (k-1)th bit set to 1 implies L1 cycle slip in channel k PRN. Example: Bit 3 set to 1 implies an L1 cycle slip in channel 4. Bits 12-15: not used.  
L2 cycle slip flag  2  ushort  Bits 0-11: (k-1)th bit set to 1 implies L2 cycle slip in channel k PRN. Example: Bit 3 set to 1 implies an L2 cycle slip in channel 4. Bits 12-15: not used.  
Pad  2  byte  0  N/A  

30 
 
 
Item  Bytes  Format  Value  Units  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 21: Base GPS 1 ModemStatus 
The base GPS process may receive differential corrections from a base station via a modem connected to one of the POS MV serial ports. This group contains status information about the modemconnected to the serial port associated with the Base GPS 1 input. 
Group 22: Base GPS 2 ModemStatus 
This group contains status information about the modemconnected to the serial port associated with the Base GPS 2 input. 
Table 25: Group 21/22: Base GPS 1/2 ModemStatus 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  21 or 22  N/A  
Byte count  2  ushort  116  Bytes  
Time/Distance Fields  26  See Table 3  
Modem response  16  char  N/A  N/A  
Connection status  48  char  N/A  N/A  
Number of redials per disconnect  4  ulong  [0, )  N/A  
Maximum number of redials per disconnect  4  ulong  [0, )  N/A  
Number of disconnects  4  ulong  [0, )  N/A  
Data gap length  4  ulong  [0, )  N/A  
Maximum data gap length  4  ulong  [0, )  N/A  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 23: Auxiliary 1 GPS Display Data 
This group contains the auxiliary 1 GPS receiver data stream, containing the NMEA strings requested by the PCS from the receiver plus any other bytes that the receiver inserts into the 
31 
 
 
stream. The length of this group is variable. It is identical to group 10007 except for the time2 restriction and the fact it is intended for display only. 
Group 24: Auxiliary 2 GPS Display Data 
This group contains the auxiliary 2 GPS receiver data stream, containing the NMEA strings requested by the PCS from the receiver plus any other bytes that the receiver inserts into the stream. The length of this group is variable. It is identical to group 10008 except for the time2 restriction and the fact it is intended for display only. 
Table 26: Group 23/24: Auxiliary 1/2GPS raw displaydata 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  10007 or 10008  N/A  
Byte count  2  ushort  variable  Bytes  
Time/Distance Fields  26  See Table 3  
Reserved  6  byte  N/A  N/A  
Variable message byte count  2  ushort  [0, )  Bytes  
Auxiliary GPS raw data  variable  char  N/A  N/A  
Pad  0-3  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 29: GNSS Receiver MarineSTAR Status 
This group contains the GNSS Receiver MarineSTAR status. This Group is output at a frequency of 1 Hz, however the contents update every 30 seconds. This Group is only applied to the primary GNSS receiver. 
Table 27: Group 29: GNSS Receiver MarineSTAR Status 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  29  N/A  
Byte count  2  ushort  63  bytes  
Time/Distance Fields  26  See Table 3  

32 
 
 
Item  Bytes  Format  Value  Units  
MarineSTAR Status  1  byte  0 MarineSTAR off  1-2 Test Mode 3-4 Searching Mode 5 Tracking Initialization 6 Verifying Data Stream 7 Fully Tracking Satellite 4-255 Reserved  N/A  
Satellite ID  1  byte  (0,100) Special ID 100 Custom satellite                          110 Automatically choose satellite  N/A  
Frequency of the satellite  4  ulong  Satellite Frequency  Hz  
Bit Rate of the satellite  2  ushort  Data transfer rate  bit/sec  
HP/XP -MarineSTAR library active flag  1  byte  0 Not Active 1 Active  N/A  
HP/XP -Engine mode used by the library  1  byte  1 HP  2 XP 3 G2 4 HP+G2  5 HP+XP  N/A  
HP/XP Subscription starting date - year  2  ushort  0 for no valid subscription  N/A  
Subscription starting date - month  1  byte  1-12 or 0 for no valid subscription  N/A  
Subscription starting date - day  1  byte  1-31 or 0 for no valid subscription  N/A  

33 
 
 
Item  Bytes  Format  Value  Units  
HP/XP Subscription expiration date - year  2  ushort  0 for no valid subscription  N/A  
Subscription expiration date - month  1  byte  1-12 or 0 for no valid subscription  N/A  
Subscription expiration date - day  1  byte  1-31 or 0 for no valid subscription  N/A  
Subscribed engine mode  1  byte  1 HP  2 XP 3 G2 4 HP+G2  5 HP+XP  N/A  
Reserved  4  byte  Reserved  N/A  
Reserved  4  byte  Reserved  N/A  
HP/XP status -Receiver Operation Mode  1  byte  1 Static 2 kinematic   N/A  
HP/XP status -MarineSTAR Operation Mode  1  byte  0 Kinematic 1 Static 2 MarineSTAR not ready  N/A  
Reserved  1  byte  Reserved  N/A  
Reserved  1  byte  Reserved  N/A  
Reserved  1  byte  Reserved  N/A  
Satellite SNR  1  byte  Satellite carrier-to-noise ratio  dBHz  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

34 
 
 
Group 99: Versions and Statistics 
This group provides feedback of the current statistics and software and hardware version numbers of the POS MV. This group contains operational statistics such as total hours of operation, number of runs, average run length and longest run. 
Table 28: Group 99: Versions and statistics 

Item  Bytes  Format  Value  Units  
Group Start  4  Char  $GRP  N/A  
Group ID  2  Ushort  99  N/A  
Byte Count  2  Ushort  412  Bytes  
Time/Distance Fields  26  See Table 3  Table 3  
System version  120  Char  Product - Model, Version, Serial Number, Hardware version, Software release version - Date, ICD release version, Operating system version, IMU type, Primary GPS type (Table 12), Secondary GPS type (Table 12), DMI type, Gimbal type, ZVI type, IMU housing type ..... Example: MV-320,VER5,S/N5050,HW1.05-10, SW06.00-Jan3/11,ICD04.10, OS6.4.1,IMU7,PGPS16,SGPS16, DMI0,GIM0,ZVI0,IHT101  
Primary GPS version  80  char  Available information is displayed, eg: . Model number . Serial number . Hardware configuration version . Software release version  

35 
 
 
Item  Bytes  Format  Value  Units  
. Release date  
Secondary GPS version  80  Char  Available information is displayed, eg: . Model number . Serial number . Hardware configuration version . Software release version . Release date  
Total hours  4  float  [0, ) 0.1 hour resolution  Hours  
Number of runs  4  ulong  [0, )  N/A  
Average length of run  4  float  [0, ) 0.1 hour resolution  Hours  
Longest run  4  float  [0, ) 0.1 hour resolution  Hours  
Current run  4  float  [0, ) 0.1 hour resolution  Hours  
Options  80  Char  [option mnemonic-expiry time] [,option mnemonic-expiry time] ...  N/A  
Pad  2  short  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group End  2  char  $#  N/A  

Group 102: Sensor 1 Position, Velocity, Attitude,Heave & Dynamics 
This group contains position, velocity, attitude, track, speed and dynamics data for the sensor 1 position. 
The roll, pitch and heading data contained in this group are provided using the Tate-Bryant sequence. That is, pitch is provided with respect to local level, and roll is output with respect to the pitched X-Y plane. See the POS MV User Guide page 2-29 for a fuller explanation. 
Group 103: Sensor 2 Position, Velocity, Attitude,Heave & Dynamics 
This group contains position, velocity, attitude, track, speed and dynamics data for the sensor 2 position. 
36 
 
 
The roll, pitch and heading data contained in this group are provided using the Tate-Bryant sequence. That is, pitch is provided with respect to local level, and roll is output with respect to the pitched X-Y plane. See the POS MV User Guide page 2-29 for a fuller explanation. 
Table 29: Group 102/103:Sensor 1/2 Position, Velocity, Attitude, Heave & Dynamics 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  102 or 103  N/A  
Byte count  2  ushort  128  Bytes  
Time/Distance Fields  26  See Table 3  
Latitude  8  double  (-90, 90]  Deg  
Longitude  8  double  (-180, 180]  Deg  
Altitude  8  double  ( , )  M  
Along track velocity  4  float  ( , )  m/s  
Across track velocity  4  float  ( , )  m/s  
Down velocity  4  float  ( , )  m/s  
Roll  8  double  (-180, 180]  Deg  
Pitch  8  double  (-90, 90]  Deg  
Heading  8  double  [0, 360)  Deg  
Wander angle  8  double  (-180, 180]  Deg  
Heave1  4  float  ( , )  M  
Angular rate about longitudinal axis  4  float  ( , )  deg/s  
Angular rate about transverse axis  4  float  ( , )  deg/s  
Angular rate about down axis  4  float  ( , )  deg/s  
Longitudinal acceleration  4  float  ( , )  m/s2  
Transverse acceleration  4  float  ( , )  m/s2  
Down acceleration  4  float  ( , )  m/s2  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Heaveisoutputin the gravity directionfroma local level frame located at the sensor 1 or 2position. The Heave sign is positive down. 
37 
 
 
Group 104: Sensor 1 Position, Velocity, and Attitude Performance Metrics This group contains sensor 1 position, velocity and attitude performance metrics. All data in this 
group are RMS values. Group 105: Sensor 2 Position, Velocity, and Attitude Performance Metrics This group contains sensor 2 position, velocity and attitude performance metrics. All data in this 
group are RMS values. 

Table 30: Group 104/105:Sensor 1/2 Position, Velocity, and Attitude Performance Metrics 
Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  104 or 105  N/A  
Byte count  2  ushort  68  Bytes  
Time/Distance Fields  26  See Table 3  
N position RMS  4  float  [0, )  M  
E position RMS  4  float  [0, )  M  
D position RMS  4  float  [0, )  M  
Along track velocity RMS error  4  float  [0, )  m/s  
Across track velocity RMS error  4  float  [0, )  m/s  
Down velocity RMS error  4  float  [0, )  m/s  
Roll RMS error  4  float  [0, )  Deg  
Pitch RMS error  4  float  [0, )  Deg  
Heading RMS error  4  float  [0, )  Deg  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

38 
 
 
Group 110: MV General Status & FDIR This group contains MV specific status bits. It is an extension of the Core group 10 information. 
Table 31: Group 110: MVGeneral Status & FDIR 
Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  110  N/A  
Byte count  2  ushort  36  Bytes  
Time/Distance Fields  26  See Table 3  
General Status  2  ushort  User logged in reserved TrueZ Active TrueZ Ready TrueZ In Use Reserved  bit 0: set bit 1 to 9 bit 10: set bit 11: set bit 12: set bit 13 to 15  
TrueZ time remaining  2  ushort  [0, )  seconds  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 111: Heave & True Heave Data 
This group contains data from the True Heave calculations (delayed in time), along with time-matched Heave (Real-time) data. Both the Real-Time and True Heave values are in the gravity direction from a local level frame located at the Sensor 1 position. The Heave sign is positive down. 
Table 32: Group 111: Heave & True Heave Data 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  111  N/A  
Byte count  2  ushort  76  Bytes  
Time/Distance Fields  26  See Table 3  
True Heave  4  float  ( , )  M  
True Heave RMS  4  float  [0, )  M  

39 
 
 
Item  Bytes  Format  Value  Units  
Status  4  ulong  True Heave Valid Real-time Heave Valid reserved  bit 0: set bit 1: set bit 2 to 31  
Heave  4  float  ( , )  M  
Heave RMS  4  float  [0, )  M  
Heave Time 1  8  double  N/A  Sec  
Heave Time 2  8  double  N/A  Sec  
Rejected IMU Data Count  4  ulong  [0, )  N/A  
Out of Range IMU Data Count  4  ulong  [0, )  N/A  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 112: NMEA Strings 
This group contains a copy of the NMEA strings output from the user selected COM port. This group will be available for output at the same rate selected for NMEA output on the COM port. Note that the user must select this group for output on the desired Data in order to receive the data. 
Table 33: Group 112: NMEA Strings 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  112  N/A  
Byte count  2  ushort  variable  Bytes  
Time/Distance Fields  26  See Table 3  
Variable group byte count  2  ushort  [0, )  N/A  
NMEA strings  variable  char  N/A  N/A  
Pad  0-3  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

40 
 
 
Group 113: Heave & True Heave Performance Metrics This group contains quality data from the True Heave calculations. 
Table 34: Group 113: Heave & True Heave Performance Metrics 
Item  Byte s  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  113  N/A  
Byte count  2  ushort  68  Bytes  
Time/Distance Fields  26  See Table 3  
Heave Time 1  8  double  N/A  Sec  
Quality Control 1  8  double  N/A  N/A  
Quality Control 2  8  double  N/A  N/A  
Quality Control 3  8  double  N/A  N/A  
Status  4  ulong  Quality Control 1 Valid Quality Control 2 Valid Quality Control 3 Valid Reserved  bit 0: set bit 1: set bit 2: set bit 3 to 31  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 114: TrueZ & TrueTide Data 
This group contains altitude data from the delayed TrueZ and delayed TrueTide calculations along with the time-matched real-time data. The real-time TrueZ, delayed TrueZ and delayed TrueTide values are in the gravity direction from a local level frame located at the Sensor 1 position. The real-time TrueTide values are in the gravity direction from a local level frame located at the Vessel position. 
41 
 
 
Table 35: Group 114: TrueZ & TrueTide Data 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  114  N/A  
Byte count  2  ushort  76  Bytes  
Time/Distance Fields  26  See Table 3  
Delayed TrueZ  4  float  ( , )  M  
Delayed TrueZ RMS  4  float  [0, )  M  
Delayed TrueTide  4  float  ( , )  M  
Status  4  ulong  Delayed TrueZ Valid bit 0: set Real-time TrueZ Valid bit 1: set Reserved bit 2 to 31  
TrueZ  4  float  ( , )  M  
TrueZ RMS  4  float  [0, )  M  
TrueTide  4  float  ( , )  M  
TrueZ Time 1  8  double  N/A  Sec  
TrueZ Time 2  8  double  N/A  Sec  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  


3.3.2 Raw Data Groups 
Group 10001: Primary GPS Data Stream 
This group contains the primary GPS receiver data as output by the receiver. The length of this group is variable. The GPS data streamis packaged into the group as it is received, irrespective of GPS message boundaries. The messages contained in this group depends on the primary GPS receiver that the POS MV uses. If a data extraction process concatenates the data components from these groups into a single file, then the resulting file will be the same as a file of data recorded directly fromthe primary GPS receiver. 
Table 36: Group 10001: Primary GPS data stream 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  10001  N/A  

42 
 
 
Item  Bytes  Format  Value  Units  
Byte count  2  ushort  variable  Bytes  
Time/Distance Fields  26  See Table 3  
GPS receiver type  2  ushort  See Table 12  N/A  
Reserved  4  long  N/A  N/A  
Variable message byte count  2  ushort  [0, )  Bytes  
GPS Receiver raw data  variable  char  N/A  N/A  
Pad  0-3  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 10002: Raw IMU Data 
This group contains the IMU data as output by the IMU directly. The length of this group is 
variable. The IMU header field contains 6 characters of which the first 4 are "$IMU" and the last two are the IMU type number in ASCII format (example: "$IMU01" identifies IMU type 1). The Data checksumis a 16-bit sum of the IMU data. The POS MV provides this checksumin addition to the possible IMU-generated checksums in the IMU data field. U.S. and Canadian export control laws prevent the publication of the IMU data field formats for thedifferent IMU's that the POS MV supports. 
Table 37: Group 10002: Raw IMU data 

Item  Bytes  Forma t  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  10002  N/A  
Byte count  2  ushort  Variable  Bytes  
Time/Distance Fields  26  See Table 3  
IMU header  6  char  $IMUnn where nn identifies the IMU type.  
Variable message byte count  2  ushort  [0, )  Bytes  
IMU raw data  variable  byte  N/A  N/A  
Data Checksum  2  short  N/A  N/A  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

43 
 
 
Group 10003: Raw PPS This group contains the raw PPS data that the POS MV generates. The time of the PPS is given in the Time/Distance fields. 
Table 38: Group 10003: Raw PPS 
Item  Bytes  Format  Value  Units  
Group start  4  Char  $GRP  N/A  
Group ID  2  Ushort  10003  N/A  
Byte count  2  Ushort  36  Bytes  
Time/Distance Fields  26  See Table 3  
PPS pulse count  4  Ulong  [0, )  N/A  
Pad  2  Byte  0  N/A  
Checksum  2  Ushort  N/A  N/A  
Group end  2  Char  $#  N/A  

Group 10007: Auxiliary 1 GPS Data Stream 
This group contains the auxiliary 1 GPS receiver data stream, containing the NMEA strings requested by the PCS from the receiver plus any other bytes that the receiver inserts into the stream. The length of this group is variable. If a data extraction process concatenates the data components from these groups into a single file, then the resulting file will be the same as an ASCII file of NMEA strings recorded directly fromthe auxiliary 1 GPS receiver. 
Group 10008: Auxiliary 2 GPS Data Stream 
This group contains the auxiliary 2 GPS receiver data stream, containing the NMEA strings requested by the PCS from the receiver plus any other bytes that the receiver inserts into the stream. The length of this group is variable. If a data extraction process concatenates the data components from these groups into a single file, then the resulting file will be the same as an ASCII file of NMEA strings recorded directly fromthe auxiliary 2 GPS receiver. 
Table 39: Group 10007/10008: Auxiliary 1/2 GPS data streams 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  10007 or 10008  N/A  
Byte count  2  ushort  variable  Bytes  
Time/Distance Fields  26  See Table 3  
reserved  2  byte  N/A  N/A  

44 
 
 
Item  Bytes  Format  Value  Units  
reserved  4  long  N/A  N/A  
Variable message byte count  2  ushort  [0, )  Bytes  
Auxiliary GPS raw data  variable  char  N/A  N/A  
Pad  0-3  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

Group 10009: Secondary GPS Data Stream 
This group contains the secondary GPS receiver data as output by the receiver. The length of this group is variable. The GPS data streamis packaged into the group as it is received, irrespective of GPS message boundaries. The messages contained in this group depends on the secondary GPS receiver that the POS MV uses. If a data extraction process concatenates the data components from these groups into a single file, then the resulting file will be the same as a file of data recorded directly fromthe secondary GPS receiver. 
Table 40: Group 10009: Secondary GPS data stream 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  10009  N/A  
Byte count  2  ushort  Variable  Bytes  
Time/Distance Fields  26  See Table 3  
GPS receiver type  2  ushort  See Table 12  N/A  
Reserved  4  byte  N/A  N/A  
Variable message byte count  2  ushort  [0, )  Bytes  
GPS Receiver Message  variable  char  N/A  N/A  
Pad  0-3  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

45 
 
 
Group 10011: Base GPS 1 Data Stream 
This group contains the message data streamthe POS MV receivesas differential corrections. The length of this group is variable and dependent on the messages received by the PCS. If a data extraction process concatenates the data components from this group into a single file, then the resultingfile will be the same as a file of data captured from the serial data streamconnected to a differential corrections port. 
Group 10012: Base GPS 2 Data Stream 
This group contains the message data streamthe POS MV receivesas differential corrections. The length of this group is variable and dependent on the messages received by the PCS. If a data extraction process concatenates the data components from this group into a single file, then the resultingfile will be the same as a file of data captured from the serial data streamconnected to a differential corrections port. 
Table 41: Group 10011/10012: Base GPS 1/2 data stream 

Item  Bytes  Format  Value  Units  
Group start  4  char  $GRP  N/A  
Group ID  2  ushort  10011 or 10012  N/A  
Byte count  2  ushort  variable  Bytes  
Time/Distance Fields  26  See Table 3  
reserved  6  byte  N/A  N/A  
Variable message byte count  2  ushort  [0, )  Bytes  
Base GPS raw data  variable  byte  N/A  N/A  
Pad  0-3  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Group end  2  char  $#  N/A  

46 
 
 



4 Message Input and Output 
4.1 Introduction 
The POS MV uses the Control Port to receive control messages from the POS Controller, (a user's custom software application or MV POSView), and to acknowledge successful receipt of the messages. The Control Port is bi-directional and uses the TCP/IP protocol to communicate with the control and display software. 
Each message sent to POS MV causes an action to be initiated. When POS MV receives and validates a message, it replies to the POS Controller by sending an 'Acknowledge' message, Message ID 0, on the Control Port over which it received the message. The Acknowledge message protocol is defined below. The purpose of the Acknowledge message is to informthe POS Controller that the POS MV has received a message and has either accepted or rejected it. In addition, POS MV also outputs a message echo on each of the Display and Data ports to indicate the current system state, regardless of whether the action was successful or not.  

4.2 Message Output Data Rates 
The POS MV periodically generates copies (echos) of received control message or internally generated messages at maximum frequencies described in Table 42. This output allows a POS Controller to monitor the current state of the configuration of the POS MV. The content of the output messages reflects the current state of thePOS MV. Thus, if the state of the system changes, as part of the normal operations, it is reflected in the next set of echo messages from the POS MV. 
4.2.1 Message Numbering Convention 
All POS products use the following message numbering convention. POS MV outputs the message categories shown. Reserved message numbers are assigned to other products or previous versions of POS products. In particular, POS MV V3 core messages occupy the namespace range 1-19. 
0 Core - Acknowledge message 1 - 19 Core - Reserved 20 - 49 Core - Installation parameter set-up messages 50 - 79 Core - Processing control messages 80 - 89 Core - Reserved 90 - 99 Core - Program control override messages 100 - 199 POS MV specific messages 200 - 19999 Reserved 20000 - 20099 Core - Diagnostic messages 20100 - 20199 POS MV specific diagnostic messages 20200 - 29999 Reserved 
47 
 
 
The Acknowledge message is the message that POS MV sends as a reply to a message fromthe 
POS Controller. It is described in detail in Section 0 of this document. Installation parameter set-up messages comprise all messages that the user sends via the POS Controller to implement a particular installation of the POS MV. The POS Controller would not normally send these messages once the installation is completed. Messages 20-29 are signal processing parameter set-up messages. These specify sensor installation parameters and user accuracies. Messages 30-49 are hardware control messages. These specify communication control parameters and real-time message selections. 
Processing control messages comprise all messages that the user requires to control and monitor POS MV during a navigation session. These include navigation mode control, data acquisition control and possibly initialization of navigation quantities if no GPS signal is available. 
Program control override messages permits the user to directly control functions that POS MV normally performs automatically. The user would send a programcontrol override message only under special circumstances. For example, the user may believe that the primary or secondary GPS receiver has lost its configuration and chooses to manually command the POS MV to re-configure the receiver. This message category also includes control messages that alter the normal operation or output of POS MV for diagnosis purposes. The actions induced by these messages are not part of the normal POS MV operation and should be interpreted only by qualified Applanix service personnel. 
Table 42: Control messages output data rates 

Message  Contents  Display Port (Hz)  Real-Time Data Port (Hz)  Logging Data Port (Hz)  
Stby  Nav  Stby  Nav  Stby  Nav  
0  Acknowledge  - - - - - - 
Installation Parameter Set-up Messages  
20  General installation parameters1  1.0  1.0  0.1  0.1  0.1  0.1  
21  GAMS installation parameters1  1.0  1.0  0.1  0.1  0.1  0.1  
22  Reserved  
23  Reserved  
24  User accuracy specifications1  1.0  1.0  0.1  0.1  0.1  0.1  
25  Reserved  
30  Primary GPS set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
31  Secondary GPS set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
32  Set POS IP address  1.0  1.0  0.1  0.1  0.1  0.1  
33  Reserved  - - - - - - 
34  COM port set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
35  See message 135  
36  See message 136  
37  Base GPS 1 Set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
38  Base GPS 2 Set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
39  Aux GNSS 1/2 protocol set-up1  1.0  1.0  0.1  0.1  0.1  0.1  

48 
 
 
Message  Contents  Display Port (Hz)  Real-Time Data Port (Hz)  Logging Data Port (Hz)  
Stby  Nav  Stby  Nav  Stby  Nav  
40  Reserved  - - - - - - 
41  Primary GPS Receiver Integrated DGPS Source Control  1.0  1.0  0.1  0.1  0.1  0.1  
Processing Control Messages  
50  Navigation mode control  1.0  1.0  1.0  0.1  0.1  0.1  
51  Display Port control1  1.0  1.0  1.0  0.1  0.1  0.1  
52  Real-Time Data Port control1  1.0  1.0  1.0  0.1  0.1  0.1  
53  Logging Port Control  1.0  1.0  1.0  0.1  0.1  0.1  
54  Save/restore parameters command  - - - - - - 
55  Time synchronization control  1.0  1.0  1.0  0.1  0.1  0.1  
56  General data  1.0  1.0  1.0  0.1  0.1  0.1  
57  Installation calibration control  - - - - - - 
58  GAMS calibration control  - - - - - - 
60  Reserved  - - - - - - 
61  Logging Data Port control1  1.0  1.0  1.0  0.1  0.1  0.1  
Program Control Override Messages  
90  Program control  - - - - - - 
91  GPS control  - - - - - - 
92  Reserved  - - - - - - 
93  Reserved  - - - - - - 
POS MV Specific Messages  
106  Heave filter set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
111  Password control  - - - - - - 
120  Sensor parameter set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
121  Vessel Installation parameters1  1.0  1.0  0.1  0.1  0.1  0.1  
135  NMEA output set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
136  Binary output set-up1  1.0  1.0  0.1  0.1  0.1  0.1  
POS MV Specific Diagnostic Control Messages  
20102  Binary output diagnostics set-up  1.0  1.0  0.1  0.1  0.1  0.1  

1 Message is saved in NVM 

4.2.2 Compatibility with Previous POS Products 
The compatibility of POS MV V5 messages with POS MV V4 products is given as follows: 
. The POS MV V5 message format and content is the same as that of POS MV V4 products. 
. The POS MV V5 Message 34 has additional enumerations to allow control of the RS232/422 transciever and GNSS to COM port connection on Stand-Alone (SA) chassis. 
49 
 
 


4.3 Message Format 
4.3.1 Introduction 
All control messages have the format described in Table 43. The messages consist of a header, message body and footer. The next section describes the specific message formats. 
Table 43: Message format 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  Message dependent  N/A  
Byte count  2  ushort  Message dependent  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Message body  Message dependent format and content.  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

The header consists of the following components: 
. an ASCII string ($MSG) 
. unique message identifier 
. byte count 
. transaction number The byte count is a short unsigned integer that includes the number of bytes in all fields in the 
message except the Message start ASCII delimiter, the Message ID and the byte count. Therefore, the byte count is always 8 bytes less than the length of the complete message. The transaction number is a number that is attached to the input message by the client. POS MV 
returns this number to the user in the Acknowledge message (ID 0). This mechanism permits the client to know which message the POS MV is responding to; the number must be between 0 and 65532 when sent to POS. The transaction numbers 65533 to 65535 are used by POS when outputting the echo copy of the messages. 
The message body falls between the header and footer. While many messages have a message body, it is not a requirement of the protocol. Message without bodies may in themselves act as events, or messages may use the body to command a particular state. 
Messages end with a footer that contains a pad, a checksumand an ASCII delimiter ($#). The pad is used to make each message length a multiple of four bytes. The checksum is calculated so that short (16 bit) integer addition of sequential groups of two bytes results in a net sumof zero. 
50 
 
 
Parameters flagged as default are the factory settings. 
The byte, short, ushort, long, ulong, float and double formats are defined in Appendix A: Data Format Description. The ranges of valid values for message fields that contain numbers are specified in the same way 
as for numerical group fields. Message fields that contain numerical values may contain invalid numbers. Invalid byte, short, ushort, long, ulong, float and double values are defined in Table 85 (Appendix A: Data Format Description). POS MV ignores invalid values that it receives in fields containing numerical values. This does not apply to fields containing bit settings. 


4.4 Messages Tables 
4.4.1 General Messages 
The following tables list the format that POS MV expects for each message input and provides for each message output. 
Message 0: Acknowledge 
POS MV responds to a user control message with the Acknowledge message in three possible ways described below: 
1. 
The control message fromthe POS Controller triggers achange ofstate within the POS MV. Some changes of state such as navigation mode transitions may require several seconds to complete. POS MV sends Message 0: Acknowledge indicating that the transition is in progress but not necessarily complete. For example, POSMV replies to a message commanding the POS MV to transition to Navigate mode as soon as the mode transition begins. 

2. 
The control message from the POS Controller contains new POS MVinstallation or set-up parameters that replace the parameters currently used by the POS MV. The Acknowledge message then indicates whether the POS MV has received and begun to use the new parameters. POS MV responds with Message 0: Acknowledge only when it has begun to use the new parameters. 

3. 
The control message from the POS Controller starts the transmission of one or more groups of data. The Acknowledge message indicates the successful completion of the requested action. The POS MV subsequently transmits the requested groups on the Display and/or Data ports. If the data for one or more of the requested groups are not current at the time of request, the P POS MV outputs the group(s) with stale fields set to invalid values as described in Table 85. Message 0: Acknowledge indicates if the data for a requested group is available (not yet implemented). 


The New Parameters Status field indicates if the message being acknowledged has changed the parameters. This allows a POS Controller to prompt the user to direct the POS MV to save the 
51 
 
 
parameters to non-volatile memory if the user has not already done so before commanding a 
Standby mode transition or systemshutdown. POS MV sets the Parameter Name to the name of a parameter that it has rejected or to a null string if it did not reject any parameters. 
Table 44: Message 0: Acknowledge 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  0  N/A  
Byte count  2  ushort  44  N/A  
Transaction number  2  ushort  Transaction number sent by client.  N/A  
ID of received message  2  ushort  Any valid message number.  N/A  
Response code  2  ushort  See Table 45  N/A  
New parameters status  1  byte  Value Message 0 No change in parameters 1 Some parameters changed 2-255 Reserved  N/A  
Parameter name  32  char  Name of rejected parameter on parameter error only  N/A  
Pad  1  bytes  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Table 45: Message response codes 
Field Value  Field Name  Description  
0  Not applicable  The message is not applicable to the POS MV.  
1  Message accepted  POS MV has properly accepted the message from the POS Controller.  
2  Message accepted -too long  POS MV has accepted the messaged from the POS Controller. This is a warning that the POS MV expected a shorter message than the one received. This could be caused if the POS MV and the POS Controller have different ICD versions.  

52 
 
 
Field Value  Field Name  Description  
3  Message accepted -too short  POS MV has accepted the messaged from the POS Controller. This is a warning that the POS MV expected a longer message than the one received. This could be caused if the POS MV and the POS Controller have different ICD versions.  
4  Message parameter error  The message contains one or more parameter errors.  
5  Not applicable in current state  POS MV cannot process the message or cannot output data requested in its current state.  
6  Data not available  The requested data is not available from POS MV.  
7  Message start error  The message does not have the proper header "$MSG".  
8  Message end error  The message does not have the proper footer "$#".  
9  Byte count error  The byte count of the message is too large for POS MV's internal buffer.  
10  Checksum error  The message checksum validation failed.  
11  User not logged in  Password protection feature is in effect, and user must enter password before sending the command. This should only occur if an incompatible Controller or Controller version is being used.  
12  Password incorrect  User was prompted for password and entered incorrect password.  
13-65535  Reserved  Reserved  


4.4.2 Installation Parameter Set-up Messages 
Message 20: General Installation and Processing Parameters 
This message contains general installation parameters that POS MV requires to correctly process sensor data and output the computed navigation data. The POS MV accepts this message at any time. The parameters contained in this message become part of the processing parameters (referred to as "settings") that POS MV saves to NVM. 
The following are brief descriptions of the parameters that this message contains. 
Time Tag Selection 
The Time Tag Type field selects the time tag types used for Time 1, Time 2 and Distance fields in the Time/Distance fields in each group (see Table 3). The user can select POS, GPS or UTC time for Time 1 and POS, GPS, UTC or User timefor Time 2. 
53 
 
 
Selection of GPS time directs POS MV to set the selected Time 1 or Time 2 field in all groups to the GPS seconds of the current week. The GPS week number can be obtained fromGroup 3: Primary GNSS status. 
Selection of UTC time directs POS MV to set the selected Time 1 or Time 2 field in all groups to the UTC seconds of the current week. UTC seconds of the week will lag GPS seconds of the week by the accumulated leap seconds since the startup of GPS at which time the two times were synchronized. 
AutoStart Selection 
The Select/Deselect Autostart field directs POS MV to enable or disable the AutoStart function. When AutoStart is enabled POS MV enters Navigate mode immediately on power-up using the parameters stored in its NVM. When Autostart is disabled, POS MV enters Standby mode on power-up. The user must explicitly command a transition to Navigate mode. 
Lever Arms and Mounting Angles 
This message contains a series of fields that contain lever arm components and mounting angles. These define the positions and orientations of the IMU and aiding sensors (GPS antennas) with respect to user-defined reference and Vessel coordinate frames. These coordinate frames and the installation data contained in this message are defined for an IMU that is rigidly mounted to the Vessel. 
The Vessel frame is a right-handed coordinate frame that is fixed to the Vessel whose navigation solution the POS MV computes. The X-Y-Z axes are directed along the forward, right and down directions of the Vessel. These are the forward along beam, starboard and vertical directions. 
The reference frame is a user-defined coordinate frame that is co-aligned with the Vessel frame, but which may be at a location that allows easier measurement oflever arms. It is alsothe coordinate frame in which the relative positions and orientations of the IMU and aiding sensors are measured. Its origin does not necessarily coincide with the Vessel frame origin, however it is aligned withthe Vessel frame. 
The IMU frame is a right-handed coordinate frame whose X-Y-Z axes coincide with the inertial sensor input axes. The IMU delivers inertial data resolved in the IMU frame to the PCS. The position and orientation of the IMU frame is fixed with respect to the Vessel frame when the user mounts the IMU. Practical considerations may limit the choices in IMU location, in which case the actual position and orientation of the IMU frame may differ froma desired position and orientation. 
The interpretations of the lever arm and orientation fields are as follows: Reference to IMU lever arm components 
These are the X-Y-Z distances from the user-defined reference frame origin to the IMU inertial sensor assembly origin, resolved in the reference frame. 
Note: When MV POSView is used to send this message to the POS MV, the lever arm measurement entered in MV POSView should be to the target painted on the top of the IMU enclosure. MV POSView automatically adds the correct IMU enclosure to the IMU sensing centre offsets (including mounting angles) when constructing the message. The echo message output by POS MV on the Display and Data ports contain the lever arm to the sensing centre 
54 
 
 
parameters. Prior to displaying the lever arm value, MV POSView applies the inverse offset to the Reference to IMU lever arm. If a user wishes to write a POS Controller application, the appropriate offsets can be supplied upon request. 
Reference to Primary GPS lever arm components 
These are the X-Y-Z distances measured from the user-defined reference frame origin to the phase centre of the primary GPS antenna, resolved in the reference frame. 
Reference to Auxiliary 1 GPS lever arm components 
These are the X-Y-Z distances measured from the user-defined reference frame origin to the phase centre of the auxiliary 1 GPS antenna, resolved in the reference frame. POS MV uses these lever arm components whenever it processes data from an optional auxiliary 1 GPS receiver. If POS MV does not receive the auxiliary 1 GPS data, then it does not use these parameters. 
Reference to Auxiliary 2 GPS lever arm components 
These are the X-Y-Z distances measured from the user-defined reference frame origin to the phase centre of the auxiliary 2 GPS antenna, resolved in the reference frame. POS MV uses these lever arm components whenever it processes data from an optional auxiliary 2 GPS receiver. If POS MV does not receive the auxiliary 2 GPS data, then it does not use these parameters. 
IMU with respect to Reference frame mounting angles 
These are the angular offsets ( .x, .y, .z ) of the IMU frame with respect to the reference frame when the IMU is rigidly mounted to the Vessel. The angles define the Euler sequence of rotations that bring the reference frame into alignment with the IMU frame. The angles follow the Tate-Bryant sequence of rotation, given as follows: 
right-hand screw rotation of .z about the z axis 
right-hand screw rotation of .y about the once rotated y axis 
right-hand screw rotation of .x about the twice rotated x axis 
The angles .x, .y and .z may be thought of as the roll, pitch and yaw of the IMU body frame with respect to the user IMU frame. 
Reference Frame with respect to Vessel Frame mounting angles 
Although these X-Y-Z fields are part of Core message 20 they are not used in the POS MV product. POS MV assumes the reference frame and the Vessel frame are co-aligned. MV POSView does not provide data entry fields for these values. 
Multipath Setting 
The Multipath Environment field directs POS MV to set its processing parameters for one of three multipath levels impinging on primary, secondary and auxiliary GPS antennas. These are LOW, MEDIUM and HIGH multipath. This field allows the user to select the multipath environment which best describes the present multipath conditions. POS uses this information to scale the RMS errors on the position and velocity outputs reported to the user to ensure that the 
55 
 
 
reported errors are reasonable. If the user selects LOW, POS MV assumes virtually no multipath error in the primary, secondary and auxiliary GPS data. If the user selects MEDIUM or HIGH, POS MV assumes, respectively, moderate or severe multipath errors and accounts for these in its GPS processing algorithms. 
Table 46: Message 20: General Installation and Processing Parameters 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  20  N/A  
Byte count  2  ushort  84  N/A  
Transaction Number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Time types  1  byte  Value (bits 0-3) Time type 1 0 POS time 1 GPS time 2 UTC time (default) 3-16 Reserved Value (bits 4-7) Time type 2 0 POS time (default) 1 GPS time 2 UTC time 3 User time 4-16 Reserved  
Distance type  1  byte  Value State 0 N/A 1 POS distance (default) 2 DMI distance 3-255 Reserved  
Select/deselect AutoStart  1  byte  Value State 0 AutoStart disabled (default) 1 AutoStart enabled 2-255 Reserved  
Reference to IMU X lever arm  4  float  ( , ) default = 0  meters  
Reference to IMU  4  float  ( , ) default = 0  meters  

56 
 
 
Item  Bytes  Format  Value  Units  
Y lever arm  
Reference to IMU Z lever arm  4  float  ( , ) default = 0  meters  
Reference to Primary GPS X lever arm  4  float  ( , ) default = 0  meters  
Reference to Primary GPS Y lever arm  4  float  ( , ) default = 0  meters  
Reference to Primary GPS Z lever arm  4  float  ( , ) default = 0  meters  
Reference to Auxiliary 1 GPS X lever arm  4  float  ( , ) default = 0  meters  
Reference to Auxiliary 1 GPS Y lever arm  4  float  ( , ) default = 0  meters  
Reference to Auxiliary 1 GPS Z lever arm  4  float  ( , ) default = 0  meters  
Reference to Auxiliary 2 GPS X lever arm  4  float  ( , ) default = 0  meters  
Reference to Auxiliary 2 GPS Y lever arm  4  float  ( , ) default = 0  meters  
Reference to Auxiliary 2 GPS Z lever arm  4  float  ( , ) default = 0  meters  
X IMU wrt Reference frame mounting angle  4  float  [-180, +180] default = 0  degrees  
Y IMU wrt Reference frame mounting angle  4  float  [-180, +180] default = 0  degrees  
Z IMU wrt Reference frame mounting angle  4  float  [-180, +180] default = 0  degrees  
X Reference frame wrt Vessel frame mounting angle  4  float  [-180, +180] default = 0  degrees  
Y Reference frame wrt Vessel frame mounting angle  4  float  [-180, +180] default = 0  degrees  
Z Reference frame wrt Vessel frame mounting angle  4  float  [-180, +180] default = 0  degrees  
Multipath environment  1  byte  Value Multipath  

57 
 
 
Item  Bytes  Format  Value  Units  
0 1-255  Low (default) Reserved  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 21: GAMS Installation Parameters 
This message contains the GAMS installation parameters. POS MV accepts this message at any time. The parameters contained in this message become part of the processing parameters (referred to as "settings") that POS MV saves to NVM. 
The following are brief descriptions of the parameters that this message contains. 
The Primary-Secondary Antenna Separation field is deprecated. Any values in the field will not be used by the system. Leaving it at the default value is acceptable. 
The Baseline Vector X-Y-Z Component fields contain the components of the primary-secondary antenna baseline vector resolved in the IMU frame. The user is usually not able to measure these and hence may insert the components that the POS MV computed in a previous GAMS calibration. POS MV computes the vector length and flags any length smaller than 10 centimetres as invalid. It replaces a user-entered primary-secondary antenna separation with a valid length. The default is a zero vector. Only an experienced user should use this message, as a wrong value will disable the GAMS algorithmand a re-calibration will be necessary. 
The Maximum Heading Error RMS For Calibration field contains the maximum navigation solution heading error RMS that the POS MV uses for executing a GAMS baseline calibration. If the current heading error RMS exceeds the specified maximum when the user commands a GAMS calibration, then POS MV defers the calibration until the heading error RMS drops to below the specified maximum. 
The Heading Correction field contains a user-entered azimuth error in the primary-secondary antenna baseline vector. POS MV computes a new baseline vector that has been rotated so that the POS MV computed heading changes by the specified heading correction when GAMS is on-line. 
The Baseline Vector Standard Deviation field contains the uncertainty for which the baseline 
58 
 
 
vector components are measured. The choices of the values from the controller are 0.01 (certain), 0.05, 0.1, 0.25, or 10.0, if the vector components are completely unknown. Although strictly speaking, user may enter any value if send this message throughtheir own method. Any standard deviation values less than 0.01 will disable calibration. The default value is 10.0. 
Note: POS MV echos this message with the updated Baseline Vector andthe HeadingCorrection field cleared. The user should not enter another Heading Correction without also restoring the original calibrated Baseline Vector. 
Table 47: Message 21: GAMS installation parameters 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  21  N/A  
Byte count  2  ushort  36  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Primary-secondary antenna separation (deprecated)  4  float  [0, ) default = 0  Meters  
Baseline vector X component  4  float  ( , ) default = 0  Meters  
Baseline vector Y component  4  float  ( , ) default = 0  meters  
Baseline vector Z component  4  float  ( , ) default = 0  meters  
Maximum heading error RMS for calibration  4  float  [0, ) default = 3  degrees  
Heading correction  4  float  ( , ) default = 0  degrees  
Baseline vector standard deviation  4  float  (0, ) default = 10  meters  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

59 
 
 
Message 24: User Accuracy Specifications 
This message sets the user accuracy specifications for full navigation status. POS MV declares Full Navigation status on the front panel LED's and through the POS Controller when the position, velocity, attitude and heading error RMS have all dropped to or below these accuracy specifications. The default heading accuracy is 0.08 degrees for the SurfMaster, SurfMaster One, and Trimble MPS500 while it is 0.05 for all other products. 
POS MV accepts this message at anytime. The parameters contained in this message become part of the processing parameters (referred to as "settings") that POS MV saves to NVM. 
Table 48: Message 24: User accuracy specifications 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  24  N/A  
Byte count  2  ushort  24  N/A  
Transaction number  2  ushort  Input: Transaction number Output: 65533 to 65535  N/A  
User attitude accuracy  4  float  (0, )  default = 0.05  degrees  
User heading accuracy  4  float  (0, )  default = 0.08 / 0.05 (see above)  degrees  
User position accuracy  4  float  (0, )  default = 2  meters  
User velocity accuracy  4  float  (0, )  default = 0.5  meters/second  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 30: Primary GPS Setup 
This message contains the setup parameters for the primary GPS receiver. POS MV accepts this message at anytime. The parameters contained in this message become part of the processing parameters (referred to as "settings") that POS MV saves to NVM. 
The Select/Deselect GPS AutoConfig field directs POS MV to reconfigure the primary GPS receiver if the POS MV detects that the primary GPS configuration is incorrect. If the user chooses to disable auto-configuration, then the user must configure the primary GPS receiver manually. 
The Primary GPS COM1 Output Message Rate field specifies the rate at which the primary GPS receiver outputs its raw observables messages over its COM1 port to the POS MV. POS MV only process 1 Hz observables, however, selecting a higher output rate will allow more data to be logged which may be useful for a post processed solution. 
60 
 
 
The Primary GPS COM2 Port Control directs the primary GPS receiver to accept RTCM differential corrections, RTCA Type 18/19 corrections, CMR corrections or commands over its COM2 port. This message assumes that the user can access the GPS receiver COM2 port directly and connect either a source of RTCM differential corrections or a PC-compatible computer running control software that is compatible with the primary GPS receiver. The POS MV  hardware connects the GPS 1 port on the PCS back panel directly to the Primary GPS COM2 port. The Primary GPS COM2 port must not be confused with the COM2 port on the PCS. POS MV processes raw GPS observables and corrections so there is no need to feed corrections directly to the Primary GPS receiver. The GPS 1 port on thePCS read panel is primarily to allow GPS receiver firmware upgrades. 
Note: GPS Autoconfig will be turned off upon receipt of an Accept Command message and will 
be turned on again when either an Accept RTCM or a GPS reconfigure message is issued. The Primary GPS COM2 Communication Protocol fields are elaborated in Table 50. They specify the COM2 RS-232 communication protocol settings. 
Table 49: Message 30: Primary GPS Setup 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  30  N/A  
Byte count  2  ushort  16  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Select/deselect GPS AutoConfig  1  byte  Value State 0 AutoConfig disabled 1 AutoConfig enabled (default) 2-255 Reserved  
Primary GPS COM1 port message output rate (not supported)  1  byte  Value Rate (Hz) 1 1 (default) 2 2 3 3 4 4 5 5 10 10 11-255 Reserved  

61 
 
 
Item  Bytes  Format  Value  Units  
Primary GPS COM2 port control  1  byte  Value Operation 0 Accept RTCM (default) 1 Accept commands 2 Accept RTCA 3-255 Reserved  
Primary GPS COM2 communication protocol  4  See Table 50 Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  
Antenna frequency (only applicable for Trimble Force5 GPS receivers)  1  byte  Value Operation 0 Accept L1 only 1 Accept L1/L2 2 Accept L2 only  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  
Table 50: RS-232/422 communication protocol settings 


Item  Bytes  Format  Value  
RS-232/422 port baud rate  1  byte  Value 0 1 2 3 4 5 6 7 8-255  Rate 2400 4800 9600 19200 38400 57600 76800 115200 Reserved  
Parity  1  byte  Value 0 1 2 3-255  Parity no parity even parity odd parity Reserved  

62 
 
 
Item  Bytes  Format  Value  
Data/Stop Bits  1  byte  Value  Data/Stop Bits  
0  7 data, 1 stop  
1  7 data, 2 stop  
2  8 data, 1 stop  
3  8 data, 2 stop  
4-255  Reserved  

Flow Control1  1  byte  Value 0  Flow Control none  
1  hardware  
2 3-255  XON/XOFF Reserved  

Notes: 1 RS422 doesn't support flow control, hence this is used as an indication that this port is switched into RS422 mode. This selection only applies to POS MV V5 stand alone chassis COM 3 and COM 4. 
Message 31: Secondary GPS Setup 
This message contains the set-up parameters for the secondary GPS receiver. POS MV accepts this message at anytime. The parameters contained in this message become part of the processing parameters (referred to as "settings") that POS MV saves to NVM. 
The Select/Deselect GPS AutoConfig field directs POS MV to reconfigure the secondary GPS receiver if the POS MV detects that the secondary GPS configuration is incorrect. If the user chooses to disable auto-configuration, then the user must configure the secondary GPS receiver manually. 
The Secondary GPS COM1 Output Message Rate field specifies the rate at which the secondary 
GPS receiver outputs messages over its COM1 port to POS MV. The Secondary GPS COM2 Port Control directs the secondary GPS receiver to accept RTCM differential corrections, RTCA Type 18 corrections or commands over its COM2 port. This message assumes that the user can access the GPS receiver COM2 port directly and connect either a source of RTCM differential correctionsor a PC-compatible computer running control software that is compatible with the secondary GPS receiver. The currentPOS MV hardware connects the GPS 2 port on the PCS back panel directly to the Secondary GPS COM2 port. The Secondary GPS COM2 port must not be confused with the COM2 port on the PCS. POS MV  processes raw GPS observables and corrections so there is no need to feed corrections directly to the Secondary GPS receiver. The GPS 1 port on the PCS read panel is primarily to allow GPS receiver firmware upgrades. 
The Secondary GPS COM2 Communication Protocol fields are elaborated in Table 50. They specify the COM2 RS-232 communication protocol settings. 
63 
 
 
Table 51: Message 31: Secondary GPS Setup 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  31  N/A  
Byte count  2  ushort  16  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Select/deselect GPS AutoConfig  1  byte  Value State 0 AutoConfig disabled 1 AutoConfig enabled (default) 2-255 Reserved  
Secondary GPS COM1 port message output rate (Not Supported)  1  byte  Value Rate (Hz) 1 1 (default) 2 2 3 3 4 4 5 5 10 10 11-255 Reserved  
Secondary GPS COM2 port control  1  byte  Value Operation 0 Accept RTCM (default) 1 Accept commands 2 Accept RTCA 3-255 Reserved  
Secondary GPS COM2 communication protocol  4  See Table 50 Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  
Antenna frequency (only applicable for Trimble Force5 GPS receivers)  1  byte  Value Operation 0 Accept L1 only 1 Accept L1/L2 2 Accept L2 only  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

64 
 
 
Message 32: Set POS IP Address 
This message installs a new IP address and subnet mask in POS MV. POS MV accepts this message at anytime. The parameters contained in this message become part of the processing parameters (referred to as "settings"), however, POS MV does not save it to NVM but changes an OS setup file. 
It is important to note that while POS provides a lot of freedomto choose addresses, the Internet Assigned Numbers Authority (IANA) has reserved only the following three blocks of the IP address space for private internets: 
10.0.0.0 -10.255.255.255 172.16.0.0 -172.31.255.255 192.168.0.0 -192.168.255.255 
All other addresses are reserved or public and may be assigned to specific companies or organizations. POS address assignments outside these private ranges should be done with care and understanding of the consequences. Likewise, it is important to select an appropriate subnet mask that is compatible with the chosen IP address. The exact subnet mask will depend on the number of sub-networks and hosts per network desired. 
When POS MV activates the new IP address, it will disconnect from any connected controller and begin using the new IP address. The changes take effect immediately upon receipt of the message. 
Table 52: Message 32: Set POS IP Address 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  32  N/A  
Byte count  2  ushort  16  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
IP address: Network part 1  1  byte  [1, 126] Class A (typical subnet mask 255.0.0.0) [128, 191] Class B (typical subnet mask 255.255.0.0 [192, 223] Class C (typical subnet mask 255.255.255.0) default = 129  N/A  
IP address: Network part 2  1  byte  [0, 255] default = 100  N/A  
IP address: Host part 1  1  byte  [0, 255] default = 0  N/A  

65 
 
 
Item  Bytes  Format  Value  Units  
IP address: Host part 2  1  byte  [1, 254] default = 219  N/A  
Subnet mask: Network part 1  1  byte  [255] default = 255 * see conditions below  
Subnet mask: Network part 2  1  byte  [0, 255] default = 255 * see conditions below  
Subnet mask: Host part 1  1  byte  [0, 255] default = 0 * see conditions below  
Subnet mask: Host part 2  1  byte  [0, 254] default = 0 * see conditions below  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

* Not only must the parts of the subnet mask be within the ranges specified, but if the network part 2 and the 2 host fields are considered as one 32 bit word, then any bit that is set may not have a cleared bit to its left. This results in the following valid subnet masks: 
255.0.0.0  255.255.0.0  255.255.255.0  
255.128.0.0  255.255.128.0  255.255.255.128  
255.192.0.0  255.255.192.0  255.255.255.192  
255.224.0.0  255.255.224.0  255.255.255.224  
255.240.0.0  255.255.240.0  255.255.255.240  
255.248.0.0  255.255.248.0  255.255.255.248  
255.252.0.0  255.255.252.0  255.255.255.252  
255.254.0.0  255.255.254.0  255.255.255.254  

The subnet must be chosen carefully if UDP unicast is selected as the network protocol for real-time data output (Messages 52 and 62). The user specified UDP unicast IP address must be within the same subnet as the POS IP address in order for data output to be functional. If the UDP unicast IP address is outside the subnet, there will be no data output on the port that has UDP unicast selected. A quick method to check if two IP addresses are on the same subnet is to performa bitwise AND operation with the subnet and both UDP and POS IP addresses and compare their results. If they are equal, they are on the same subnet. Pseudo code describing this process can be seen below: 
66 
 
 
if ( (POS IP & SUBNET) == (UDP IP & SUBNET) ) // Same subnet  else // Different subnet 
Here is a quick example showing a subnet selection that does not allow UDP unicast output: 
Original POS IP: 192.168.53.100 Original POS Subnet: 255.255.255.0 UDP Unicast IP: 192.168.53.1 
Modified POS IP: 172.16.30.100 Modified POS Subnet: 255.255.0.0 
POS IP:  172  16  30  100  
                                     10101100 00010000 00011110 01100100  
SUBNET:  255  255  0  0  
                                     11111111 11111111 00000000 00000000  
UDP IP:  192  168  53  1  
                                     11000000 10101000 00110101 00000001  

POS IP & SUBNET: 10101100 00010000 00000000 00000000 
UDP IP & SUBNET: 11000000 10101000 00000000 00000000 
Note that (POS IP & SUBNET) != (UDP IP & SUBNET) 
Once modified, the POS IP will change to 172.168.30.100 but the real-time output port will not be sending data to 192.168.53.1 (the selected UDP unicast IP) because it is not on the same subnet. 
Message 33: Event Discrete Setup 
This message directs the POS MV to set the senses of the signals for the Event 1 to 6 discrete input triggers and the PPS output. The user can select either positive or negative edge trigger for each event. The POS MV accepts this message at anytime. The parameters contained in this message become part of the processing parameters (referred to as "settings") that the POS MV saves to NVM. 
67 
 
 
The Guard Time instructs POS MV to ignore any additional event triggers that occur on that input for the specified amount of time after the initial trigger. This can be useful for filtering out spurious trigger signals. The maximum event input frequency is 500 Hz so the default guard time is 2 ms. 
Note that not all POS MV systems support all 6 Event inputs. AP board set has all 6 Event inputs on user connector, rack mount (RM) chassis do not have event inputs, and small form factor (SFF) chassis have 4 Event inputs. Refer to the User Manual for connection details. 
Table 53: Message 33: Event Discrete Setup 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  33  N/A  
Byte count  2  ushort  28  N/A  
Transaction number  2  ushort  Input: Output:  Transaction number [65533, 65535]  N/A  
Event 1 trigger  1  byte  Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  
Event 2 trigger  1  byte  Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  
Event 3 trigger  1  byte  Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  
Event 4 trigger  1  byte  Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  

68 
 
 
Item  Bytes  Format  Value  Units  
Event 5 trigger  1  byte  Value Command 0 Positive edge (default) 1 Negative edge 2-255 Reserved  
Event 6 trigger  1  byte  Value Command 0 Positive edge (default) 1 Negative edge 2-255 Reserved  
Event 1 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  
Event 2 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  
Event 3 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  
Event 4 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  
Event 5 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  
Event 6 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  
PPS Out polarity  1  byte  Value Command 0 Positive pulse (default) 1 Negative pulse 2 Pass through1 3-255 Reserved  
PPS Out pulse width  2  ushort  [1, 500] (default 1)  msec  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

1 - "Pass though" means the PPS Out pulse is identical to the PPS In pulse, whether it is from the internal GNSS or an external PPS source. Ifthis mode is selected the PPS Out pulsewidth field is ignored. 
Message 34: COM Port Setup 
This message sets up the communication protocol and selects the input and output content for all available COM ports. It is a variable length message to accommodate MV V5 hardware with varying numbers of COM ports. 
When this message is sent to POS MV it may contain parameters for 1 to 10 COM ports. Any COM port can be assigned. If an assigned COM port is not present it will be ignored. Any COM port or ports can be specified as long as they are listed in ascending order and the Port Mask field 
69 
 
 
has bits set corresponding to each COM port entry. All input selections and the Base GNSS output selections must be uniquely assigned to a COM port. NMEA and Real-time Binary outputs may be assigned to any number of COM ports. COM6 and 10 are currently considered to be reserved as there is no physical hardware support. COM5 is only provided on certain supporting systems. Please refer to hardware specification for COM5 inclusion. As of FW9.xx, COM7 is used to confirm availability of input through Ethernet, while COM8 and 9 are used to confirm availability of output through Ethernet. COM7 (Ethernet Input) is available across all products. Thus, it should be always included in the Message 34. COM8 and 9 (Ethernet Output) is only available on certain MV configurations. Those configurations should include COM8 and 9 in their Message 34. Note: if COM7, 8, 9 were not part of the user-sent Message 34 but they exist, then the echo reply will contain them. 
Since COM7, 8, and 9 refers to Ethernet communication, fields containing Communication protocol are ignored. Moreover, COM7 will only accept Input select choices "No input", "Base GPS 1", and "Base GPS 2"; any other selections for Input select or any Output select are ignored. For COM8, it expects to have Output select set to "No output" or "NMEA messages". For COM9, it expects to have Output select set to "No output" or "Real-time binary". Other choices are ignored. 
When this message is output from POS MV it always contains parameters for all n COM ports available for that particular system, with the current protocol and input/output selections. 
Table 54: Message 34: COM Port Setup 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  34  N/A  
Byte count  2  ushort  12 + 8 x nPorts  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Number of COM ports  2  ushort  [1,10] Number (nPorts) of COM ports assigned by this message.  N/A  
COM Port Parameters  8 x nPorts  See Table 55 One set of parameters for each of nPorts COM port.  

70 
 
 
Item  Bytes  Format  Value  Units  
Port mask  2  ushort  Input: Bit positions indicate which port parameters are in message (port parameters must appear in order of increasing port number). Bit 0 ignored Bit n set COMn parameter in message Bit n clear COMn parameter not in message Output: Bit positions indicate which port numbers are available on the PCS for I/O configuration.  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  
Table 55: COM port parameters 


Item  Bytes  Format  Value  Units  
Communication protocol  4  See Table 50 Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  
Input select  2  ushort  Value Input 0 No input 1 Auxiliary 1 GNSS 2 Auxiliary 2 GNSS 3 Reserved 4 Base GNSS 1 5 Base GNSS 2 6 Reserved 7 GNSS 11 8 GNSS 21 9-255 No input  

71 
 
 
Item  Bytes  Format  Value  Units  
Output select  2  ushort  Value 0 1 2 3 4 5 6 7 8 9-255  Output No output NMEA messages Real-time binary Reserved Base GNSS 1 Base GNSS 2 Reserved GNSS 11 GNSS 21 No output  

Notes: 1: The GNSS 1 and 2 selection only applies to POS MV V5 stand alone chassis COM 3 and COM 4 respectively, and when selected it applies to both Input and Output. 
Message 35: See Message 135 
Message 36: See Message 136 
Message 37: Base GPS 1 Setup 
This message selects the message types assigned to the Base GPS 1 port identified in Message 
34. If POS MV is connected to a Hayes compatible telephone modem, then this message directs POS MV's configuration of the modem.  
Message 38: Base GPS 2 Setup 
This message selects the message types assigned to the Base GPS 2 port identified in Message 
34. If POS MV is connected to a Hayes compatible telephone modem, then this message directs 
POS MV's configuration of the modem. The connection control field will always be set to NO_ACTION when sent by POS MV except when the message sent by the client had modem control set to AUTOMATIC and the connection control set to CONNECT. The reason for this is to prevent manual or command actions from getting saved in NVM and being inadvertently activated when POS MV is started. The AUTOMATIC-CONNECT combination is the only one that a user may want to save to NVM. 
The IP address for the source of correction must lie within the POS subnet or the message will be rejected. See subnet mask description for Message 32 on page 66. However, if Communication protocol is set to be COM, the IP address range validation will not be done. 
72 
 
 
Table 56: Message 37/38: Base GPS 1/2 Setup 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  37/38  N/A  
Byte count  2  ushort  248  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Select Base GPS input type  2  ushort  Value Operation 0 Do not accept base GPS messages 1 Accept RTCM MSG 1/9 (default) 2 Accept RTCMv2.x MSG 3, 18/19 3 Accept CMR/CMR+ 4 Accept RTCA (Deprecated) 5 Accept RTCMv3.x 6-65535 Reserved  
Line control  1  byte  Value Operation 0 Line used for Serial (default) 1 Line used for Modem 2-255 Reserved  
Modem control  1  byte  Value Operation 0 Automatic control (default) 1 Manual control 2 Command control 3-255 Reserved  
Connection control  1  byte  Value Operation 0 No action (default) 1 Connect 2 Disconnect/Hang-up 3 Send AT Command 4-255 No action  
Phone number  32  char  N/A  N/A  
Number of redials  1  byte  [0, ) default = 0  N/A  
Modem command string  64  char  N/A  N/A  
Modem initialization string  128  char  N/A  N/A  

73 
 
 
Item  Bytes  Format  Value  Units  
Data timeout length  2  ushort  [0, 255] default = 0  seconds  
Datum Type  2  ushort  Value 0 1  Operation WGS 84 (default) NAD 83  
Communication Protocol  1  byte  Value 0 1 2  Protocol COM (default) TCP UDP  
IP address: Network part 1  1  byte  [1,126], [128, 223]  
IP address: Network part 2  1  byte  [0, 255]  
IP address: Host part 1  1  byte  [0, 255]  
IP address: Host part 2  1  byte  [1, 254]  
Port Number  2  ushort  (0,65535]  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 39: Aux GNSS Setup 
This message contains the protocol tobe expected froman auxiliary GNSS receiver connected to POS MV. The default NMEA setting directs POS MV to decode the Aux GNSS data as per the NMEA standard. The NAVCOM setting directs POS MV to decode the GGA station ID field according tothe non-standard NAVCOM encoding. 
Table 57: Message 39: Aux GNSS Setup 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  39  N/A  
Byte count  2  ushort  8  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  

74 
 
 
Item  Bytes  Format  Value  Units  
Aux GNSS 1 protocol  1  Byte  Value 0 1  Protocol NMEA (default) NAVCOM  
Aux GNSS 2 protocol  1  Byte  Value 0 1  Protocol NMEA (default) NAVCOM  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 41: Primary GPS Receiver Integrated DGPS Source Control 
This message is used to specify settings related to the source or service provider of Integrated DGPS corrections. This message is only valid when GPS Type 12 is installed as the Primary GPS receiver. The parameters contained in this message become part of the processing parameters (referred to as "settings") that the POS MV saves to NVM. 
Table 58: Message 41: Primary GPS Receiver Integrated DGPS Source Control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  41  N/A  
Byte count  2  ushort  52  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  

75 
 
 
Item  Bytes  Format  Value  Units  
DGPS source mode  1  byte  Source mode for DGPS corrections: 0 Disabled 2 MarineStar VBS only 5 MarineStar XP only 6 MarineStar HP only 7 MarineStar Auto mode 1, 3, 4 Reserved 8-11 Reserved 12 MarineStar G2 only 13 MarineStar HPXP 14 MarineStar HPG2  N/A  
Beacon Acquisition Mode  1  byte  Beacon mode used to acquire DGPS signals : 0 Channel disabled 1 Manual mode 2 Auto Distance mode 3 Auto Power mode 4-255 Reserved  N/A  
Beacon Channel 0 Frequency  2  ushort  [2835-3250]  10 * kHz  
Beacon Channel 1 Frequency  2  ushort  [2835-3250]  10 * kHz  
Satellite ID  1  byte  0-8 Reserved 9    MarineStar Auto ID Search 10-255 Reserved  N/A  
Satellite bit rate  2  ushort  [600, 1200, 2400]  baud  
Satellite frequency  8  double  [1500e6-1600e6]  Hz  
Request Database Source  1  byte  0 Unknown 1 Beacon Stations 2 LandStar Stations 3-255 Reserved  N/A  

76 
 
 
Item  Bytes  Format  Value  Units  
Landstar Correction Source  1  byte  0 Unknown 1 LandStar Stations 2 LandStar Network 3-255 Reserved  N/A  
MarineSTAR Activation Code  25  byte  0 Unknown (0,) Enter service Provider Activation Information  N/A  
DGPS source mode 2  1  byte  Source mode for DGPS corrections: 0 Disabled 8 WAAS mode 9 EGNOS mode 10 MSAS mode 1-7 Reserved 11-255 Reserved  N/A  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  


4.4.3 Processing Control Messages 
Message 50: Navigation Mode Control 
This message directs POS MV to transition to a specified navigation mode. The two basic navigation modes are Standby and Navigate. 
Table 59: Message 50: Navigation mode control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  50  N/A  
Byte count  2  ushort  8  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  

77 
 
 
Item  Bytes  Format  Value  Units  
Navigation mode  1  byte  Value 0 1 2 3-255  Mode No operation (default) Standby  Navigate Reserved  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 51: Display Port Control 
This message directs POS MV to output specified groups on the Display Port primarily for the 
purpose of display of data on the POS Controller. The Number of Groups field contains the number n of groups that this message selects. Thereafter follow n Display Port Output Group Identification fields, each of which identifies one selected group to be output on the Display Port. 
The POS MV always outputs Groups 1, 2, 3, 10 and 110 on the Display Port to provide a minimal set of data for the POS Controller. These cannot be de-selected by omission from this message. 
POS MV accepts this message at anytime. The parameters contained in this message become 
part of the processing parameters (referred to as "settings") that POS MV saves to NVM. When MV POSView is connected to a POS MV Control port, it immediately sends message 51 requesting the groups it requires to populate all its currently open windows. Whenever the user opens a new display window, MV POSView automatically sends message 51 requesting the additional group(s) that are required. Hence there is no user setup window for the Display port in MV POSView. 
Table 60: Message 51: Display Port Control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  51  N/A  
Byte count  2  ushort  10 + 2 x number of groups (+2 if pad bytes are required)  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  

78 
 
 
Item  Bytes  Format  Value  Units  
Number of groups selected for Display Port  2  ushort  [4, 70] default = 4 (Groups 1,2,3,10 are always output on Display Port)  N/A  
Display Port output group identification  variable  ushort  Group ID to output [1, 65534]  N/A  
Reserved  2  ushort  0  N/A  
Pad  0 or 2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 52: Real-Time Data Port Control 
This message directs POS MV to output specified groups on the Real-Time Data Port at a 
specified rate. The Number of Groups field contains the number n of groups that this message selects. Thereafter follow n Data Port Output Group Identification fields, each of which identifies one selected group to be output on the Data Port. 
The Data Port Output Rate field selects the output rates of all specified groups fromone of several available discrete output rates. POS MV outputs a selected group at the lesser of the user-specified rate or the internal update rate; this depends on the selected group. If the user selects a group to be output at maximum available rate when the internal update rate of the group data is 1 Hz, then POS MV outputs the selected group at 1 Hz. An exception is Group 4: Time-tagged IMU, which the POS MV outputs at the IMU data rate regardless of the user-specified data rate. 
The Data Port Protocol selects which network protocol shall be used. TCP will wait for an incoming TCP connection, UDP unicast will start broadcasting UDP packets to the address specified by the UDP Unicast IP Address paremeters, and UDP Broadcast will broadcast UDP packets to all addresses on the subnet. 
The selected UDP unicast address must be on the currently set POS subnet or the message will 
be rejected. See subnet mask description for Message 32 on page 66 for more details. POS MV accepts this message at anytime. The parameters contained in this message become part of the processing parameters (referred to as "settings") that POS MV saves to NVM. 
79 
 
 
Table 61: Message 52 Real-Time/Logging Data Port Control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  52  N/A  
Byte count  2  ushort  15 + 2 x number of groups (+1 or 3 pad bytes)  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Number of groups selected for Data Port  2  ushort  [0, 70] default = 0  N/A  
Data Port output group identification  variable  ushort  Group ID to output [1, 65534]  N/A  
Data Port output rate  2  ushort  Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 other values Reserved  
Data Port Protocol  1  byte  Value Protocol 0 TCP (default) 1 UDP Unicast 2 UDP Broadcast  
UDP Unicast IP Address: Network part 1  1  byte  [128, 191] Class B, subnet mask 255.255.0.0 [192, 232] Class C, subnet mask 255.255.255.0 default = 192  N/A  

80 
 
 
Item  Bytes  Format  Value  Units  
UDP Unicast IP Address: Network part 2  1  byte  [0, 255] default = 168  N/A  
UDP Unicast IP Address: Host part 1  1  byte  [0, 255] default = 53  N/A  
UDP Unicast IP Address: Host part 2  1  byte  [1, 253] default = 1  N/A  
Pad  1 or 3  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 53: Logging Port Control 
This message controls a data-logging device and directs the POS MV to output specified groups 
on the Logging Port at a specified rate. The Number of Groups field contains the number n of groups that this message selects. Thereafter follow n Logging Port Output Group Identification fields, each of which identifies one selected group to be output on the Logging Port. 
The Logging Port Output Rate field selects the output rates of all specified groups from one of several available discrete output rates. The POS MV will output a selected group at the lesser of the user-specified rate or the internal update rate. This will depend on the selected group. For example, if the user selects a group to be output at 50 Hz when the internal update rate of the group data is 1 Hz, then the POS MV will output the selected group at 1 Hz. An exception is Group 4: Time-tagged IMU, which the POS MV will output at the IMU data rate regardless of the user-specified data rate. The available maximum data output rate is related to the IMU data rate and hence the IMU type. 
The Select/Deselect AutoLog field directs the POS MV to enable or disable the AutoLog function; when the AutoLog function is enabled, the POS MV begins to record data to the Logging Port using the automatically incrementing filename stored in NVM as soon as the POS MV has powered up and self-initialized. This feature allows the user to operate the POS MV and to record data without having to connect a client computer running POS Controller. 
The Disk Logging Control field directs the POS MV to begin and end logging to the logging device connected to the Logging Port. The Filename Kernel field sets the logging filename kernel. The POS MV appends the filename kernel with extensions .000 to .999 to create filenames on the internal logging disk. Each file holds about 12MBytes of recorded data. The default filename kernel is default. 
The POS MV accepts this message at anytime. The parameters contained in this message become part of the processing parameters (referred to as "settings") that the POS MV saves to 
81 
 
 
NVM. 
Table 62: Message 53: Logging Port Control 
Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  53  N/A  
Byte count  2  ushort  76 + 2 x number of groups (+2 if required for pad)  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Number of groups selected for Logging Port  2  ushort  [0, 70] default = 0  N/A  
Logging Port output group identification  variable  ushort  Group ID to Output [1, 65534]  N/A  
Logging Port output rate  2  ushort  Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 (NOT available for IMU type 17.) other values reserved  
Select/deselect AutoLog  1  byte  Value State 0 AutoLog disabled (default) 1 AutoLog enabled 2-255 No action  

82 
 
 
Item  Bytes  Format  Value  Units  
Disk logging control  1  byte  Value Command 0 Stop logging  (default) 1 Start logging 2-255 No action  
Filename kernel  12  chars  Filename kernel (default = default)  N/A  
Reserved  52  bytes  N/A  N/A  
Pad  0 or 2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 54: Save/Restore Parameters Control 
This message directs POS MV to save the current configuration to non-volatile memory (NVM) or to retrieve the currently saved parameters from NVM. POS MV accepts this message at anytime. 
If the Control field is set to any value other than 1-3, this message has no effect. If the Control field is set to 1, POS MV saves the current parameters to NVM, thereby overwriting the previously saved parameters. If the Control field is set to 2, POS MV retrieves the currently saved parameters into the active parameters for the current navigation session. If the Control field is set to 3, POS MV resets the active parameters to the factory default settings. The previously active parameters are overwritten. 
Table 63: Message 54: Save/restore parameters control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  54  N/A  
Byte count  2  ushort  8  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Control  1  byte  Value Operation 0 No operation 1 Save parameters in NVM 2 Restore user settings from NVM 3 Restore factory default settings 4-255 No operation  
Pad  1  byte  0  N/A  

83 
 
 
Item  Bytes  Format  Value  Units  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 55: User Time Recovery 
This message specifies the time of the last PPS in user time to POS MV. It directs POS MV to synchronize its User Time with the time specified in the User PPS Time field. POS MV accepts this message at anytime at a maximum rate of once per second. 
To establish user time synchronization, the user must send the user time of last PPS to POS MV with this message after the PPS has occurred. The resolution of time synchronization is one microsecond. 
Table 64: Message 55: User time recovery 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  55  N/A  
Byte count  2  ushort  24  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
User PPS time  8  double  [0, ) default = 0.0  seconds  
User time conversion factor  8  double  [0, ) default = 1.0  ./seconds  
Pad  2  short  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 56: General Data 
This message provides POS MV with an initial time, position, distance and attitude fix when either the primary GPS receiver is unable to provide this information within a maximum initializationtime. The data in this message allows a stationary POS MV to complete the coarse leveling algorithmand begin operating in Navigate mode. POS MV can also be commanded to start (or continue) in an alignment status beyond coarse leveling should the accuracy of prescribed initial conditions warrant. The initial horizontal position CEP describes the circular error probability of the initial position. The initial altitude standard deviation describes the uncertainty in the initial altitude. These can be used to re-align POS MV at a last known position following an integration failure when GPS is unavailable. 
84 
 
 
POS MV accepts this message at any time. It will only use the data in this message if GPS data remains unavailable for longer than 120 seconds after receipt ofthis message. It will supersede this general data with GPS position data as soon as the GPS data becomes available. POS MV does not save this message to NVM, hence the user must provide this message during every POS MV start-up where the general data are required. 
Table 65: Message 56: General data 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  56  N/A  
Byte count  2  ushort  80  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Time of day: Hours  1  byte  [0, 23] default = 0  hours  
Time of day: Minutes  1  byte  [0, 59] default = 0  minutes  
Time of day: Seconds  1  byte  [0, 59] default = 0  seconds  
Date: Month  1  byte  [1, 12] default = 1  month  
Date: Day  1  byte  [1, 31] default = 1  day  
Date: Year  2  ushort  [0, 65534] default = 0  year  
Initial alignment status  1  byte  See Table 5  N/A  
Initial latitude  8  double  [-90, +90]  default = 0  degrees  
Initial longitude  8  double  [-180, +180] default = 0  degrees  
Initial altitude  8  double  [-1000, +10000] default = 0  meters  
Initial horizontal position CEP  4  float  [0, ) default = 0  meters  
Initial altitude RMS uncertainty  4  float  [0, ) default = 0  meters  
Initial distance  8  double  [0, ) default = 0  meters  
Initial roll  8  double  [-180, +180] default = 0  degrees  
Initial pitch  8  double  [-180, +180] default = 0  degrees  
Initial heading  8  double  [0, 360) default = 0  degrees  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

85 
 
 
Message 57: Installation Calibration Control 
This message controls the POS MV function of self-calibration of primary installation parameters. POS MV accepts this message at any time. The primary installation parameters exclude the GAMS installation parameters, which are handled by a separate calibration function and controlled separately by Message 58: GAMS Calibration Control. 
The calibration is done assuming that the IMU Frame is the Reference Frame. Ifit is desirable to have the IMU and Reference Frames non-coincident, then the user must apply additional offsets consistently to all sensor frames to define a non-coincident Reference Frame. 
The calibration action byte specifies a calibration action. The calibration select byte identifies installation parameter sets on which the calibration action is applied. POS MV executes the specified calibration action as soon as it receives this message. The following are calibration actions available to the user: 
. start an auto-calibration or a manual calibration of selected installation parameters 
. stop an ongoing calibration 
. perform normal transfer of selected calibrated parameters following manual calibration 
. performforced transfer of selected calibrated parameters following manual calibration The user selects one or more installation parameter sets for calibration by setting the bits in the calibration select byte corresponding to the parameter sets to be calibrated to 1. The user starts a calibration of the selected installation parameters by setting the calibration action byte to 2 for a manual calibration or 3 for an auto-calibration. POS MV restarts the Navigate mode with the calibration option set. It then computes corrected versions of the selected installation parameters and reports these with corresponding calibration figures of merit (FOM) in Group 14: Calibrated installation parameters. A calibration of a selected set of installation parameters is completed when the corresponding FOM reaches 100. The user stops all calibrations by setting the calibration action byte to 1. POS MV restarts the Navigate mode without the calibration option and abandons any previous calibrationactions. In an auto-calibration, POS MV replaces the existing set of installation parameters and issues a corresponding Message 20: General Installation and Processing Parameters or Message 22: Aiding Sensor Installation Parameters when the calibration is completed. POS MV resets its Kalman filter and restarts the normal Navigate mode with the updated installation parameters when all selected calibrations are completed. In a manual calibration, POS MV continues the calibration and displays the final values in Group 
14: Calibrated installation parameters until it receives a user command to stop the calibration or 
transfer the calibrated parameters. In a normal transfer of calibrated parameters, POS MV replaces the existing set of installation parameters selected by the calibration select byte with the corrected parameters displayed in Group 14: Calibrated installation parameters and having a FOM of 100. POS MV resets its Kalman filter and restarts the normal Navigate mode with the possibly updated installation parameters. 
86 
 
 
In a forced transfer of calibrated parameters, POS MV replaces the existing set of installation parameters selected by the calibration select byte with the corrected parameters displayed in Group 14: Calibrated installation parameters and having a FOM greater than 0. POS MV resets its Kalman filter and restarts the normal Navigate mode with the updated installation parameters. 
Table 66: Message 57: Installation calibration control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  57  N/A  
Byte count  2  ushort  9  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Calibration action  1  byte  Value Command 0 No action (default) 1 Stop all calibrations 2 Manual calibration 3 Auto-calibration 4 Normal calibrated parameter transfer 5 Forced calibrated parameter transfer 6-255 No action  
Calibration select  2  ushort  Bit (set) Command 0 Calibrate primary GPS lever arm 1 Calibrate auxiliary 1 GPS lever arm 2 Calibrate auxiliary 2 GPS lever arm 3 - 7 reserved 8 Calibrate GAMS lever arm  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

87 
 
 
Message 58: GAMS Calibration Control This message controls the operation of the GAMS calibration function. POS MV accepts this message at any time. 
The GAMS Calibration Control field directs POS MV to do the following: 
. stop a current calibration in progress (deprecated) 
. begin a new calibration or resume a suspended calibration 
. suspend a current calibration in progress (deprecated) or 
. force a calibration to start without regard to the current navigation solution attitude 
accuracy (deprecated) 
However, upon release of the new GAMS/GNSS heading, stop, suspend, and force calibration are no longer accepted. Sending any value other than to begin calibration will result in message rejection and inaction. 
POS MV returns Message 21: GAMS Installation Parameters containing the new GAMS installation parameters when the calibration is completed. 
Table 67: Message 58: GAMS Calibration Control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  58  N/A  
Byte count  2  ushort  8  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
GAMS calibration control  1  byte  Value Command 0 Stop calibration (default) (deprecated) 1 Begin or resume calibration 2 Suspend calibration (deprecated) 3 Force calibration (deprecated) 4-255 No action  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

88 
 
 
Message 61: Logging Data Port Control 
This message directs the POS MV to output specified groups on the Logging Data Port at a specified rate.  
The format is similar to that of Message 52 but no network protocol is specified. Pay attention to the difference in byte count and number of pad bytes. The format is given by Table 68. 
POS MV accepts this message at anytime. The parameters contained in this message become part of the processing parameters (referred to as "settings") that POS MV saves to NVM. 
Table 68: Message 61: Second Data PortControl 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  52 or 61  N/A  
Byte count  2  ushort  10 + 2 x number of groups (+2 if pad bytes are required)  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  
Number of groups selected for Data Port  2  ushort  [0, 70] default = 0  N/A  
Data Port output group identification  variable  ushort  Group ID to output [1, 65534]  N/A  
Data Port output rate  2  ushort  Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 other values Reserved  
Pad  0 or 2  byte  0  N/A  

89 
 
 
Item  Bytes  Format  Value  Units  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  


4.4.4 Program Control Override Messages 
Message 90: Program Control 
This message controls the operational status of POS MV. POS MV accepts this message at any time. POS MV interprets the values in the message as follows. 
000 The connected POS Controller is alive and the TCP/IP connection is good. 
001 Terminate the TCP/IP connection. This allows the POS Controller to disconnect as controller and re-connect later. 
100 Reset the GAMS algorithm to clear any pending problems. 
101 Reset POS to clear pending problems. All parameters will be loaded from NVM after a reset. 
102 Shutdown POS in preparation for power-off. This function allows POS to synchronize its files before the user disconnects the power. The user should ensure that POS settings are saved before beginning the shutdown procedure. 
POS MV continuously monitors the TCP/IP connection between itself and the POS Controller. POS MV expects to receive at least one message fromthe POS Controller every 30 seconds or it will automatically terminate the TCP/IP connection. The purpose of this function is for the POS MV to determine if the POS Controller has failed, in which case it can reset the TCP/IP port. This message can be used with a value of 0 as a no operation (NOP) message when no other messages need to be sent to POS MV. 
Table 69: Message 90: Program Control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  90  N/A  
Byte count  2  ushort  8  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  

90 
 
 
Item  Bytes  Format  Value  Units  
Control  2  ushort  Value Command 000 Controller alive 001 Terminate TCP/IP connection 100 Reset GAMS 101 Reset POS 102 Shutdown POS all other values are reserved  
Pad  0  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 91: GPS Control 
This message directs POS MV to configure or reset its internal GPS receivers. POS MV accepts 
this message at any time. The Control Command field when set to Send GPS configuration (0) directs POS MV to reconfigure the GPS receivers. POS MV then sends the configuration script messages to the receivers in the same way as it does during initialization following power-up. The user would use this command if he suspected that an internal GPS receiver had not initialized correctly or had lost its configuration. 
The Control Command field when set to Send reset command (1) directs POS MV to send "cold reset" commands to theGPS receivers. This directs an internal GPS receiver to revert to the factory default configurations. The user would use this command to establish a starting point for troubleshooting problems with a GPS receiver. 
Table 70: Message 91: GPS control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  91  N/A  
Byte count  2  ushort  8  N/A  
Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  

91 
 
 
Item  Bytes  Format  Value  Units  
Control command  1  byte  Value 0 1 2 3 4-255  Command Send primary GPS configuration Send primary GPS reset command Send secondary GPS configuration Send secondary GPS reset command No action  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  


4.4.5 POS MV Specific Messages 
Message 106: Heave Filter Set-up 
This message allows the user to set the cut-off frequency and damping ratio of the heave filter. Also, the message is accepted at anytime and may be saved. 
Table 71: Message 106: Heave Filter Set-up 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  106  N/A  
Byte count  2  ushort  16  N/A  
Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  
Heave Corner Period  4  float  (10.0, ) (default = 200.0)  seconds  
Heave Damping Ratio  4  float  (0, 1.0) (default = 0.707)  N/A  
Heave Phase Corrector  1  byte  (1,0) = (on,off) (default = 0)  N/A  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

92 
 
 
Message 111: Password Protection Control 
This command "Logs in" the user, or changes the password used for user login. The message is accepted anytime, but is redundant if "Login" (Password Control) is sent when "user logged in" condition exists (see Table 31: Group 110: MV General Status & FDIR). This is 
the case when the user has logged in within the last 10 minutes, and has not disconnected or terminated the connection to the PCS, since the login. The message is not saved to NVM, when sent (and accepted) with Password Control equal to 
"Change Password". The new password is, however, immediately saved in the operating system's configuration file. The message is not echoed nor output to any of Display or Data Ports. 
Table 72: Message 111: Password Protection Control 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  111  N/A  
Byte count  2  ushort  48  N/A  
Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  
Password Control  1  byte  Value Command 0 Login 1 Change Password  N/A  
Password  20  char  String value of current Password, terminated by "null" if less than 20 characters, or 20 (non-null) characters. Default: pcsPasswd  N/A  
New Password  20  char  If Password Control = 0: N/A If Password Control = 1: String value of new (user-selected) Password, terminated by "null" if less than 20 characters, or 20 (non-null) characters.  N/A  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

93 
 
 
Message 120: Sensor Parameter Set-up 
This message contains data that is sent to POS to define the installation parameters of sensors 1 and 2 and the heave lever arm. The interpretation of the items in this message is as follows: Sensor(s) wrt Reference frame mounting angle: 
Physical angular offsets of the sensor(s) body frame with respect to the user defined reference frame. The reference frame is defined as the right-handed orthogonal co-ordinate system with its origin defined at any point the user wishes. The axes are fixed to the reference frame, with the x axis in the forward going direction, the y axis perpendicular to the x axis and pointing to the right (starboard side), and the z axis pointing down. The sensor(s) body frame is defined as the right-handed orthogonal co-ordinate system with its origin at the sensing centre of the sensor. These axes are fixed to the sensor.  
The angles define the Euler sequence of rotations that bring the reference frame into alignment with the sensor body frame. The angles follow the Tate-Bryant sequence of rotation given as follows: right-hand screw rotation of .z about the z axis followed by a rotation of .y about the once rotated y axis followed by a rotation of .x about the twice rotated x axis. The angles .x, .y, and .z may be thought of as the roll, pitch, and yaw of the sensor body frame with respect to the reference frame. 
Reference to Sensor(s) Lever arms: 
Distances measured from the reference frame origin to the sensing centre of the sensors resolved in the reference frame. Since the reference frame is always aligned to the vessel frame (by design), then from the reference frame origin, x is positive towards the bow, y is positive towards the starboard side of the vessel, and z is positive down (Right-Hand Rule). 
Reference to Centre of Rotation Lever arms: 
This set of lever arms allows the user to enter the lever arms between the reference frame origin and the point on the vessel that experiences vertical motion due only to heave, without roll and/or pitch induced vertical motion. The lever arms are defined as the distances measured from the reference frame origin to the centre of rotation (CoR) resolved in the reference frame. Since the reference frame is always aligned to the vessel frame (by design), then from the reference frame origin, x is positive towards the bow, y is positive towards the starboard side of the vessel, and z is positive down (Right-Hand Rule). 
Vertical acceleration data from the IMU is transformed to the centre of vessel rotation (specified by the lever arms), double integrated and passed through the high-pass heave filter and then transformed back to the sensor positions. If this parameter is not entered, heave is calculated at the IMU location and then transformed to the sensor positions. 
94 
 
 
Table 73: Message 120: Sensor Parameter Set-up 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  120  N/A  
Byte count  2  ushort  68  N/A  
Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  
X Sensor 1 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  
Y Sensor 1 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  
Z Sensor 1 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  
X Sensor 2 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  
Y Sensor 2 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  
Z Sensor 2 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  
Reference to Sensor 1 X lever arm  4  float  ( , ) default = 0  m  
Reference to Sensor 1 Y lever arm  4  float  ( , ) default = 0  m  
Reference to Sensor 1 Z lever arm  4  float  ( , ) default = 0  m  
Reference to Sensor 2 X lever arm  4  float  ( , ) default = 0  m  

95 
 
 
Item  Bytes  Format  Value  Units  
Reference to Sensor 2 Y lever arm  4  float  ( , )  default = 0  m  
Reference to Sensor 2 Z lever arm  4  float  ( , )  default = 0  m  
Reference to CoR X lever arm  4  float  ( , )  default = 0  m  
Reference to CoR Y lever arm  4  float  ( , )  default = 0  m  
Reference to CoR Z lever arm  4  float  ( , )  default = 0  m  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

wrt = with respect to 
Message 121: Vessel Installation Parameter Set-up 
This message contains data that is sent to POS to define the installation parameters of the vessel. 
The interpretation of the items in this message is as follows: 

Reference to Vessel Lever Arms: 
This set of lever arms allows the user to define a different point at which the position and velocity data is valid for the vessel than the point to which all lever arms are measured. Thus, it is possible to have position valid at the vessel bridge, but measure all sensor lever arms to some conveniently accessible reference point. 
The lever arm distances are measured fromthe user defined reference frame origin to 
vessel position of interest resolved in the reference frame. 
Table 74: Message 121: Vessel Installation Parameter Set-up 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  121  N/A  
Byte count  2  ushort  20  N/A  
Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  

96 
 
 
Item  Bytes  Format  Value  Units  
Reference to Vessel X lever arm  4  float  ( , )  default = 0  m  
Reference to Vessel Y lever arm  4  float  ( , )  default = 0  m  
Reference to Vessel Z lever arm  4  float  ( , )  default = 0  m  
Pad  2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

Message 135: NMEA Output Set-up 
This message allows the user to configure Nmea output on one or more COM ports. The COM ports on which the Nmea output appears is controlled by message 34. 
Note that this is a MV specific version of the Core message 35. The ZDA, UTC and PPS output strings are fixed at 1 Hz (if selected) and synchronized to the GPS PPS. They may be combined with other outputs at higher rates. 
Table 75: Message 135: NMEA Output Set-up 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  135  N/A  
Byte count  2  ushort  For even #ports (16 + #ports x 10) For odd #ports (18 + #ports x 10)  N/A  
Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  
Reserved  9  byte  N/A  N/A  
Number of Ports  1  byte  [0, 10]  N/A  
NMEA Port Definitions  variable  See Table 76: NMEA Port Definition #ports x 10  
Pad  0 or 21  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  

97 
 
 
Item  Bytes  Format  Value  Units  
Message end  2  char  $#  N/A  

Pad size is 0 bytes if number of ports is even, size is 2 bytes if number of ports is odd. 
Table 76: NMEA Port Definition 

Port Number  1  byte  [1, 10]  N/A  
Nmea Formula Select  4  ulong  Bit (set) Format Formula 0 $xxGST NMEA (pseudorange measurement noise stats) 1 (default) $xxGGA NMEA (Global Position System Fix) 2 $xxHDT NMEA (heading) 3 $xxZDA NMEA (date & time) 4,5 reserved 6 $xxVTG NMEA (track and speed) 7 $PASHR NMEA (attitude (Tate-Bryant)) 8 $PASHR NMEA (attitude (TSS)) 9 $PRDID NMEA (attitude (Tate-Bryant) 10 $PRDID NMEA (attitude (TSS) 11 $xxGGK NMEA (Global Position System Fix) 12 $UTC UTC date and time 13 reserved 14 $xxPPS UTC time of PPS pulse 15 reserved 16 $xxRMC NMEA (Global Position System Fix) 21 $xxGLL NMEA (Global Position System Fix) 22 UTCT UTC Time Trimble Format 23 $xxGGAT NMEA (Trimble expanded GGA) xx - is substituted by the Talker ID  N/A  
Nmea output rate  2  ushort  Value Rate (Hz) 0 N/A  Hz  

98 
 
 

 1 1 (default) 2 2 5 5 10 10 20 20 25 25 50 50 201 0.1 202 0.05 Note: 0.1, 0.05Hz not applicable to ZDA, UTC, PPS  
Talker ID  1  byte  Value ID 0 IN (default) 1 GP  N/A  
Roll Sense  1  byte  Value Digital +ve 0 port up (default) 1 starboard up  N/A  
Pitch Sense  1  byte  Value Digital +ve 0 bow up (default) 1 stern up  N/A  
Heave Sense  1  byte  Value Digital +ve 0 up (default) 1 down  N/A  

Message 136: Binary Output Set-up This message allows the user to configure the real-time binary output on one or more COM ports. The COM ports on which the binary output appears is controlled by message 34. Note that this is a MV specific version of the Core message 36. 
Table 77: Message 136: Binary Output Set-up 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  136  N/A  
Byte count  2  ushort  For even #ports (16 + #ports x 10) For odd #ports (14 + #ports x 10)  N/A  

99 
 
 
Item  Bytes  Format  Value  Units  
Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  
Reserved  7  byte  N/A  N/A  
Number of Ports  1  byte  [0, 10]  N/A  
Binary Port Definitions  #ports x 10  See Table 78: Binary Port Definition  
Pad  0, 2  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  
Table 78: Binary Port Definition 


Pad size is 2 bytes if number of ports is even, size is 0 bytes if number of ports is odd. 
Port Number  1  byte  [1, 10]  N/A  
Formula Select  4  ushort  Value Format Formula 0 - 2 reserved 3 Simrad1000 header (Tate-Bryant) roll = . pitch = . heave = heave heading = . 4 Simrad1000 header (TSS) roll = sin-1(sin.cos.) pitch = . heave = heave heading = . 5 Simrad3000 header (Tate-Bryant) roll = . pitch = . heave = heave heading = . 6 Simrad3000 header (TSS) roll = sin-1(sin.cos.) pitch = . heave = heave  N/A  

100 
 
 

 heading = . 7 TSS (Format 1) header (default) horizontal acceleration vertical acceleration heave = heave status roll = sin-1(sin.cos.) pitch = . <CR><LF> 8 TSM 5265 header (Tate-Bryant) time tag roll = . pitch = . heave = heave heading = . vel (long, trans, down) 9 TSM 5265 time tag (TSS) roll = sin-1(sin.cos.) pitch = . heave = heave heading = . vel (long, trans, down) 10 Atlas header (TSS) roll = sin-1(sin.cos.) pitch = . heave = heave status footer 11 - 15 reserved 16 PPS header GPS seconds of week week number UTC offset PPS count checksum 17 TM1B header checksum byte count week number  

101 
 
 

 GPS seconds of week clock offset clock offset std. dev. UTC offset clock model status  
Message Update Rate  1  byte  Value Rate (Hz) 0 N/A 1 1 2 2 5 5 10 10 20 20 25 25 (default) 50 50 100 100 200 200  Hz  
Roll Sense  1  byte  Value Digital +ve 0 port up (default) 1 starboard up  N/A  
Pitch Sense  1  byte  Value Digital +ve 0 bow up (default) 1 stern up  N/A  
Heave Sense  1  byte  Value Digital +ve 0 up (default) 1 down  N/A  
Sensor Frame Output  1  byte  Value Frame of Reference 0 sensor 1 frame (default) 1 sensor 2 frame  N/A  



4.4.6 POS MV Specific Diagnostic Control Messages 
Message 20102: Binary Output Diagnostics 
This message is used to set selected output values for the real-time binary output port. This is used to allow POS to generate user selectable constant outputs to test the communications interface between POS and the sensor.  
Note that this message must be sent again to disable the fixed output. 
102 
 
 
Table 79: Message 20102: Binary Output Diagnostics 

Item  Bytes  Format  Value  Units  
Message start  4  char  $MSG  N/A  
Message ID  2  ushort  20102  N/A  
Byte count  2  ushort  24  N/A  
Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  
Operator roll input  4  float  (-180, 180] default = 0  deg  
Operator pitch input  4  float  (-180, 180] default = 0  deg  
Operator heading input  4  float  [0, 360) default = 0  deg  
Operator heave input  4  float  [-100 to 100] default = 0  m  
Output Enable  1  byte  Value Command 0 Disabled (default) Output navigation solution data 1 Enabled Output operator specified fixed values  
Pad  1  byte  0  N/A  
Checksum  2  ushort  N/A  N/A  
Message end  2  char  $#  N/A  

103 
 
 
 



5 Appendix A: Data Format Description 
5.1 Data Format 
The data format for byte, short, long, float and double as used in POS are defined as follows: 
Byte or Character 
Table 80: Byte Format MSBit LSBit 
7  6  5  4  3  2  1  0  


Short Integer 
The short integer format of the POS data is the INTEL style byte order as follows: 
Table 81: Short Integer Format MSB LSB 

Byte#: 1 0 

Long Integer 
The long integer format of the POS data is the INTEL style byte order as follows: 
Table 82: Long Integer Format MSB LSB 

31  23  15  7  
24  16  8  0  

Byte #: 3 2 1 0 

Float and Double 
The floating point format of the POS data is the INTEL byte order fromthe IEEE-754 floating point representation standard as follows: 
Table 83: Single-Precision Real Format 

Single-Precision Data format  
31 s  30  23 22 e f  0  
Field Size in Bits  
Sign (s)  1  
Biased Exponents (e)  8  
Fraction (f)  23  
Total  32  

104 
 
 
 
Single-Precision Data format  
Interpretation of Sign  
Positive Fraction  s=0  
Negative Fraction  s=1  
Normalised Numbers  
Bias of Biased Exponent  +127 ($7F)  
Range of Biased Exponent  [0, 255] ($FF)  
Range of Fraction  zero or nonzero  
Fraction  -23)1.f (where f=bit22 -1+bit21 -2...+bit0  
Relation to Representation of Real Numbers  (-1)sx2e-127x1.f  
Approximate Ranges  
Maximum Positive Normalised  3.4x1038  
Minimum Positive Normalised  1.2x10-38  
Table 84: Double-Precision Real Format 


Double-Precision Data format  
63 62 52 51 0 s e f  
Field Size in Bits  
Sign (s)  1  
Biased Exponents (e)  11  
Fraction (f)  52  
Total  64  
Interpretation of Sign  
Positive Fraction  s=0  
Negative Fraction  s=1  
Normalised Numbers  
Bias of Biased Exponent  +1023 ($3FF)  
Range of Biased Exponent  [0, 2047] ($7FF)  
Range of Fraction  zero or nonzero  
Fraction  -52)1.f (where f=bit51 -1+bit50 -2...+bit0  
Relation to Representation of Real Numbers  (-1)sx2e-1023x1.f  
Approximate Ranges  
Maximum Positive Normalized  1.8x10308  
Minimum Positive Normalized  2.2x10-308  



5.2 Invalid Data Values 
Since there are several fields in each group or message, it is possible that one or more numerical fields will be invalid when the group or message is output. The following numerical values should be interpreted as invalid if they are output in any group or message. This does not apply to single or multiple byte fields that are comprised of bit sub-fields. 
The hexadecimal value describes the contents of the bytes that represent the invalid decimal value for the type. The invalid values for all integer types are the maximum positive values that the integer types can take. 
The invalid value for the floating-point types is any value in the range of NaN (Not a Number) or INF (Infinity) defined by IEEE-754. The value NaN is by definition any float or double having a mantissa set to any nonzero value and an exponent whose bits are all set to 1. POS MV assigns an invalid float or double in any group by setting all bits representing the float or double set to 1. POS MV rejects any message that contains any of the invalid integer values in Table 85 or any value in the range of NaN or INF. 
Table 85: Invalid data values 

Data Type  Hexadecimal Value  Decimal Value  
Byte  FF  255 (=28 - 1)  
Short  7F FF  32767 (=215 - 1)  
Unsigned short (ushort)  FF FF  65535 (=216 - 1)  
Long  7F FF FF FF  2147483647 (=231 - 1)  
Unsigned long (ulong)  FF FF FF FF  4294967295 (=232 - 1)  
Float  FF FF FF FF  NaN  
Double  FF FF FF FF FF FF FF FF  NaN  



6 Appendix B: Glossary of Acronyms 
AutoConfig auto configure Aux auxiliary C/A course acquisition char character COM(1) communications port 1 COM(2) communications port 2 COM(3) communications port 3 D down dB decibels deg degrees deg/s degrees/second DGPS differential global positioning system DMI distance measurement indicator double double precision floating point E East FDIR Fault Detection, Isolation and Reconfiguration float floating-point precision GAMS GPS Azimuth Measurement Subsystem GNSS Global Navigation Satellite System GPS Global Positioning System HDOP Horizontal Dilution of Precision Hz Hertz I/O input and output ICD interface control document IMU Inertial Measurement Unit IP Internet Protocol lat latitude long longitude LSB least significant bit m metres m/s metres/second m/s2 metres/second/second ms millisecond MSB most significant bit N North N/A not applicable 
1 
COPYRIGHT  (c) APPLANIX CORPORATION, 2017 
ALLRIGHTS RESERVED.  NO PART OFTHIS PUBLICATION MAYBE REPRODUCED, STORED IN A RETRIEVALSYSTEM OR TRANSMITTED IN ANY FORM ORBY ANY MEANS WITHOUT THE PRIOR WRITTEN CONSENT OFAPPLANIX CORPORATION. 
 
NOP No Operation NVM non-volatile Memory PCS POS Computer System POS Position and Orientation System POSPAC Applanix POSPAC post-processing software package PPS Pulse per Second PRN Pseudo RandomNoise RAM random access memory RF radio frequency RMS root-mean-square RTK real-time kinematic RX receive data sec second SV space vehicle (GPS satellites) TCP Transmission Control Protocol UDP User DatagramProtocol ulong unsigned long ushort unsigned short UTC Universal Coordinated Time VDOP Vertical Dilution of Precision wrt with respect to 
2 
COPYRIGHT  (c) APPLANIX CORPORATION, 2017 
ALLRIGHTS RESERVED.  NO PART OFTHIS PUBLICATION MAYBE REPRODUCED, STORED IN A RETRIEVALSYSTEM OR TRANSMITTED IN ANY FORM ORBY ANY MEANS WITHOUT THE PRIOR WRITTEN CONSENT OFAPPLANIX CORPORATION. 


"""