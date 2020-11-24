import re
import traceback
import ctypes  # for static header types
import numpy  # for dynamic array allocation and manipulation
import datetime
from collections import OrderedDict
import pprint

try:
    from HSTB.shared.HSTPSettings import UseDebug
    _dHSTP = UseDebug()
except:
    _dHSTP = False

types = {"char": ctypes.c_char, "ushort": ctypes.c_ushort, "long": ctypes.c_long, "short": ctypes.c_short,
         "ulong": ctypes.c_ulong, "double": ctypes.c_double, "float": ctypes.c_float, "ubyte": ctypes.c_uint8, "byte": ctypes.c_uint8}

structures = {}  # place finished data structures in this dictionary and other structures can then use them as a sub-type
GROUP_ID_VALUES = {}
GROUP_VALUE_IDS = {}
MESSAGE_ID_VALUES = {}
MESSAGE_VALUE_IDS = {}


class EOD(Exception):

    def __init__(self, value="End Of Data"):
        self.value = value

    def __str__(self):
        return str(self.value)


class CORRUPT(Exception):

    def __init__(self, value="End Of Data"):
        self.value = value

    def __str__(self):
        return str(self.value)


def MakeUnion(cls):
    class MadeUnion(ctypes.Union):
        _pack_ = 1
        _fields_ = [(cls.__name__, cls), ('bytes', ctypes.c_ubyte * ctypes.sizeof(cls))]  # using ubyte since char gets interpreted as string and stops in the event that there is a null ("\00") character
    return MadeUnion


class S57Structure(ctypes.Structure):
    _pack_ = 1


trans = str.maketrans("/-, &:", "______")


def ParseFields(subfields, classdict, bIgnore=False):
    classdict['_arraytypes'] = OrderedDict()  # ordered dictionary!!!
    classdict['subfields'] = OrderedDict()  # ordered dictionary!!!
    classdict['float_types'] = []  # subfields that have a Real float type and will need some conversion constant
    classdict['_fields_'] = []
    classdict['_names_formats'] = {'names': [], 'formats': []}  # dictionary to be passed to numpy dtype constructor
    classdict['_variable_padding'] = False

    variable = None
    padding = None
    last_field = ""
    for bytes_str, datatype, rawname, descr, txtline in subfields:
        descr = descr.strip()
        bFound = False
        bitfield = None
        array = None
        bSkipDType = False
        for tdict in (types, structures):  # structures is a built list that transforms "See Table 3" to class type
            if datatype in tdict:  # for k in tdict.keys():
                # if k==datatype:  #re.match(r"\b%s\b"%k, descr):
                subname = rawname.strip().translate(trans).replace("__", "_").replace("__", "_")
                while subname in classdict['_names_formats']['names']:
                    subname += "_"
                use_type = tdict[datatype]
                # if tdict==structures: print datatype, use_type

                m = re.match(r"variable|\d+(\W*(,|-|to|or)\W*)\d+", bytes_str)  # arrays with undefined size
                if m:
                    if subname == "Pad":
                        array = tdict["byte"]
                        classdict['_variable_padding'] = True
                        padding = subname  # Padding gets computed so we don't need to figure out what field controls the length
                    else:
                        array = tdict[datatype]
                        variable = subname
                else:
                    # fixed size arrays - basic types (not variable and not a structure) which have a set size array length
                    try:
                        n = int(bytes_str)
                        cnt = int(n / ctypes.sizeof(use_type))
                        # print datatype, use_type, cnt
                        if cnt < 1 and n > 0:
                            try:
                                print("GroupID", classdict['subfields']['Group_ID'])
                            except KeyError:
                                try:
                                    print("MessageID", classdict['subfields']['Message_ID'])
                                except:
                                    pass
                            print(" !!!! ********  !!!!! ERROR warning Zero length array -- ", txtline)
                            print('-----', use_type, ctypes.sizeof(use_type), n)

                        if cnt != 1:
                            use_type = tdict[datatype] * cnt
                            if cnt == 0:
                                bSkipDType = True
                    except ValueError:
                        pass
                    except TypeError as e:
                        if use_type == True:
                            pass  # we fill the types with "true" when parsing the text file, so ignore this
                        else:
                            raise e

                # m=re.match(r"\W*\w+\W*:\W*(\d+)", descr[len(k):]) #bitfields
                # if m:
                #    bitfield = int(m.groups()[0])
                bFound = True
        if not bFound:
            if _dHSTP:
                print("failed to find type for:", descr)
                print(bytes_str, datatype, rawname, descr, txtline, subname)
            if bIgnore:
                continue
            raise TypeError("Subtype not found")
        try:
            # if the data record (subname) is variable length then create a placeholder for it that isn't in the ctypes structure
            # otherwise add a ctypes field to the structure for reading via binary memmoves etc.
            if array:
                classdict['_arraytypes'][subname] = array
                if "table" in datatype:
                    classdict[subname] = []  # list of structures ("variable See Table 8")
                else:
                    classdict[subname] = numpy.zeros([0], array)  # numpy will accept ctypes values for dtype
            else:
                classdict['_names_formats']['names'].append(subname)
                if not bSkipDType:  # skip when there is a zero length element.
                    if datatype in types:
                        fmt = use_type
                    elif datatype in structures:
                        if "PCSClassBuilder.py" not in __file__:
                            fmt = use_type._dtype
                        else:  # When parsing the docs and building the classes module the structures dictionary isn't complete so this would fail
                            fmt = ctypes.c_bool
                    else:
                        raise Exception("No type for to use for making numpy dtype")
                classdict['_names_formats']['formats'].append(fmt)
                if bitfield:
                    classdict['_fields_'].append(("_" + subname, use_type, bitfield))  # append the variable name and it's ctype or ctype.structure based class
                else:
                    classdict['_fields_'].append(("_" + subname, use_type))  # append the variable name and it's ctype or ctype.structure based class

                if padding:
                    classdict["_padEnd__"] = "_" + subname
                    padding = None
                if variable:  # previous type was a variable length array, so mark this as the beginning of the post-array data for use in read/write to file functions
                    classdict["_arrayEnd__"] = "_" + subname
                    if "byte_count" in last_field.lower():
                        classdict['_vbyteCount__'] = last_field
                        if _dHSTP:
                            print("********* Byte count used from", last_field)
                    elif "number_of" in last_field.lower():
                        classdict['_vCount__'] = last_field
                        if _dHSTP:
                            print("********* Object count used from", last_field)
                    else:
                        if _dHSTP:
                            print("*********")
                        raise Exception("Didn't find byte count for " + variable + " at " + last_field)
                    variable = None
                else:
                    last_field = subname
        except Exception as e:
            print(bytes_str, datatype, rawname, descr, txtline, subname)
            raise e
        classdict['subfields'][subname] = descr  # store all the format and comment info
    try:
        if classdict['_fields_'][-1][0] not in ("_Message_end", "_Group_end", "_Group_End"):
            if _dHSTP:
                print("Group/message end missing - Last field parsed was " + classdict['_fields_'][-1][0])
    except IndexError:
        if _dHSTP:
            print("Empty data structure - no fields found")
    try:
        classdict['_dtype'] = numpy.dtype(classdict['_names_formats'])  # used for making an object directly into a numpy array -- used to work from field definition but the offset/packing changed from python 2.5 to 2.7 (or the related change in numpy version)
    except Exception as e:
        for bytes_str, datatype, rawname, descr, txtline in subfields:
            print(bytes_str, datatype, rawname, descr, txtline, subname)
        raise e


class MSDF(type(ctypes.Structure)):
    '''This metaclass will read a "s57desc" member (doc string pretty much pulled straight from s57 docs)
    and create a subfields member that has the subfield descriptions (format, names, comments).
    It will also create a ctypes structure with all the fixed length subfields which can be accessed by
    subfield label (four letter acronym).  
    '''
    def __new__(cls, name, bases, classdict):
        # print cls
        # print name
        # print bases
        if 'sdf_list' in classdict:
            # print classdict['s57desc']
            subfields = classdict['sdf_list'][:]
            ParseFields(subfields, classdict)
            # structures[name]=eval(name) #add to the global list of SDF structures to be available to other complex structures.
        # print classdict
        return type(ctypes.Structure).__new__(cls, name, bases, classdict)


class BaseField(ctypes.Structure, metaclass=MSDF):
    _pack_ = 1

    def __init__(self, *args, **opts):
        '''Passing in values in order of the subfield or by acronym name as optional arguments will fill the 
        s57 object accordingly'''
        keys = list(self.subfields.keys())
        try:
            self.predata_len = eval("self.__class__.%s.offset" % self._arrayEnd__)
            self.postdata_len = ctypes.sizeof(self.__class__) - self.predata_len
            try:
                self.postpad_len = ctypes.sizeof(self.__class__) - eval("self.__class__.%s.offset" % self._padEnd__)
                self.postdata_len -= self.postpad_len  # remove the postpad portion
            except AttributeError:
                self.postpad_len = 0

        except AttributeError:
            self.predata_len = ctypes.sizeof(self.__class__)
            self.postdata_len = 0
            self.postpad_len = 0

        for i, v in enumerate(args):
            self.__setattr__(keys[i], v)
        for k, v in list(opts.items()):
            self.__setattr__(k, v)

    def __getattr__(self, key):  # Get the value from the underlying subfield (perform any conversion necessary)
        # if key in s57fields.s57field_dict.keys():
        # if len(key)==4: #try to access the subfield
        if key not in self.float_types:
            try:
                if key.startswith("__"):
                    raise AttributeError
                if key in list(self.__dict__.keys()):  # we've called __getattr__ directly which causes this case
                    sf = self.__dict__[key]
                else:
                    sf = eval("self._%s" % key)
                    if isinstance(sf, bytes):  # in python 3 the char array is coming back as a bytestring, which would break existing code
                        sf = sf.decode("UTF8")
#                if isinstance(sf, str):
#                    return sf
#                else:
#                    return sf.val
                return sf
            except AttributeError:
                raise AttributeError(key + " not in " + str(self.__class__))
        else:
            return eval("self._f_%s" % key)

    def __setattr__(self, key, value):  # Set the underlying subfield value
        try:
            _sf = eval("self._%s" % key)
            try:
                if key not in self.float_types:
                    #                    if isinstance(sf, str):
                    #                        self.__dict__["_"+key] = str(value)
                    #                    else:
                    #                        sf.val = value
                    try:
                        ctypes.Structure.__setattr__(self, "_" + key, value)
                    except:
                        try:
                            ctypes.Structure.__setattr__(self, "_" + key, type(self.__getattr__(key))(value))
                        except:
                            ctypes.Structure.__setattr__(self, "_" + key, value.encode())
                else:
                    self.__dict__["_f_" + key] = value
            except:
                traceback.print_exc()
                #raise AttributeError(key+" Not set correctly")
        except:
            self.__dict__[key] = value

    def __repr__(self):
        strs = []
        for f in self.subfields:
            v = eval("self.%s" % f)
            if isinstance(v, (str)):
                strs.append(f + '="%s"' % v)  # show strings with quotes for cut/paste utility
            else:
                strs.append(f + '=' + str(v))
        return self.FieldTag + '(' + ", ".join(strs) + ')'

    def GetInitStr(self):
        return [self.__getattr__(k) for k in list(self.subfields.keys())]

    def GetTimeTypes(self):
        try:
            tt = self.Time_Distance_Fields.Time_types
            t1 = tt & 0x0F
            t2 = (tt & 0xF0) >> 4
        except AttributeError:
            t1, t2 = None, None
        return t1, t2

    def GetDatetime(self):
        try:
            hdr = self.hdr  # most datasections have the time in a "hdr" attribute
        except:
            hdr = self  # otherwise this may be a FISHPACSENSORSSECTION itself
        return datetime.datetime(hdr.year, hdr.month, hdr.day, hdr.hour, hdr.minute, hdr.second, int(hdr.fseconds * 1000000))

    def ReadFromFile(self, f, pos=-1, skim=False):
        '''Reads PosMV style packets.  Either it's fixed size or there is a single (group) of
        variable sized data in the middle of the packet.
        '''
        if pos >= 0:
            f.seek(pos)
        startpos = f.tell()

        s = f.read(self.predata_len)
        if len(s) < self.predata_len:
            raise EOD
        ctypes.memmove(ctypes.addressof(self), s, self.predata_len)
        our_len = self.predata_len
        if self.postdata_len > 0 or self.postpad_len > 0:  # there is variable length data which has to be figured out (and possibly variable length padding too)
            # predata_len includes the PCSRecordHEader but the Byte_count in the PCS structures does not so add it to the Byte_count
            remaining_len = self.Byte_count + ctypes.sizeof(PCSRecordHeader) - self.predata_len  # @UndefinedVariable
            remaining_data = f.read(remaining_len)
            # Get the first variable field (there is often a variable sized padding field that follows)
            arraykey, dtype = list(self._arraytypes.items())[0]  # the fieldname and type of data expected
            try:
                # if it's a plain array of a type then read it from the string
                variable_len = self.__getattr__(self._vbyteCount__)
                array = numpy.fromstring(remaining_data[:variable_len], dtype)
            except AttributeError:
                # if the array failed then it's an array of structures (tables) in the pdf description, so read each entry separately
                element_size = ctypes.sizeof(dtype)
                arraycnt = self.__getattr__(self._vCount__)
                variable_len = arraycnt * element_size
                array = []
                for n in range(arraycnt):
                    v = dtype()
                    ctypes.memmove(ctypes.addressof(v), remaining_data[n * element_size:], element_size)
                    array.append(v)
            our_len += variable_len
            self.__setattr__(arraykey, array)  # _vbyteCount has the fieldname of whatever field preceeds the array and should specify how many bytes are there

            # if self.postpad_len == 0 and not self._variable_padding:  # the variable data structure has a 4 byte alignment so there is no pad
            #    ctypes.memmove(ctypes.addressof(self) + self.predata_len, f.read(self.postdata_len), self.postdata_len)
            # read the post variable length data
            ctypes.memmove(ctypes.addressof(self) + self.predata_len, remaining_data[variable_len:], self.postdata_len)
            our_len += self.postdata_len
            # read the post variable length pad data
            ctypes.memmove(ctypes.addressof(self) + self.predata_len + self.postdata_len, remaining_data[-self.postpad_len:], self.postpad_len)
            our_len += self.postpad_len
            # else:  # there is a padding with variable size
            #    pad_len = self.Byte_count + ctypes.sizeof(PCSRecordHeader) - ctypes.sizeof(self.__class__) - variable_len
            #    #extra = v % 4
            #    #pad_len = (4 - extra) % 4
            #    ctypes.memmove(ctypes.addressof(self) + self.predata_len, remaining_data[self.predata_len + variable_len:], self.postdata_len)

            if len(self._arraytypes) > 1:
                padkey, dtype = list(self._arraytypes.items())[1]  # the fieldname and type of data expected
                self.__setattr__(padkey, numpy.fromstring(remaining_data[self.predata_len + self.postdata_len + variable_len:-self.postpad_len], dtype))  # _vbyteCount has the fieldname of whatever field preceeds the array and should specify how many bytes are there

        if not skim:
            bBadEnd = False
            try:
                if self.Message_end != "$#":
                    bBadEnd = True
            except AttributeError:
                try:
                    if self.Group_end != "$#":
                        bBadEnd = True
                except AttributeError:
                    try:
                        if self.Group_End != "$#":
                            bBadEnd = True
                    except AttributeError:
                        pass  # non-group/message sub-structure
            if bBadEnd:
                # if reading with the wrong version/revision some of the packets will still work but others may fail
                # Force to the correct position for the next record so that a unknown change in data format won't corrupt reading of the rest of the data.
                f.seek(startpos + self.Byte_count + ctypes.sizeof(PCSRecordHeader))  # @UndefinedVariable
                try:
                    gid = self.Group_ID
                except:
                    try:
                        gid = self.Message_ID
                    except:
                        gid = "Unknown"
                print("Corrupt packet %s (ID %s), data said %d bytes while the class structure + variable size read is %d" % (self.FieldTag, gid, self.Byte_count + ctypes.sizeof(PCSRecordHeader), our_len))  # @UndefinedVariable
                raise CORRUPT("Bad end tag")
                # print "************Bad end tag -- try to reset file pointer******************"
                # print self


#     def WriteToFile(self, f, pos=-1):
#         '''Writes a ctypes dataset, any of the fixed size headers should work, can't ascii strings.
#         Need to override for anything needing to write non-ctypes or SDF data channel data strings .
#         '''
#         raise Exception("Not finished")
#         # To implement this, need to iterate the subfields and write out each as a binary (or do as a group)
#         # watch out for the variable size data and the padding which can also be variable length
#         if pos >= 0:
#             f.seek(pos)
#         f.write(self)
#         for name, dtype in self._arraytypes.iteritems():
#             if dtype != ctypes.c_char:  # character string/arrays are handled special in an overloaded WriteToFile method
#                 a = self.__getattr__(name)
#                 numbytes = numpy.array([len(a)], dtype)  # get the length of the coming array
#                 numbytes.tofile(f)
#                 a.tofile(f)


#--------------------------------------------------------------------------------------------------------
# Everything above this point is copied verbatim into the s57classes.py, below will be the dynamic content
#--------------------------------------------------------------------------------------------------------

class PCSRecordHeader(BaseField):
    FieldTag="PCSRecordHeader"
    sdf_list = [['4', 'char', 'Start', '$GRP N/A ', 'Start 4 char $GRP N/A '],
 ['2', 'ushort', 'ID', '2 N/A ', 'ID 2 ushort 2 N/A '],
 ['2', 'ushort', 'Byte count', '80 bytes ', 'Byte count 2 ushort 80 bytes ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['PCSRecordHeader']=PCSRecordHeader
structures["see table 0"]=PCSRecordHeader
        
class GrpRecordHeader(BaseField):
    FieldTag="GrpRecordHeader"
    sdf_list = [['4', 'char', 'Start', '$GRP N/A ', 'Start 4 char $GRP N/A '],
 ['2', 'ushort', 'ID', '2 N/A ', 'ID 2 ushort 2 N/A '],
 ['2', 'ushort', 'Byte count', '80 bytes ', 'Byte count 2 ushort 80 bytes '],
 ['8', 'double', 'Time 1', 'N/A seconds ', 'Time 1 8 double N/A seconds '],
 ['8', 'double', 'Time 2', 'N/A seconds ', 'Time 2 8 double N/A seconds '],
 ['8',
  'double',
  'Distance tag',
  'N/A meters ',
  'Distance tag 8 double N/A meters '],
 ['1',
  'byte',
  'Time types',
  'Time 1 Select Value in bits 0-3 ',
  'Time types 1 byte Time 1 Select Value in bits 0-3 ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GrpRecordHeader']=GrpRecordHeader
structures["see table 1"]=GrpRecordHeader
        
class Time_and_distance_fields(BaseField):
    FieldTag="Time_and_distance_fields"
    sdf_list = [['8',
  'double',
  'Time 1',
  ' N/A  seconds  ',
  'Time 1  8  double  N/A  seconds  '],
 ['8',
  'double',
  'Time 2',
  ' N/A  seconds  ',
  'Time 2  8  double  N/A  seconds  '],
 ['8',
  'double',
  'Distance tag',
  ' N/A  meters  ',
  'Distance tag  8  double  N/A  meters  '],
 ['1',
  'byte',
  'Time types',
  ' Time 1 Select Value in bits 0-3, Time 2 Select Value in bits 4-7  ',
  'Time types  1  byte  Time 1 Select Value in bits 0-3, Time 2 Select Value in bits 4-7  '],
 ['1',
  'byte',
  'Distance type',
  ' Distance Select Value N/A 0 POS distance 1 (default) DMI distance 2  ',
  'Distance type  1  byte  Distance Select Value N/A 0 POS distance 1 (default) DMI distance 2  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Time_and_distance_fields']=Time_and_distance_fields
structures["see table 3"]=Time_and_distance_fields
        
class Vessel_position_velocity_attitude_dynamics(BaseField):
    FieldTag="Vessel_position_velocity_attitude_dynamics"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  Char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 1  N/A  ', 'Group ID  2  Ushort  1  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 132  bytes  ',
  'Byte count  2  Ushort  132  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['8',
  'double',
  'Latitude',
  ' (-90, 90]  degrees  ',
  'Latitude  8  double  (-90, 90]  degrees  '],
 ['8',
  'double',
  'Longitude',
  ' (-180, 180]  degrees  ',
  'Longitude  8  double  (-180, 180]  degrees  '],
 ['8',
  'double',
  'Altitude',
  ' ( , )  meters  ',
  'Altitude  8  double  ( , )  meters  '],
 ['4',
  'float',
  'North velocity',
  ' ( , )  meters/second  ',
  'North velocity  4  float  ( , )  meters/second  '],
 ['4',
  'float',
  'East velocity',
  ' ( , )  meters/second  ',
  'East velocity  4  float  ( , )  meters/second  '],
 ['4',
  'float',
  'Down velocity',
  ' ( , )  meters/second  ',
  'Down velocity  4  float  ( , )  meters/second  '],
 ['8',
  'double',
  'Vessel roll',
  ' (-180, 180]  degrees  ',
  'Vessel roll  8  double  (-180, 180]  degrees  '],
 ['8',
  'double',
  'Vessel pitch',
  ' (-90, 90]  degrees  ',
  'Vessel pitch  8  double  (-90, 90]  degrees  '],
 ['8',
  'double',
  'Vessel heading',
  ' [0, 360)  degrees  ',
  'Vessel heading  8  double  [0, 360)  degrees  '],
 ['8',
  'double',
  'Vessel wander angle',
  ' (-180, 180]  degrees  ',
  'Vessel wander angle  8  double  (-180, 180]  degrees  '],
 ['4',
  'float',
  'Vessel track angle',
  ' [0, 360)  degrees  ',
  'Vessel track angle  4  float  [0, 360)  degrees  '],
 ['4',
  'float',
  'Vessel speed',
  ' [0, )  meters/second  ',
  'Vessel speed  4  float  [0, )  meters/second  '],
 ['4',
  'float',
  'Vessel angular rate about longitudinal axis',
  ' ( , )  degrees/second  ',
  'Vessel angular rate about longitudinal axis  4  float  ( , )  degrees/second  '],
 ['4',
  'float',
  'Vessel angular rate about transverse axis',
  ' ( , )  degrees/second  ',
  'Vessel angular rate about transverse axis  4  float  ( , )  degrees/second  '],
 ['4',
  'float',
  'Vessel angular rate about down axis',
  ' ( , )  degrees/second  ',
  'Vessel angular rate about down axis  4  float  ( , )  degrees/second  '],
 ['4',
  'float',
  'Vessel longitudinal acceleration',
  ' ( , )  meters/second2  ',
  'Vessel longitudinal acceleration  4  float  ( , )  meters/second2  '],
 ['4',
  'float',
  'Vessel transverse acceleration',
  ' ( , )  meters/second2  ',
  'Vessel transverse acceleration  4  float  ( , )  meters/second2  '],
 ['4',
  'float',
  'Vessel down acceleration',
  ' ( , )  meters/second2  ',
  'Vessel down acceleration  4  float  ( , )  meters/second2  '],
 ['1',
  'byte',
  'Alignment status',
  ' See Table 5  N/A  ',
  'Alignment status  1  byte  See Table 5  N/A  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Vessel_position_velocity_attitude_dynamics']=Vessel_position_velocity_attitude_dynamics
structures["see table 4"]=Vessel_position_velocity_attitude_dynamics
        
GROUP_ID_VALUES[1]='Vessel_position_velocity_attitude_dynamics'

GROUP_VALUE_IDS['Vessel_position_velocity_attitude_dynamics']=1

class alignment_status(BaseField):
    FieldTag="alignment_status"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['alignment_status']=alignment_status
structures["see table 5"]=alignment_status
        
class Vessel_navigation_performance_metrics(BaseField):
    FieldTag="Vessel_navigation_performance_metrics"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 2  N/A  ', 'Group ID  2  ushort  2  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 80  bytes  ',
  'Byte count  2  ushort  80  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'float',
  'North position RMS error',
  ' [0, )  meters  ',
  'North position RMS error  4  float  [0, )  meters  '],
 ['4',
  'float',
  'East position RMS error',
  ' [0, )  meters  ',
  'East position RMS error  4  float  [0, )  meters  '],
 ['4',
  'float',
  'Down position RMS error',
  ' [0, )  meters  ',
  'Down position RMS error  4  float  [0, )  meters  '],
 ['4',
  'float',
  'North velocity RMS error',
  ' [0, )  meters/second  ',
  'North velocity RMS error  4  float  [0, )  meters/second  '],
 ['4',
  'float',
  'East velocity RMS error',
  ' [0, )  meters/second  ',
  'East velocity RMS error  4  float  [0, )  meters/second  '],
 ['4',
  'float',
  'Down velocity RMS error',
  ' [0, )  meters/second  ',
  'Down velocity RMS error  4  float  [0, )  meters/second  '],
 ['4',
  'float',
  'Roll RMS error',
  ' [0, )  degrees  ',
  'Roll RMS error  4  float  [0, )  degrees  '],
 ['4',
  'float',
  'Pitch RMS error',
  ' [0, )  degrees  ',
  'Pitch RMS error  4  float  [0, )  degrees  '],
 ['4',
  'float',
  'Heading RMS error',
  ' [0, )  degrees  ',
  'Heading RMS error  4  float  [0, )  degrees  '],
 ['4',
  'float',
  'Error ellipsoid semi-major',
  ' [0, )  meters  ',
  'Error ellipsoid semi-major  4  float  [0, )  meters  '],
 ['4',
  'float',
  'Error ellipsoid semi-minor',
  ' [0, )  meters  ',
  'Error ellipsoid semi-minor  4  float  [0, )  meters  '],
 ['4',
  'float',
  'Error ellipsoid orientation',
  ' (0, 360]  degrees  ',
  'Error ellipsoid orientation  4  float  (0, 360]  degrees  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Vessel_navigation_performance_metrics']=Vessel_navigation_performance_metrics
structures["see table 6"]=Vessel_navigation_performance_metrics
        
GROUP_ID_VALUES[2]='Vessel_navigation_performance_metrics'

GROUP_VALUE_IDS['Vessel_navigation_performance_metrics']=2

class GNSS_receiver_channel_status_data(BaseField):
    FieldTag="GNSS_receiver_channel_status_data"
    sdf_list = [['2',
  'ushort',
  'SV PRN',
  ' [1, 138]  N/A  ',
  'SV PRN  2  ushort  [1, 138]  N/A  '],
 ['2',
  'ushort',
  'Channel tracking status',
  ' See Table 11  N/A  ',
  'Channel tracking status  2  ushort  See Table 11  N/A  '],
 ['4',
  'float',
  'SV azimuth',
  ' [0, 360)  degrees  ',
  'SV azimuth  4  float  [0, 360)  degrees  '],
 ['4',
  'float',
  'SV elevation',
  ' [0, 90]  degrees  ',
  'SV elevation  4  float  [0, 90]  degrees  '],
 ['4',
  'float',
  'SV L1 SNR',
  ' [0, )  dB  ',
  'SV L1 SNR  4  float  [0, )  dB  '],
 ['4',
  'float',
  'SV L2 SNR',
  ' [0, )  dB  ',
  'SV L2 SNR  4  float  [0, )  dB  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GNSS_receiver_channel_status_data']=GNSS_receiver_channel_status_data
structures["see table 8"]=GNSS_receiver_channel_status_data
        
class GNSS_navigationsolution_status(BaseField):
    FieldTag="GNSS_navigationsolution_status"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GNSS_navigationsolution_status']=GNSS_navigationsolution_status
structures["see table 9"]=GNSS_navigationsolution_status
        
class NAVCOM_navigation_solution_status(BaseField):
    FieldTag="NAVCOM_navigation_solution_status"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['NAVCOM_navigation_solution_status']=NAVCOM_navigation_solution_status
structures["see table 10"]=NAVCOM_navigation_solution_status
        
class GNSS_channel_status(BaseField):
    FieldTag="GNSS_channel_status"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GNSS_channel_status']=GNSS_channel_status
structures["see table 11"]=GNSS_channel_status
        
class GNSS_receiver_type(BaseField):
    FieldTag="GNSS_receiver_type"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GNSS_receiver_type']=GNSS_receiver_type
structures["see table 12"]=GNSS_receiver_type
        
class Time_tagged_IMU_data(BaseField):
    FieldTag="Time_tagged_IMU_data"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 4  N/A  ', 'Group ID  2  ushort  4  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 60  bytes  ',
  'Byte count  2  ushort  60  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['29', 'byte', 'IMU Data', ' ', 'IMU Data  29 byte  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Time_tagged_IMU_data']=Time_tagged_IMU_data
structures["see table 13"]=Time_tagged_IMU_data
        
GROUP_ID_VALUES[4]='Time_tagged_IMU_data'

GROUP_VALUE_IDS['Time_tagged_IMU_data']=4

class Event_1_2(BaseField):
    FieldTag="Event_1_2"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 5 or 6  N/A  ',
  'Group ID  2  ushort  5 or 6  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 36  bytes  ',
  'Byte count  2  ushort  36  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'ulong',
  'Event pulse number',
  ' [0, )  N/A  ',
  'Event pulse number  4  ulong  [0, )  N/A  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Event_1_2']=Event_1_2
structures["see table 14"]=Event_1_2
        
GROUP_ID_VALUES[5]='Event_1_2'

GROUP_VALUE_IDS['Event_1_2']=5

GROUP_ID_VALUES[6]='Event_1_2'

GROUP_VALUE_IDS['Event_1_2']=6

class PPS_Time_Recovery_and_Status(BaseField):
    FieldTag="PPS_Time_Recovery_and_Status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 7  N/A  ', 'Group ID  2  ushort  7  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 36  bytes  ',
  'Byte count  2  ushort  36  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'ulong',
  'PPS count',
  ' [0, )  N/A  ',
  'PPS count  4  ulong  [0, )  N/A  '],
 ['1',
  'byte',
  'Time synchronization status',
  ' 0 1 2 3  Not synchronized Synchronizing Fully synchronized Using old offset  ',
  'Time synchronization status  1  byte  0 1 2 3  Not synchronized Synchronizing Fully synchronized Using old offset  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group End', ' $#  N/A  ', 'Group End  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['PPS_Time_Recovery_and_Status']=PPS_Time_Recovery_and_Status
structures["see table 15"]=PPS_Time_Recovery_and_Status
        
GROUP_ID_VALUES[7]='PPS_Time_Recovery_and_Status'

GROUP_VALUE_IDS['PPS_Time_Recovery_and_Status']=7

class Logging_Information(BaseField):
    FieldTag="Logging_Information"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 8  N/A  ', 'Group ID  2  ushort  8  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 4848  N/A  ',
  'Byte count  2  ushort  4848  N/A  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'ulong',
  'Disk Kbytes remaining',
  ' [0, )  Kbytes  ',
  'Disk Kbytes remaining  4  ulong  [0, )  Kbytes  '],
 ['4',
  'ulong',
  'Disk Kbytes logged',
  ' [0, )  Kbytes  ',
  'Disk Kbytes logged  4  ulong  [0, )  Kbytes  '],
 ['4',
  'float',
  'Disk logging time remaining',
  ' [0, )  Seconds  ',
  'Disk logging time remaining  4  float  [0, )  Seconds  '],
 ['4',
  'ulong',
  'Disk Kbytes total',
  ' [0, )  Kbytes  ',
  'Disk Kbytes total  4  ulong  [0, )  Kbytes  '],
 ['1',
  'byte',
  'Logging State',
  ' 0 Standby 1 Logging 2 Buffering 255 Invalid  ',
  'Logging State  1  byte  0 Standby 1 Logging 2 Buffering 255 Invalid  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group End', ' $#  N/A  ', 'Group End  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Logging_Information']=Logging_Information
structures["see table 16"]=Logging_Information
        
GROUP_ID_VALUES[8]='Logging_Information'

GROUP_VALUE_IDS['Logging_Information']=8

class GAMS_Solution_Status(BaseField):
    FieldTag="GAMS_Solution_Status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 9  N/A  ', 'Group ID  2  ushort  9  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 72  bytes  ',
  'Byte count  2  ushort  72  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['1',
  'ubyte',
  'Number of satellites',
  ' N/A  N/A  ',
  'Number of satellites  1  ubyte  N/A  N/A  '],
 ['4',
  'float',
  'A priori PDOP',
  ' [0, 999]  N/A  ',
  'A priori PDOP  4  float  [0, 999]  N/A  '],
 ['4',
  'float',
  'Computed antenna separation',
  ' [0, )  meters  ',
  'Computed antenna separation  4  float  [0, )  meters  '],
 ['1',
  'byte',
  'Solution Status',
  ' 0 fixed integer 1 fixed integer test install data 2 degraded fixed integer 3 floated ambiguity 4 degraded floated ambiguity 5 solution without install data 6 solution from navigator attitude and install data 7 no solution  ',
  'Solution Status  1  byte  0 fixed integer 1 fixed integer test install data 2 degraded fixed integer 3 floated ambiguity 4 degraded floated ambiguity 5 solution without install data 6 solution from navigator attitude and install data 7 no solution  '],
 ['12',
  'byte',
  'PRN assignment',
  ' Each byte contains 0-32 where 0 = unassigned PRN 1-40 = PRN assigned to channel  ',
  'PRN assignment  12  byte  Each byte contains 0-32 where 0 = unassigned PRN 1-40 = PRN assigned to channel  '],
 ['2',
  'ushort',
  'Cycle slip flag',
  ' Bits 0-11: (k-1)th bit set to 1 implies cycle slip in channel k. Example: Bit 3 set to 1 implies cycle slip in channel 4. Bits 12-15: not used.  ',
  'Cycle slip flag  2  ushort  Bits 0-11: (k-1)th bit set to 1 implies cycle slip in channel k. Example: Bit 3 set to 1 implies cycle slip in channel 4. Bits 12-15: not used.  '],
 ['8',
  'double',
  'GAMS heading',
  ' [0,360)  Degrees  ',
  'GAMS heading  8  double  [0,360)  Degrees  '],
 ['8',
  'double',
  'GAMS heading RMS error',
  ' (0, )  Degrees  ',
  'GAMS heading RMS error  8  double  (0, )  Degrees  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GAMS_Solution_Status']=GAMS_Solution_Status
structures["see table 17"]=GAMS_Solution_Status
        
GROUP_ID_VALUES[9]='GAMS_Solution_Status'

GROUP_VALUE_IDS['GAMS_Solution_Status']=9

class General_and_FDIR_status(BaseField):
    FieldTag="General_and_FDIR_status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 10  N/A  ', 'Group ID  2  ushort  10  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 60  Bytes  ',
  'Byte count  2  ushort  60  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'ulong',
  'General Status A',
  ' Coarse levelling active Coarse levelling failed Quadrant resolved Fine align active Inertial navigator initialised Inertial navigator alignment active  bit 0: set bit 1: set bit 2: set bit 3: set bit 4: set bit 5: set  ',
  'General Status A  4  ulong  Coarse levelling active Coarse levelling failed Quadrant resolved Fine align active Inertial navigator initialised Inertial navigator alignment active  bit 0: set bit 1: set bit 2: set bit 3: set bit 4: set bit 5: set  '],
 ['4',
  'ulong',
  'General Status',
  ' User attitude RMS performance bit 0: set  ',
  'General Status  4  ulong  User attitude RMS performance bit 0: set  '],
 ['4',
  'ulong',
  'General Status',
  ' Gimbal input ON bit 0: set  ',
  'General Status  4  ulong  Gimbal input ON bit 0: set  '],
 ['4',
  'ulong',
  'FDIR Level 1',
  ' IMU-POS checksum error bit 0: set  ',
  'FDIR Level 1  4  ulong  IMU-POS checksum error bit 0: set  '],
 ['2',
  'ushort',
  'FDIR Level 1 IMU failures',
  ' Shows number of FDIR Level 1 Status IMU failures (bits 0 or 1) = Bad IMU Frames  ',
  'FDIR Level 1 IMU failures   2  ushort  Shows number of FDIR Level 1 Status IMU failures (bits 0 or 1) = Bad IMU Frames  '],
 ['2',
  'ushort',
  'FDIR Level 2',
  ' Inertial speed exceeds max bit 0: set  ',
  'FDIR Level 2  2  ushort  Inertial speed exceeds max bit 0: set  '],
 ['2',
  'ushort',
  'FDIR Level 3 status',
  ' Reserved bits: 0-15  ',
  'FDIR Level 3 status  2  ushort  Reserved bits: 0-15  '],
 ['2',
  'ushort',
  'FDIR Level 4',
  ' Primary GPS position rejected bit 0: set  ',
  'FDIR Level 4  2  ushort  Primary GPS position rejected bit 0: set  '],
 ['2',
  'ushort',
  'FDIR Level 5',
  ' X accelerometer failure bit 0: set  ',
  'FDIR Level 5  2  ushort  X accelerometer failure bit 0: set  '],
 ['4',
  'ulong',
  'Extended Status',
  ' Primary GPS in Marinestar HP mode Primary GPS in Marinestar XP mode Primary GPS in Marinestar VBS mode Primary GPS in PPP mode Aux. GPS in Marinestar HP mode Aux. GPS in Marinestar XP mode Aux. GPS in Marinestar VBS mode Aux. GPS in PPP mode Primary GPS in Marinestar G2 mode Primary GPS in Marinestar HPXP mode Primary GPS in Marinestar HPG2 mode Reserved  bit 0: set bit 1: set bit 2: set bit 3: set bit 4: set bit 5: set bit 6: set bit 7: set bit 12:set bit 14:set bit 15:set bits: 8-11 13,16-31  ',
  'Extended Status  4  ulong  Primary GPS in Marinestar HP mode Primary GPS in Marinestar XP mode Primary GPS in Marinestar VBS mode Primary GPS in PPP mode Aux. GPS in Marinestar HP mode Aux. GPS in Marinestar XP mode Aux. GPS in Marinestar VBS mode Aux. GPS in PPP mode Primary GPS in Marinestar G2 mode Primary GPS in Marinestar HPXP mode Primary GPS in Marinestar HPG2 mode Reserved  bit 0: set bit 1: set bit 2: set bit 3: set bit 4: set bit 5: set bit 6: set bit 7: set bit 12:set bit 14:set bit 15:set bits: 8-11 13,16-31  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['General_and_FDIR_status']=General_and_FDIR_status
structures["see table 18"]=General_and_FDIR_status
        
GROUP_ID_VALUES[10]='General_and_FDIR_status'

GROUP_VALUE_IDS['General_and_FDIR_status']=10

class Secondary_GNSS_status(BaseField):
    FieldTag="Secondary_GNSS_status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 11  N/A  ', 'Group ID  2  ushort  11  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 76 + 20 x (number of channels)  Bytes  ',
  'Byte count  2  ushort  76 + 20 x (number of channels)  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['1',
  'byte',
  'Navigation solution status',
  ' See Table 9  N/A  ',
  'Navigation solution status  1  byte  See Table 9  N/A  '],
 ['1',
  'byte',
  'Number of SV tracked',
  ' [0, 60]  N/A  ',
  'Number of SV tracked  1  byte  [0, 60]  N/A  '],
 ['2',
  'ushort',
  'Channel status byte count',
  ' [0, 1200]  Bytes  ',
  'Channel status byte count  2  ushort  [0, 1200]  Bytes  '],
 ['variable',
  'see table 8',
  'Channel status',
  ' ',
  'Channel status  variable  See Table 8  '],
 ['4', 'float', 'HDOP', ' (0, )  N/A  ', 'HDOP  4  float  (0, )  N/A  '],
 ['4', 'float', 'VDOP', ' (0, )  N/A  ', 'VDOP  4  float  (0, )  N/A  '],
 ['4',
  'float',
  'DGPS correction latency',
  ' [0, 99.9]  Seconds  ',
  'DGPS correction latency  4  float  [0, 99.9]  Seconds  '],
 ['2',
  'ushort',
  'DGPS reference ID',
  ' [0, 1023]  N/A  ',
  'DGPS reference ID  2  ushort  [0, 1023]  N/A  '],
 ['4',
  'ulong',
  'GPS/UTC week number',
  ' [0, 9999) 0 if not available  Week  ',
  'GPS/UTC week number  4  ulong  [0, 9999) 0 if not available  Week  '],
 ['8',
  'double',
  'GPS/UTC time offset ',
  ' ( , 0]  Seconds  ',
  'GPS/UTC time offset (GPS time - UTC time)  8  double  ( , 0]  Seconds  '],
 ['4',
  'float',
  'GNSS navigation message latency',
  ' [0, )  Seconds  ',
  'GNSS navigation message latency  4  float  [0, )  Seconds  '],
 ['4',
  'float',
  'Geoidal separation',
  ' ( , )  Meters  ',
  'Geoidal separation  4  float  ( , )  Meters  '],
 ['2',
  'ushort',
  'GNSS receiver type',
  ' See Table 12  N/A  ',
  'GNSS receiver type  2  ushort  See Table 12  N/A  '],
 ['4',
  'ulong',
  'GNSS status',
  ' GNSS summary status fields which depend on GNSS receiver type.  ',
  'GNSS status  4  ulong  GNSS summary status fields which depend on GNSS receiver type.  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Secondary_GNSS_status']=Secondary_GNSS_status
structures["see table 19"]=Secondary_GNSS_status
        
GROUP_ID_VALUES[11]='Secondary_GNSS_status'

GROUP_VALUE_IDS['Secondary_GNSS_status']=11

class Auxiliary_1_2GPS_status(BaseField):
    FieldTag="Auxiliary_1_2GPS_status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 12 or 13  N/A  ',
  'Group ID  2  ushort  12 or 13  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 72 + 20 x (number of channels)  Bytes  ',
  'Byte count  2  ushort  72 + 20 x (number of channels)  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['1',
  'byte',
  'Navigation solution status',
  ' See Table 9 (See Table 10 when using NAVCOM)  N/A  ',
  'Navigation solution status  1  byte  See Table 9 (See Table 10 when using NAVCOM)  N/A  '],
 ['1',
  'byte',
  'Number of SV Tracked',
  ' [0, 60]  N/A  ',
  'Number of SV Tracked  1  byte  [0, 60]  N/A  '],
 ['2',
  'ushort',
  'Channel status byte count',
  ' [0, 1200]  Bytes  ',
  'Channel status byte count  2  ushort  [0, 1200]  Bytes  '],
 ['variable',
  'see table 8',
  'Channel status',
  ' ',
  'Channel status  variable  See Table 8  '],
 ['4', 'float', 'HDOP', ' (0, )  N/A  ', 'HDOP  4  float  (0, )  N/A  '],
 ['4', 'float', 'VDOP', ' (0, )  N/A  ', 'VDOP  4  float  (0, )  N/A  '],
 ['4',
  'float',
  'DGPS correction latency',
  ' (0, )  Seconds  ',
  'DGPS correction latency  4  float  (0, )  Seconds  '],
 ['2',
  'ushort',
  'DGPS reference ID',
  ' [0, 1023]  N/A  ',
  'DGPS reference ID  2  ushort  [0, 1023]  N/A  '],
 ['4',
  'ulong',
  'GPS/UTC week number',
  ' [0, 9999) 0 if not available  Week  ',
  'GPS/UTC week number  4  ulong  [0, 9999) 0 if not available  Week  '],
 ['8',
  'double',
  'GPS time offset ',
  ' ( , 0]  Seconds  ',
  'GPS time offset (GPS time - UTC time)  8  double  ( , 0]  Seconds  '],
 ['4',
  'float',
  'GPS navigation message latency',
  ' [0, )  Seconds  ',
  'GPS navigation message latency  4  float  [0, )  Seconds  '],
 ['4',
  'float',
  'Geoidal separation',
  ' N/A  Meters  ',
  'Geoidal separation  4  float  N/A  Meters  '],
 ['2',
  'ushort',
  'NMEA messages Received',
  ' Bit (set) NMEA Message 0 GGA (GPS position) 1 GST (noise statistics) 2 GSV (satellites in view) 3 GSA (DOP & active SVs) 4-15 Reserved  ',
  'NMEA messages Received  2  ushort  Bit (set) NMEA Message 0 GGA (GPS position) 1 GST (noise statistics) 2 GSV (satellites in view) 3 GSA (DOP & active SVs) 4-15 Reserved  '],
 ['1',
  'byte',
  'Aux 1/2 in Use1',
  ' 0 Not in use 1 In Use  N/A  ',
  'Aux 1/2 in Use1  1  byte  0 Not in use 1 In Use  N/A  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Auxiliary_1_2GPS_status']=Auxiliary_1_2GPS_status
structures["see table 20"]=Auxiliary_1_2GPS_status
        
GROUP_ID_VALUES[12]='Auxiliary_1_2GPS_status'

GROUP_VALUE_IDS['Auxiliary_1_2GPS_status']=12

GROUP_ID_VALUES[13]='Auxiliary_1_2GPS_status'

GROUP_VALUE_IDS['Auxiliary_1_2GPS_status']=13

class Calibrated_installation_parameters(BaseField):
    FieldTag="Calibrated_installation_parameters"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 14  N/A  ', 'Group ID  2  ushort  14  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 128  Bytes  ',
  'Byte count  2  ushort  128  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['2',
  'ushort',
  'Calibration status',
  'See Table 22  ',
  'Calibration status  2  ushort See Table 22  '],
 ['4',
  'float',
  'Reference to Primary GPS X lever arm',
  ' ( , )  Meters  ',
  'Reference to Primary GPS X lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to Primary GPS Y lever arm',
  ' ( , )  Meters  ',
  'Reference to Primary GPS Y lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to Primary GPS Z lever arm',
  ' ( , )  Meters  ',
  'Reference to Primary GPS Z lever arm  4  float  ( , )  Meters  '],
 ['2',
  'ushort',
  'Reference to Primary GPS lever arm calibration FOM',
  ' [0, 100]  N/A  ',
  'Reference to Primary GPS lever arm calibration FOM  2  ushort  [0, 100]  N/A  '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS X lever arm',
  ' ( , )  Meters  ',
  'Reference to Auxiliary 1 GPS X lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS Y lever arm',
  ' ( , )  Meters  ',
  'Reference to Auxiliary 1 GPS Y lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS Z lever arm',
  ' ( , )  Meters  ',
  'Reference to Auxiliary 1 GPS Z lever arm  4  float  ( , )  Meters  '],
 ['2',
  'ushort',
  'Reference to Auxiliary 1 GPS lever arm calibration FOM',
  ' [0, 100]  N/A  ',
  'Reference to Auxiliary 1 GPS lever arm calibration FOM  2  ushort  [0, 100]  N/A  '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS X lever arm',
  ' ( , )  Meters  ',
  'Reference to Auxiliary 2 GPS X lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS Y lever arm',
  ' ( , )  Meters  ',
  'Reference to Auxiliary 2 GPS Y lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS Z lever arm',
  ' ( , )  Meters  ',
  'Reference to Auxiliary 2 GPS Z lever arm  4  float  ( , )  Meters  '],
 ['2',
  'ushort',
  'Reference to Auxiliary 2 GPS lever arm calibration FOM',
  ' [0, 100]  N/A  ',
  'Reference to Auxiliary 2 GPS lever arm calibration FOM  2  ushort  [0, 100]  N/A  '],
 ['4',
  'float',
  'Reference to DMI X lever arm',
  ' ( , )  Meters  ',
  'Reference to DMI X lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to DMI Y lever arm',
  ' ( , )  Meters  ',
  'Reference to DMI Y lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to DMI Z lever arm',
  ' ( , )  Meters  ',
  'Reference to DMI Z lever arm  4  float  ( , )  Meters  '],
 ['2',
  'ushort',
  'Reference to DMI lever arm calibration FOM',
  ' [0, 100]  N/A  ',
  'Reference to DMI lever arm calibration FOM  2  ushort  [0, 100]  N/A  '],
 ['4',
  'float',
  'DMI scale factor',
  ' ( , )  %  ',
  'DMI scale factor  4  float  ( , )  %  '],
 ['2',
  'ushort',
  'DMI scale factor calibration FOM',
  ' [0, 100]  N/A  ',
  'DMI scale factor calibration FOM  2  ushort  [0, 100]  N/A  '],
 ['4',
  'float',
  'Reference to DVS X lever arm',
  ' ( , )  Meters  ',
  'Reference to DVS X lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to DVS Y lever arm',
  ' ( , )  Meters  ',
  'Reference to DVS Y lever arm  4  float  ( , )  Meters  '],
 ['4',
  'float',
  'Reference to DVS Z lever arm',
  ' ( , )  meters  ',
  'Reference to DVS Z lever arm  4  float  ( , )  meters  '],
 ['2',
  'ushort',
  'Reference to DVS lever arm calibration FOM',
  ' [0, 100]  N/A  ',
  'Reference to DVS lever arm calibration FOM  2  ushort  [0, 100]  N/A  '],
 ['4',
  'float',
  'DVS scale factor',
  ' ( , )  %  ',
  'DVS scale factor  4  float  ( , )  %  '],
 ['2',
  'ushort',
  'DVS scale factor calibration FOM',
  ' [0, 100]  N/A  ',
  'DVS scale factor calibration FOM  2  ushort  [0, 100]  N/A  '],
 ['4',
  'float',
  'Primary to Secondary GPS X lever arm',
  ' ( , )  meters  ',
  'Primary to Secondary GPS X lever arm  4  float  ( , )  meters  '],
 ['4',
  'float',
  'Primary to Secondary GPS Y lever arm',
  ' ( , )  meters  ',
  'Primary to Secondary GPS Y lever arm  4  float  ( , )  meters  '],
 ['4',
  'float',
  'Primary to Secondary GPS Z lever arm',
  ' ( , )  meters  ',
  'Primary to Secondary GPS Z lever arm  4  float  ( , )  meters  '],
 ['2',
  'ushort',
  'Primary to Secondary GPS lever arm calibration FOM',
  ' [0, 100]  N/A  ',
  'Primary to Secondary GPS lever arm calibration FOM  2  ushort  [0, 100]  N/A  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Calibrated_installation_parameters']=Calibrated_installation_parameters
structures["see table 21"]=Calibrated_installation_parameters
        
GROUP_ID_VALUES[14]='Calibrated_installation_parameters'

GROUP_VALUE_IDS['Calibrated_installation_parameters']=14

class IIN_Calibration_Status(BaseField):
    FieldTag="IIN_Calibration_Status"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['IIN_Calibration_Status']=IIN_Calibration_Status
structures["see table 22"]=IIN_Calibration_Status
        
class User_Time_Status(BaseField):
    FieldTag="User_Time_Status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 17  N/A  ', 'Group ID  2  ushort  17  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 40  Bytes  ',
  'Byte count  2  ushort  40  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'ulong',
  'Number of Time Synch message rejections',
  ' [0, )  N/A  ',
  'Number of Time Synch message rejections  4  ulong  [0, )  N/A  '],
 ['4',
  'ulong',
  'Number of User Time resynchronizations',
  ' [0, )  N/A  ',
  'Number of User Time resynchronizations  4  ulong  [0, )  N/A  '],
 ['1',
  'byte',
  'User time valid',
  ' 1 or 0  N/A  ',
  'User time valid  1  byte  1 or 0  N/A  '],
 ['1',
  'byte',
  'Time Synch message received',
  ' 1 or 0  N/A  ',
  'Time Synch message received  1  byte  1 or 0  N/A  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['User_Time_Status']=User_Time_Status
structures["see table 23"]=User_Time_Status
        
GROUP_ID_VALUES[17]='User_Time_Status'

GROUP_VALUE_IDS['User_Time_Status']=17

class IIN_solution_status(BaseField):
    FieldTag="IIN_solution_status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 20  N/A  ', 'Group ID  2  ushort  20  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 60  Bytes  ',
  'Byte count  2  ushort  60  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['2',
  'ushort',
  'Number of satellites',
  ' [0, 12]  N/A  ',
  'Number of satellites  2  ushort  [0, 12]  N/A  '],
 ['4',
  'float',
  'A priori PDOP',
  ' [0, 999]  N/A  ',
  'A priori PDOP  4  float  [0, 999]  N/A  '],
 ['4',
  'float',
  'Baseline length',
  ' [0, )  Meters  ',
  'Baseline length  4  float  [0, )  Meters  '],
 ['2',
  'ushort',
  'IIN processing status',
  ' 0 Fixed Narrow Lane RTK 1 Fixed Wide Lane RTK 2 Float RTK 3 Code DGPS 4 RTCM DGPS 5 Autonomous (C/A) 6 GPS navigation solution 7 No solution  ',
  'IIN processing status  2  ushort  0 Fixed Narrow Lane RTK 1 Fixed Wide Lane RTK 2 Float RTK 3 Code DGPS 4 RTCM DGPS 5 Autonomous (C/A) 6 GPS navigation solution 7 No solution  '],
 ['12',
  'byte',
  'PRN assignment  12',
  ' Each byte contains 0-40 where 0 = unassigned PRN 1-40 = PRN assigned to channel  ',
  'PRN assignment  12  12 byte  Each byte contains 0-40 where 0 = unassigned PRN 1-40 = PRN assigned to channel  '],
 ['2',
  'ushort',
  'L1 cycle slip flag',
  ' Bits 0-11: (k-1)th bit set to 1 implies L1 cycle slip in channel k PRN. Example: Bit 3 set to 1 implies an L1 cycle slip in channel 4. Bits 12-15: not used.  ',
  'L1 cycle slip flag  2  ushort  Bits 0-11: (k-1)th bit set to 1 implies L1 cycle slip in channel k PRN. Example: Bit 3 set to 1 implies an L1 cycle slip in channel 4. Bits 12-15: not used.  '],
 ['2',
  'ushort',
  'L2 cycle slip flag',
  ' Bits 0-11: (k-1)th bit set to 1 implies L2 cycle slip in channel k PRN. Example: Bit 3 set to 1 implies an L2 cycle slip in channel 4. Bits 12-15: not used.  ',
  'L2 cycle slip flag  2  ushort  Bits 0-11: (k-1)th bit set to 1 implies L2 cycle slip in channel k PRN. Example: Bit 3 set to 1 implies an L2 cycle slip in channel 4. Bits 12-15: not used.  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['IIN_solution_status']=IIN_solution_status
structures["see table 24"]=IIN_solution_status
        
GROUP_ID_VALUES[20]='IIN_solution_status'

GROUP_VALUE_IDS['IIN_solution_status']=20

class Base_GPS_1_2_ModemStatus(BaseField):
    FieldTag="Base_GPS_1_2_ModemStatus"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 21 or 22  N/A  ',
  'Group ID  2  ushort  21 or 22  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 116  Bytes  ',
  'Byte count  2  ushort  116  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['16',
  'char',
  'Modem response',
  ' N/A  N/A  ',
  'Modem response  16  char  N/A  N/A  '],
 ['48',
  'char',
  'Connection status',
  ' N/A  N/A  ',
  'Connection status  48  char  N/A  N/A  '],
 ['4',
  'ulong',
  'Number of redials per disconnect',
  ' [0, )  N/A  ',
  'Number of redials per disconnect  4  ulong  [0, )  N/A  '],
 ['4',
  'ulong',
  'Maximum number of redials per disconnect',
  ' [0, )  N/A  ',
  'Maximum number of redials per disconnect  4  ulong  [0, )  N/A  '],
 ['4',
  'ulong',
  'Number of disconnects',
  ' [0, )  N/A  ',
  'Number of disconnects  4  ulong  [0, )  N/A  '],
 ['4',
  'ulong',
  'Data gap length',
  ' [0, )  N/A  ',
  'Data gap length  4  ulong  [0, )  N/A  '],
 ['4',
  'ulong',
  'Maximum data gap length',
  ' [0, )  N/A  ',
  'Maximum data gap length  4  ulong  [0, )  N/A  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Base_GPS_1_2_ModemStatus']=Base_GPS_1_2_ModemStatus
structures["see table 25"]=Base_GPS_1_2_ModemStatus
        
GROUP_ID_VALUES[21]='Base_GPS_1_2_ModemStatus'

GROUP_VALUE_IDS['Base_GPS_1_2_ModemStatus']=21

GROUP_ID_VALUES[22]='Base_GPS_1_2_ModemStatus'

GROUP_VALUE_IDS['Base_GPS_1_2_ModemStatus']=22

class Auxiliary_1_2GPS_raw_displaydata(BaseField):
    FieldTag="Auxiliary_1_2GPS_raw_displaydata"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 10007 or 10008  N/A  ',
  'Group ID  2  ushort  10007 or 10008  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' variable  Bytes  ',
  'Byte count  2  ushort  variable  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['6', 'byte', 'Reserved', ' N/A  N/A  ', 'Reserved  6  byte  N/A  N/A  '],
 ['2',
  'ushort',
  'Variable message byte count',
  ' [0, )  Bytes  ',
  'Variable message byte count  2  ushort  [0, )  Bytes  '],
 ['variable',
  'char',
  'Auxiliary GPS raw data',
  ' N/A  N/A  ',
  'Auxiliary GPS raw data  variable  char  N/A  N/A  '],
 ['0-3', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0-3  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Auxiliary_1_2GPS_raw_displaydata']=Auxiliary_1_2GPS_raw_displaydata
structures["see table 26"]=Auxiliary_1_2GPS_raw_displaydata
        
GROUP_ID_VALUES[10007]='Auxiliary_1_2GPS_raw_displaydata'

GROUP_VALUE_IDS['Auxiliary_1_2GPS_raw_displaydata']=10007

GROUP_ID_VALUES[10008]='Auxiliary_1_2GPS_raw_displaydata'

GROUP_VALUE_IDS['Auxiliary_1_2GPS_raw_displaydata']=10008

class GNSS_Receiver_MarineSTAR_Status(BaseField):
    FieldTag="GNSS_Receiver_MarineSTAR_Status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 29  N/A  ', 'Group ID  2  ushort  29  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 63  bytes  ',
  'Byte count  2  ushort  63  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['1',
  'byte',
  'MarineSTAR Status',
  ' 0 MarineSTAR off  1-2 Test Mode 3-4 Searching Mode 5 Tracking Initialization 6 Verifying Data Stream 7 Fully Tracking Satellite 4-255 Reserved  N/A  ',
  'MarineSTAR Status  1  byte  0 MarineSTAR off  1-2 Test Mode 3-4 Searching Mode 5 Tracking Initialization 6 Verifying Data Stream 7 Fully Tracking Satellite 4-255 Reserved  N/A  '],
 ['1',
  'byte',
  'Satellite ID',
  ' (0,100) Special ID 100 Custom satellite                          110 Automatically choose satellite  N/A  ',
  'Satellite ID  1  byte  (0,100) Special ID 100 Custom satellite                          110 Automatically choose satellite  N/A  '],
 ['4',
  'ulong',
  'Frequency of the satellite',
  ' Satellite Frequency  Hz  ',
  'Frequency of the satellite  4  ulong  Satellite Frequency  Hz  '],
 ['2',
  'ushort',
  'Bit Rate of the satellite',
  ' Data transfer rate  bit/sec  ',
  'Bit Rate of the satellite  2  ushort  Data transfer rate  bit/sec  '],
 ['1',
  'byte',
  'HP/XP -MarineSTAR library active flag',
  ' 0 Not Active 1 Active  N/A  ',
  'HP/XP -MarineSTAR library active flag  1  byte  0 Not Active 1 Active  N/A  '],
 ['1',
  'byte',
  'HP/XP -Engine mode used by the library',
  ' 1 HP  2 XP 3 G2 4 HP+G2  5 HP+XP  N/A  ',
  'HP/XP -Engine mode used by the library  1  byte  1 HP  2 XP 3 G2 4 HP+G2  5 HP+XP  N/A  '],
 ['2',
  'ushort',
  'HP/XP Subscription starting date - year',
  ' 0 for no valid subscription  N/A  ',
  'HP/XP Subscription starting date - year  2  ushort  0 for no valid subscription  N/A  '],
 ['1',
  'byte',
  'Subscription starting date - month',
  ' 1-12 or 0 for no valid subscription  N/A  ',
  'Subscription starting date - month  1  byte  1-12 or 0 for no valid subscription  N/A  '],
 ['1',
  'byte',
  'Subscription starting date - day',
  ' 1-31 or 0 for no valid subscription  N/A  ',
  'Subscription starting date - day  1  byte  1-31 or 0 for no valid subscription  N/A  '],
 ['2',
  'ushort',
  'HP/XP Subscription expiration date - year',
  ' 0 for no valid subscription  N/A  ',
  'HP/XP Subscription expiration date - year  2  ushort  0 for no valid subscription  N/A  '],
 ['1',
  'byte',
  'Subscription expiration date - month',
  ' 1-12 or 0 for no valid subscription  N/A  ',
  'Subscription expiration date - month  1  byte  1-12 or 0 for no valid subscription  N/A  '],
 ['1',
  'byte',
  'Subscription expiration date - day',
  ' 1-31 or 0 for no valid subscription  N/A  ',
  'Subscription expiration date - day  1  byte  1-31 or 0 for no valid subscription  N/A  '],
 ['1',
  'byte',
  'Subscribed engine mode',
  ' 1 HP  2 XP 3 G2 4 HP+G2  5 HP+XP  N/A  ',
  'Subscribed engine mode  1  byte  1 HP  2 XP 3 G2 4 HP+G2  5 HP+XP  N/A  '],
 ['4',
  'byte',
  'Reserved',
  ' Reserved  N/A  ',
  'Reserved  4  byte  Reserved  N/A  '],
 ['4',
  'byte',
  'Reserved',
  ' Reserved  N/A  ',
  'Reserved  4  byte  Reserved  N/A  '],
 ['1',
  'byte',
  'HP/XP status -Receiver Operation Mode',
  ' 1 Static 2 kinematic   N/A  ',
  'HP/XP status -Receiver Operation Mode  1  byte  1 Static 2 kinematic   N/A  '],
 ['1',
  'byte',
  'HP/XP status -MarineSTAR Operation Mode',
  ' 0 Kinematic 1 Static 2 MarineSTAR not ready  N/A  ',
  'HP/XP status -MarineSTAR Operation Mode  1  byte  0 Kinematic 1 Static 2 MarineSTAR not ready  N/A  '],
 ['1',
  'byte',
  'Reserved',
  ' Reserved  N/A  ',
  'Reserved  1  byte  Reserved  N/A  '],
 ['1',
  'byte',
  'Reserved',
  ' Reserved  N/A  ',
  'Reserved  1  byte  Reserved  N/A  '],
 ['1',
  'byte',
  'Reserved',
  ' Reserved  N/A  ',
  'Reserved  1  byte  Reserved  N/A  '],
 ['1',
  'byte',
  'Satellite SNR',
  ' Satellite carrier-to-noise ratio  dBHz  ',
  'Satellite SNR  1  byte  Satellite carrier-to-noise ratio  dBHz  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GNSS_Receiver_MarineSTAR_Status']=GNSS_Receiver_MarineSTAR_Status
structures["see table 27"]=GNSS_Receiver_MarineSTAR_Status
        
GROUP_ID_VALUES[29]='GNSS_Receiver_MarineSTAR_Status'

GROUP_VALUE_IDS['GNSS_Receiver_MarineSTAR_Status']=29

class Versions_and_statistics(BaseField):
    FieldTag="Versions_and_statistics"
    sdf_list = [['4',
  'char',
  'Group Start',
  ' $GRP  N/A  ',
  'Group Start  4  Char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 99  N/A  ', 'Group ID  2  Ushort  99  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 412  Bytes  ',
  'Byte Count  2  Ushort  412  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' Table 3  ',
  'Time/Distance Fields  26  See Table 3  Table 3  '],
 ['120',
  'char',
  'System version',
  ' Product - Model, Version, Serial Number, Hardware version, Software release version - Date, ICD release version, Operating system version, IMU type, Primary GPS type (Table 12), Secondary GPS type (Table 12), DMI type, Gimbal type, ZVI type, IMU housing type ..... Example: MV-320,VER5,S/N5050,HW1.05-10, SW06.00-Jan3/11,ICD04.10, OS6.4.1,IMU7,PGPS16,SGPS16, DMI0,GIM0,ZVI0,IHT101  ',
  'System version  120  Char  Product - Model, Version, Serial Number, Hardware version, Software release version - Date, ICD release version, Operating system version, IMU type, Primary GPS type (Table 12), Secondary GPS type (Table 12), DMI type, Gimbal type, ZVI type, IMU housing type ..... Example: MV-320,VER5,S/N5050,HW1.05-10, SW06.00-Jan3/11,ICD04.10, OS6.4.1,IMU7,PGPS16,SGPS16, DMI0,GIM0,ZVI0,IHT101  '],
 ['80',
  'char',
  'Primary GPS version',
  ' Available information is displayed, eg: . Model number . Serial number . Hardware configuration version . Software release version  ',
  'Primary GPS version  80  char  Available information is displayed, eg: . Model number . Serial number . Hardware configuration version . Software release version  '],
 ['80',
  'char',
  'Secondary GPS version',
  ' Available information is displayed, eg: . Model number . Serial number . Hardware configuration version . Software release version . Release date  ',
  'Secondary GPS version  80  Char  Available information is displayed, eg: . Model number . Serial number . Hardware configuration version . Software release version . Release date  '],
 ['4',
  'float',
  'Total hours',
  ' [0, ) 0.1 hour resolution  Hours  ',
  'Total hours  4  float  [0, ) 0.1 hour resolution  Hours  '],
 ['4',
  'ulong',
  'Number of runs',
  ' [0, )  N/A  ',
  'Number of runs  4  ulong  [0, )  N/A  '],
 ['4',
  'float',
  'Average length of run',
  ' [0, ) 0.1 hour resolution  Hours  ',
  'Average length of run  4  float  [0, ) 0.1 hour resolution  Hours  '],
 ['4',
  'float',
  'Longest run',
  ' [0, ) 0.1 hour resolution  Hours  ',
  'Longest run  4  float  [0, ) 0.1 hour resolution  Hours  '],
 ['4',
  'float',
  'Current run',
  ' [0, ) 0.1 hour resolution  Hours  ',
  'Current run  4  float  [0, ) 0.1 hour resolution  Hours  '],
 ['80',
  'char',
  'Options',
  ' [option mnemonic-expiry time] [,option mnemonic-expiry time] ...  N/A  ',
  'Options  80  Char  [option mnemonic-expiry time] [,option mnemonic-expiry time] ...  N/A  '],
 ['2', 'short', 'Pad', ' 0  N/A  ', 'Pad  2  short  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group End', ' $#  N/A  ', 'Group End  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Versions_and_statistics']=Versions_and_statistics
structures["see table 28"]=Versions_and_statistics
        
GROUP_ID_VALUES[99]='Versions_and_statistics'

GROUP_VALUE_IDS['Versions_and_statistics']=99

class Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics(BaseField):
    FieldTag="Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 102 or 103  N/A  ',
  'Group ID  2  ushort  102 or 103  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 128  Bytes  ',
  'Byte count  2  ushort  128  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['8',
  'double',
  'Latitude',
  ' (-90, 90]  Deg  ',
  'Latitude  8  double  (-90, 90]  Deg  '],
 ['8',
  'double',
  'Longitude',
  ' (-180, 180]  Deg  ',
  'Longitude  8  double  (-180, 180]  Deg  '],
 ['8', 'double', 'Altitude', ' ( , )  M  ', 'Altitude  8  double  ( , )  M  '],
 ['4',
  'float',
  'Along track velocity',
  ' ( , )  m/s  ',
  'Along track velocity  4  float  ( , )  m/s  '],
 ['4',
  'float',
  'Across track velocity',
  ' ( , )  m/s  ',
  'Across track velocity  4  float  ( , )  m/s  '],
 ['4',
  'float',
  'Down velocity',
  ' ( , )  m/s  ',
  'Down velocity  4  float  ( , )  m/s  '],
 ['8',
  'double',
  'Roll',
  ' (-180, 180]  Deg  ',
  'Roll  8  double  (-180, 180]  Deg  '],
 ['8',
  'double',
  'Pitch',
  ' (-90, 90]  Deg  ',
  'Pitch  8  double  (-90, 90]  Deg  '],
 ['8',
  'double',
  'Heading',
  ' [0, 360)  Deg  ',
  'Heading  8  double  [0, 360)  Deg  '],
 ['8',
  'double',
  'Wander angle',
  ' (-180, 180]  Deg  ',
  'Wander angle  8  double  (-180, 180]  Deg  '],
 ['4', 'float', 'Heave1', ' ( , )  M  ', 'Heave1  4  float  ( , )  M  '],
 ['4',
  'float',
  'Angular rate about longitudinal axis',
  ' ( , )  deg/s  ',
  'Angular rate about longitudinal axis  4  float  ( , )  deg/s  '],
 ['4',
  'float',
  'Angular rate about transverse axis',
  ' ( , )  deg/s  ',
  'Angular rate about transverse axis  4  float  ( , )  deg/s  '],
 ['4',
  'float',
  'Angular rate about down axis',
  ' ( , )  deg/s  ',
  'Angular rate about down axis  4  float  ( , )  deg/s  '],
 ['4',
  'float',
  'Longitudinal acceleration',
  ' ( , )  m/s2  ',
  'Longitudinal acceleration  4  float  ( , )  m/s2  '],
 ['4',
  'float',
  'Transverse acceleration',
  ' ( , )  m/s2  ',
  'Transverse acceleration  4  float  ( , )  m/s2  '],
 ['4',
  'float',
  'Down acceleration',
  ' ( , )  m/s2  ',
  'Down acceleration  4  float  ( , )  m/s2  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics']=Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics
structures["see table 29"]=Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics
        
GROUP_ID_VALUES[102]='Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics'

GROUP_VALUE_IDS['Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics']=102

GROUP_ID_VALUES[103]='Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics'

GROUP_VALUE_IDS['Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics']=103

class Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics(BaseField):
    FieldTag="Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 104 or 105  N/A  ',
  'Group ID  2  ushort  104 or 105  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 68  Bytes  ',
  'Byte count  2  ushort  68  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'float',
  'N position RMS',
  ' [0, )  M  ',
  'N position RMS  4  float  [0, )  M  '],
 ['4',
  'float',
  'E position RMS',
  ' [0, )  M  ',
  'E position RMS  4  float  [0, )  M  '],
 ['4',
  'float',
  'D position RMS',
  ' [0, )  M  ',
  'D position RMS  4  float  [0, )  M  '],
 ['4',
  'float',
  'Along track velocity RMS error',
  ' [0, )  m/s  ',
  'Along track velocity RMS error  4  float  [0, )  m/s  '],
 ['4',
  'float',
  'Across track velocity RMS error',
  ' [0, )  m/s  ',
  'Across track velocity RMS error  4  float  [0, )  m/s  '],
 ['4',
  'float',
  'Down velocity RMS error',
  ' [0, )  m/s  ',
  'Down velocity RMS error  4  float  [0, )  m/s  '],
 ['4',
  'float',
  'Roll RMS error',
  ' [0, )  Deg  ',
  'Roll RMS error  4  float  [0, )  Deg  '],
 ['4',
  'float',
  'Pitch RMS error',
  ' [0, )  Deg  ',
  'Pitch RMS error  4  float  [0, )  Deg  '],
 ['4',
  'float',
  'Heading RMS error',
  ' [0, )  Deg  ',
  'Heading RMS error  4  float  [0, )  Deg  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics']=Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics
structures["see table 30"]=Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics
        
GROUP_ID_VALUES[104]='Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics'

GROUP_VALUE_IDS['Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics']=104

GROUP_ID_VALUES[105]='Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics'

GROUP_VALUE_IDS['Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics']=105

class MVGeneral_Status_FDIR(BaseField):
    FieldTag="MVGeneral_Status_FDIR"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 110  N/A  ', 'Group ID  2  ushort  110  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 36  Bytes  ',
  'Byte count  2  ushort  36  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['2',
  'ushort',
  'General Status',
  ' User logged in reserved TrueZ Active TrueZ Ready TrueZ In Use Reserved  bit 0: set bit 1 to 9 bit 10: set bit 11: set bit 12: set bit 13 to 15  ',
  'General Status  2  ushort  User logged in reserved TrueZ Active TrueZ Ready TrueZ In Use Reserved  bit 0: set bit 1 to 9 bit 10: set bit 11: set bit 12: set bit 13 to 15  '],
 ['2',
  'ushort',
  'TrueZ time remaining',
  ' [0, )  seconds  ',
  'TrueZ time remaining  2  ushort  [0, )  seconds  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['MVGeneral_Status_FDIR']=MVGeneral_Status_FDIR
structures["see table 31"]=MVGeneral_Status_FDIR
        
GROUP_ID_VALUES[110]='MVGeneral_Status_FDIR'

GROUP_VALUE_IDS['MVGeneral_Status_FDIR']=110

class Heave_True_Heave_Data(BaseField):
    FieldTag="Heave_True_Heave_Data"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 111  N/A  ', 'Group ID  2  ushort  111  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 76  Bytes  ',
  'Byte count  2  ushort  76  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'float',
  'True Heave',
  ' ( , )  M  ',
  'True Heave  4  float  ( , )  M  '],
 ['4',
  'float',
  'True Heave RMS',
  ' [0, )  M  ',
  'True Heave RMS  4  float  [0, )  M  '],
 ['4',
  'ulong',
  'Status',
  ' True Heave Valid Real-time Heave Valid reserved  bit 0: set bit 1: set bit 2 to 31  ',
  'Status  4  ulong  True Heave Valid Real-time Heave Valid reserved  bit 0: set bit 1: set bit 2 to 31  '],
 ['4', 'float', 'Heave', ' ( , )  M  ', 'Heave  4  float  ( , )  M  '],
 ['4', 'float', 'Heave RMS', ' [0, )  M  ', 'Heave RMS  4  float  [0, )  M  '],
 ['8',
  'double',
  'Heave Time 1',
  ' N/A  Sec  ',
  'Heave Time 1  8  double  N/A  Sec  '],
 ['8',
  'double',
  'Heave Time 2',
  ' N/A  Sec  ',
  'Heave Time 2  8  double  N/A  Sec  '],
 ['4',
  'ulong',
  'Rejected IMU Data Count',
  ' [0, )  N/A  ',
  'Rejected IMU Data Count  4  ulong  [0, )  N/A  '],
 ['4',
  'ulong',
  'Out of Range IMU Data Count',
  ' [0, )  N/A  ',
  'Out of Range IMU Data Count  4  ulong  [0, )  N/A  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Heave_True_Heave_Data']=Heave_True_Heave_Data
structures["see table 32"]=Heave_True_Heave_Data
        
GROUP_ID_VALUES[111]='Heave_True_Heave_Data'

GROUP_VALUE_IDS['Heave_True_Heave_Data']=111

class NMEA_Strings(BaseField):
    FieldTag="NMEA_Strings"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 112  N/A  ', 'Group ID  2  ushort  112  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' variable  Bytes  ',
  'Byte count  2  ushort  variable  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['2',
  'ushort',
  'Variable group byte count',
  ' [0, )  N/A  ',
  'Variable group byte count  2  ushort  [0, )  N/A  '],
 ['variable',
  'char',
  'NMEA strings',
  ' N/A  N/A  ',
  'NMEA strings  variable  char  N/A  N/A  '],
 ['0-3', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0-3  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['NMEA_Strings']=NMEA_Strings
structures["see table 33"]=NMEA_Strings
        
GROUP_ID_VALUES[112]='NMEA_Strings'

GROUP_VALUE_IDS['NMEA_Strings']=112

class Heave_True_Heave_Performance_Metrics(BaseField):
    FieldTag="Heave_True_Heave_Performance_Metrics"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 113  N/A  ', 'Group ID  2  ushort  113  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 68  Bytes  ',
  'Byte count  2  ushort  68  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['8',
  'double',
  'Heave Time 1',
  ' N/A  Sec  ',
  'Heave Time 1  8  double  N/A  Sec  '],
 ['8',
  'double',
  'Quality Control 1',
  ' N/A  N/A  ',
  'Quality Control 1  8  double  N/A  N/A  '],
 ['8',
  'double',
  'Quality Control 2',
  ' N/A  N/A  ',
  'Quality Control 2  8  double  N/A  N/A  '],
 ['8',
  'double',
  'Quality Control 3',
  ' N/A  N/A  ',
  'Quality Control 3  8  double  N/A  N/A  '],
 ['4',
  'ulong',
  'Status',
  ' Quality Control 1 Valid Quality Control 2 Valid Quality Control 3 Valid Reserved  bit 0: set bit 1: set bit 2: set bit 3 to 31  ',
  'Status  4  ulong  Quality Control 1 Valid Quality Control 2 Valid Quality Control 3 Valid Reserved  bit 0: set bit 1: set bit 2: set bit 3 to 31  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Heave_True_Heave_Performance_Metrics']=Heave_True_Heave_Performance_Metrics
structures["see table 34"]=Heave_True_Heave_Performance_Metrics
        
GROUP_ID_VALUES[113]='Heave_True_Heave_Performance_Metrics'

GROUP_VALUE_IDS['Heave_True_Heave_Performance_Metrics']=113

class TrueZ_TrueTide_Data(BaseField):
    FieldTag="TrueZ_TrueTide_Data"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 114  N/A  ', 'Group ID  2  ushort  114  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 76  Bytes  ',
  'Byte count  2  ushort  76  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'float',
  'Delayed TrueZ',
  ' ( , )  M  ',
  'Delayed TrueZ  4  float  ( , )  M  '],
 ['4',
  'float',
  'Delayed TrueZ RMS',
  ' [0, )  M  ',
  'Delayed TrueZ RMS  4  float  [0, )  M  '],
 ['4',
  'float',
  'Delayed TrueTide',
  ' ( , )  M  ',
  'Delayed TrueTide  4  float  ( , )  M  '],
 ['4',
  'ulong',
  'Status',
  ' Delayed TrueZ Valid bit 0: set Real-time TrueZ Valid bit 1: set Reserved bit 2 to 31  ',
  'Status  4  ulong  Delayed TrueZ Valid bit 0: set Real-time TrueZ Valid bit 1: set Reserved bit 2 to 31  '],
 ['4', 'float', 'TrueZ', ' ( , )  M  ', 'TrueZ  4  float  ( , )  M  '],
 ['4', 'float', 'TrueZ RMS', ' [0, )  M  ', 'TrueZ RMS  4  float  [0, )  M  '],
 ['4', 'float', 'TrueTide', ' ( , )  M  ', 'TrueTide  4  float  ( , )  M  '],
 ['8',
  'double',
  'TrueZ Time 1',
  ' N/A  Sec  ',
  'TrueZ Time 1  8  double  N/A  Sec  '],
 ['8',
  'double',
  'TrueZ Time 2',
  ' N/A  Sec  ',
  'TrueZ Time 2  8  double  N/A  Sec  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['TrueZ_TrueTide_Data']=TrueZ_TrueTide_Data
structures["see table 35"]=TrueZ_TrueTide_Data
        
GROUP_ID_VALUES[114]='TrueZ_TrueTide_Data'

GROUP_VALUE_IDS['TrueZ_TrueTide_Data']=114

class Primary_GPS_data_stream(BaseField):
    FieldTag="Primary_GPS_data_stream"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 10001  N/A  ',
  'Group ID  2  ushort  10001  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' variable  Bytes  ',
  'Byte count  2  ushort  variable  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['2',
  'ushort',
  'GPS receiver type',
  ' See Table 12  N/A  ',
  'GPS receiver type  2  ushort  See Table 12  N/A  '],
 ['4', 'long', 'Reserved', ' N/A  N/A  ', 'Reserved  4  long  N/A  N/A  '],
 ['2',
  'ushort',
  'Variable message byte count',
  ' [0, )  Bytes  ',
  'Variable message byte count  2  ushort  [0, )  Bytes  '],
 ['variable',
  'char',
  'GPS Receiver raw data',
  ' N/A  N/A  ',
  'GPS Receiver raw data  variable  char  N/A  N/A  '],
 ['0-3', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0-3  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Primary_GPS_data_stream']=Primary_GPS_data_stream
structures["see table 36"]=Primary_GPS_data_stream
        
GROUP_ID_VALUES[10001]='Primary_GPS_data_stream'

GROUP_VALUE_IDS['Primary_GPS_data_stream']=10001

class Raw_IMU_data(BaseField):
    FieldTag="Raw_IMU_data"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 10002  N/A  ',
  'Group ID  2  ushort  10002  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' Variable  Bytes  ',
  'Byte count  2  ushort  Variable  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['6',
  'char',
  'IMU header',
  ' $IMUnn where nn identifies the IMU type.  ',
  'IMU header  6  char  $IMUnn where nn identifies the IMU type.  '],
 ['2',
  'ushort',
  'Variable message byte count',
  ' [0, )  Bytes  ',
  'Variable message byte count  2  ushort  [0, )  Bytes  '],
 ['variable',
  'byte',
  'IMU raw data',
  ' N/A  N/A  ',
  'IMU raw data  variable  byte  N/A  N/A  '],
 ['2',
  'short',
  'Data Checksum',
  ' N/A  N/A  ',
  'Data Checksum  2  short  N/A  N/A  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Raw_IMU_data']=Raw_IMU_data
structures["see table 37"]=Raw_IMU_data
        
GROUP_ID_VALUES[10002]='Raw_IMU_data'

GROUP_VALUE_IDS['Raw_IMU_data']=10002

class Raw_PPS(BaseField):
    FieldTag="Raw_PPS"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  Char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 10003  N/A  ',
  'Group ID  2  Ushort  10003  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 36  Bytes  ',
  'Byte count  2  Ushort  36  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['4',
  'ulong',
  'PPS pulse count',
  ' [0, )  N/A  ',
  'PPS pulse count  4  Ulong  [0, )  N/A  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  Byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  Ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  Char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Raw_PPS']=Raw_PPS
structures["see table 38"]=Raw_PPS
        
GROUP_ID_VALUES[10003]='Raw_PPS'

GROUP_VALUE_IDS['Raw_PPS']=10003

class Auxiliary_1_2_GPS_data_streams(BaseField):
    FieldTag="Auxiliary_1_2_GPS_data_streams"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 10007 or 10008  N/A  ',
  'Group ID  2  ushort  10007 or 10008  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' variable  Bytes  ',
  'Byte count  2  ushort  variable  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['2', 'byte', 'reserved', ' N/A  N/A  ', 'reserved  2  byte  N/A  N/A  '],
 ['4', 'long', 'reserved', ' N/A  N/A  ', 'reserved  4  long  N/A  N/A  '],
 ['2',
  'ushort',
  'Variable message byte count',
  ' [0, )  Bytes  ',
  'Variable message byte count  2  ushort  [0, )  Bytes  '],
 ['variable',
  'char',
  'Auxiliary GPS raw data',
  ' N/A  N/A  ',
  'Auxiliary GPS raw data  variable  char  N/A  N/A  '],
 ['0-3', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0-3  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Auxiliary_1_2_GPS_data_streams']=Auxiliary_1_2_GPS_data_streams
structures["see table 39"]=Auxiliary_1_2_GPS_data_streams
        
GROUP_ID_VALUES[10007]='Auxiliary_1_2_GPS_data_streams'

GROUP_VALUE_IDS['Auxiliary_1_2_GPS_data_streams']=10007

GROUP_ID_VALUES[10008]='Auxiliary_1_2_GPS_data_streams'

GROUP_VALUE_IDS['Auxiliary_1_2_GPS_data_streams']=10008

class Secondary_GPS_data_stream(BaseField):
    FieldTag="Secondary_GPS_data_stream"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 10009  N/A  ',
  'Group ID  2  ushort  10009  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' Variable  Bytes  ',
  'Byte count  2  ushort  Variable  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['2',
  'ushort',
  'GPS receiver type',
  ' See Table 12  N/A  ',
  'GPS receiver type  2  ushort  See Table 12  N/A  '],
 ['4', 'byte', 'Reserved', ' N/A  N/A  ', 'Reserved  4  byte  N/A  N/A  '],
 ['2',
  'ushort',
  'Variable message byte count',
  ' [0, )  Bytes  ',
  'Variable message byte count  2  ushort  [0, )  Bytes  '],
 ['variable',
  'char',
  'GPS Receiver Message',
  ' N/A  N/A  ',
  'GPS Receiver Message  variable  char  N/A  N/A  '],
 ['0-3', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0-3  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Secondary_GPS_data_stream']=Secondary_GPS_data_stream
structures["see table 40"]=Secondary_GPS_data_stream
        
GROUP_ID_VALUES[10009]='Secondary_GPS_data_stream'

GROUP_VALUE_IDS['Secondary_GPS_data_stream']=10009

class Base_GPS_1_2_data_stream(BaseField):
    FieldTag="Base_GPS_1_2_data_stream"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' 10011 or 10012  N/A  ',
  'Group ID  2  ushort  10011 or 10012  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' variable  Bytes  ',
  'Byte count  2  ushort  variable  Bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['6', 'byte', 'reserved', ' N/A  N/A  ', 'reserved  6  byte  N/A  N/A  '],
 ['2',
  'ushort',
  'Variable message byte count',
  ' [0, )  Bytes  ',
  'Variable message byte count  2  ushort  [0, )  Bytes  '],
 ['variable',
  'byte',
  'Base GPS raw data',
  ' N/A  N/A  ',
  'Base GPS raw data  variable  byte  N/A  N/A  '],
 ['0-3', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0-3  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Base_GPS_1_2_data_stream']=Base_GPS_1_2_data_stream
structures["see table 41"]=Base_GPS_1_2_data_stream
        
GROUP_ID_VALUES[10011]='Base_GPS_1_2_data_stream'

GROUP_VALUE_IDS['Base_GPS_1_2_data_stream']=10011

GROUP_ID_VALUES[10012]='Base_GPS_1_2_data_stream'

GROUP_VALUE_IDS['Base_GPS_1_2_data_stream']=10012

class Control_messages_output_data_rates(BaseField):
    FieldTag="Control_messages_output_data_rates"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Control_messages_output_data_rates']=Control_messages_output_data_rates
structures["see table 42"]=Control_messages_output_data_rates
        
class format(BaseField):
    FieldTag="format"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' Message dependent  N/A  ',
  'Message ID  2  ushort  Message dependent  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' Message dependent  N/A  ',
  'Byte count  2  ushort  Message dependent  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['format']=format
structures["see table 43"]=format
        
class Acknowledge(BaseField):
    FieldTag="Acknowledge"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2', 'ushort', 'Message ID', ' 0  N/A  ', 'Message ID  2  ushort  0  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 44  N/A  ',
  'Byte count  2  ushort  44  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Transaction number sent by client.  N/A  ',
  'Transaction number  2  ushort  Transaction number sent by client.  N/A  '],
 ['2',
  'ushort',
  'ID of received message',
  ' Any valid message number.  N/A  ',
  'ID of received message  2  ushort  Any valid message number.  N/A  '],
 ['2',
  'ushort',
  'Response code',
  ' See Table 45  N/A  ',
  'Response code  2  ushort  See Table 45  N/A  '],
 ['1',
  'byte',
  'New parameters status',
  ' Value Message 0 No change in parameters 1 Some parameters changed 2-255 Reserved  N/A  ',
  'New parameters status  1  byte  Value Message 0 No change in parameters 1 Some parameters changed 2-255 Reserved  N/A  '],
 ['32',
  'char',
  'Parameter name',
  ' Name of rejected parameter on parameter error only  N/A  ',
  'Parameter name  32  char  Name of rejected parameter on parameter error only  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Acknowledge']=Acknowledge
structures["see table 44"]=Acknowledge
        
MESSAGE_ID_VALUES[0]='Acknowledge'

MESSAGE_VALUE_IDS['Acknowledge']=0

class response_codes(BaseField):
    FieldTag="response_codes"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['response_codes']=response_codes
structures["see table 45"]=response_codes
        
class General_Installation_and_Processing_Parameters(BaseField):
    FieldTag="General_Installation_and_Processing_Parameters"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 20  N/A  ',
  'Message ID  2  ushort  20  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 84  N/A  ',
  'Byte count  2  ushort  84  N/A  '],
 ['2',
  'ushort',
  'Transaction Number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction Number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Time types',
  ' Value (bits 0-3) Time type 1 0 POS time 1 GPS time 2 UTC time (default) 3-16 Reserved Value (bits 4-7) Time type 2 0 POS time (default) 1 GPS time 2 UTC time 3 User time 4-16 Reserved  ',
  'Time types  1  byte  Value (bits 0-3) Time type 1 0 POS time 1 GPS time 2 UTC time (default) 3-16 Reserved Value (bits 4-7) Time type 2 0 POS time (default) 1 GPS time 2 UTC time 3 User time 4-16 Reserved  '],
 ['1',
  'byte',
  'Distance type',
  ' Value State 0 N/A 1 POS distance (default) 2 DMI distance 3-255 Reserved  ',
  'Distance type  1  byte  Value State 0 N/A 1 POS distance (default) 2 DMI distance 3-255 Reserved  '],
 ['1',
  'byte',
  'Select/deselect AutoStart',
  ' Value State 0 AutoStart disabled (default) 1 AutoStart enabled 2-255 Reserved  ',
  'Select/deselect AutoStart  1  byte  Value State 0 AutoStart disabled (default) 1 AutoStart enabled 2-255 Reserved  '],
 ['4',
  'float',
  'Reference to IMU X lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to IMU X lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to IMU',
  ' ( , ) default = 0  meters  ',
  'Reference to IMU  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to IMU Z lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to IMU Z lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Primary GPS X lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Primary GPS X lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Primary GPS Y lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Primary GPS Y lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Primary GPS Z lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Primary GPS Z lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS X lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Auxiliary 1 GPS X lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS Y lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Auxiliary 1 GPS Y lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS Z lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Auxiliary 1 GPS Z lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS X lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Auxiliary 2 GPS X lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS Y lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Auxiliary 2 GPS Y lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS Z lever arm',
  ' ( , ) default = 0  meters  ',
  'Reference to Auxiliary 2 GPS Z lever arm  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'X IMU wrt Reference frame mounting angle',
  ' [-180, +180] default = 0  degrees  ',
  'X IMU wrt Reference frame mounting angle  4  float  [-180, +180] default = 0  degrees  '],
 ['4',
  'float',
  'Y IMU wrt Reference frame mounting angle',
  ' [-180, +180] default = 0  degrees  ',
  'Y IMU wrt Reference frame mounting angle  4  float  [-180, +180] default = 0  degrees  '],
 ['4',
  'float',
  'Z IMU wrt Reference frame mounting angle',
  ' [-180, +180] default = 0  degrees  ',
  'Z IMU wrt Reference frame mounting angle  4  float  [-180, +180] default = 0  degrees  '],
 ['4',
  'float',
  'X Reference frame wrt Vessel frame mounting angle',
  ' [-180, +180] default = 0  degrees  ',
  'X Reference frame wrt Vessel frame mounting angle  4  float  [-180, +180] default = 0  degrees  '],
 ['4',
  'float',
  'Y Reference frame wrt Vessel frame mounting angle',
  ' [-180, +180] default = 0  degrees  ',
  'Y Reference frame wrt Vessel frame mounting angle  4  float  [-180, +180] default = 0  degrees  '],
 ['4',
  'float',
  'Z Reference frame wrt Vessel frame mounting angle',
  ' [-180, +180] default = 0  degrees  ',
  'Z Reference frame wrt Vessel frame mounting angle  4  float  [-180, +180] default = 0  degrees  '],
 ['1',
  'byte',
  'Multipath environment',
  ' Value Multipath  ',
  'Multipath environment  1  byte  Value Multipath  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['General_Installation_and_Processing_Parameters']=General_Installation_and_Processing_Parameters
structures["see table 46"]=General_Installation_and_Processing_Parameters
        
MESSAGE_ID_VALUES[20]='General_Installation_and_Processing_Parameters'

MESSAGE_VALUE_IDS['General_Installation_and_Processing_Parameters']=20

class GAMS_installation_parameters(BaseField):
    FieldTag="GAMS_installation_parameters"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 21  N/A  ',
  'Message ID  2  ushort  21  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 36  N/A  ',
  'Byte count  2  ushort  36  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['4',
  'float',
  'Primary-secondary antenna separation ',
  ' [0, ) default = 0  Meters  ',
  'Primary-secondary antenna separation (deprecated)  4  float  [0, ) default = 0  Meters  '],
 ['4',
  'float',
  'Baseline vector X component',
  ' ( , ) default = 0  Meters  ',
  'Baseline vector X component  4  float  ( , ) default = 0  Meters  '],
 ['4',
  'float',
  'Baseline vector Y component',
  ' ( , ) default = 0  meters  ',
  'Baseline vector Y component  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Baseline vector Z component',
  ' ( , ) default = 0  meters  ',
  'Baseline vector Z component  4  float  ( , ) default = 0  meters  '],
 ['4',
  'float',
  'Maximum heading error RMS for calibration',
  ' [0, ) default = 3  degrees  ',
  'Maximum heading error RMS for calibration  4  float  [0, ) default = 3  degrees  '],
 ['4',
  'float',
  'Heading correction',
  ' ( , ) default = 0  degrees  ',
  'Heading correction  4  float  ( , ) default = 0  degrees  '],
 ['4',
  'float',
  'Baseline vector standard deviation',
  ' (0, ) default = 10  meters  ',
  'Baseline vector standard deviation  4  float  (0, ) default = 10  meters  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GAMS_installation_parameters']=GAMS_installation_parameters
structures["see table 47"]=GAMS_installation_parameters
        
MESSAGE_ID_VALUES[21]='GAMS_installation_parameters'

MESSAGE_VALUE_IDS['GAMS_installation_parameters']=21

class User_accuracy_specifications(BaseField):
    FieldTag="User_accuracy_specifications"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 24  N/A  ',
  'Message ID  2  ushort  24  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 24  N/A  ',
  'Byte count  2  ushort  24  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: 65533 to 65535  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: 65533 to 65535  N/A  '],
 ['4',
  'float',
  'User attitude accuracy',
  ' (0, )  default = 0.05  degrees  ',
  'User attitude accuracy  4  float  (0, )  default = 0.05  degrees  '],
 ['4',
  'float',
  'User heading accuracy',
  ' (0, )  default = 0.08 / 0.05 (see above)  degrees  ',
  'User heading accuracy  4  float  (0, )  default = 0.08 / 0.05 (see above)  degrees  '],
 ['4',
  'float',
  'User position accuracy',
  ' (0, )  default = 2  meters  ',
  'User position accuracy  4  float  (0, )  default = 2  meters  '],
 ['4',
  'float',
  'User velocity accuracy',
  ' (0, )  default = 0.5  meters/second  ',
  'User velocity accuracy  4  float  (0, )  default = 0.5  meters/second  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['User_accuracy_specifications']=User_accuracy_specifications
structures["see table 48"]=User_accuracy_specifications
        
MESSAGE_ID_VALUES[24]='User_accuracy_specifications'

MESSAGE_VALUE_IDS['User_accuracy_specifications']=24

class RS_232_422_communication_protocol_settings(BaseField):
    FieldTag="RS_232_422_communication_protocol_settings"
    sdf_list = [['1',
  'byte',
  'RS-232/422 port baud rate',
  ' Value 0 1 2 3 4 5 6 7 8-255  Rate 2400 4800 9600 19200 38400 57600 76800 115200 Reserved  ',
  'RS-232/422 port baud rate  1  byte  Value 0 1 2 3 4 5 6 7 8-255  Rate 2400 4800 9600 19200 38400 57600 76800 115200 Reserved  '],
 ['1',
  'byte',
  'Parity',
  ' Value 0 1 2 3-255  Parity no parity even parity odd parity Reserved  ',
  'Parity  1  byte  Value 0 1 2 3-255  Parity no parity even parity odd parity Reserved  '],
 ['1',
  'byte',
  'Data/Stop Bits',
  ' Value  Data/Stop Bits  ',
  'Data/Stop Bits  1  byte  Value  Data/Stop Bits  '],
 ['1',
  'byte',
  'Flow Control1',
  ' Value 0  Flow Control none  ',
  'Flow Control1  1  byte  Value 0  Flow Control none  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['RS_232_422_communication_protocol_settings']=RS_232_422_communication_protocol_settings
structures["see table 50"]=RS_232_422_communication_protocol_settings
        
class Secondary_GPS_Setup(BaseField):
    FieldTag="Secondary_GPS_Setup"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 31  N/A  ',
  'Message ID  2  ushort  31  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 16  N/A  ',
  'Byte count  2  ushort  16  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Select/deselect GPS AutoConfig',
  ' Value State 0 AutoConfig disabled 1 AutoConfig enabled (default) 2-255 Reserved  ',
  'Select/deselect GPS AutoConfig  1  byte  Value State 0 AutoConfig disabled 1 AutoConfig enabled (default) 2-255 Reserved  '],
 ['1',
  'byte',
  'Secondary GPS COM1 port message output rate ',
  ' Value Rate (Hz) 1 1 (default) 2 2 3 3 4 4 5 5 10 10 11-255 Reserved  ',
  'Secondary GPS COM1 port message output rate (Not Supported)  1  byte  Value Rate (Hz) 1 1 (default) 2 2 3 3 4 4 5 5 10 10 11-255 Reserved  '],
 ['1',
  'byte',
  'Secondary GPS COM2 port control',
  ' Value Operation 0 Accept RTCM (default) 1 Accept commands 2 Accept RTCA 3-255 Reserved  ',
  'Secondary GPS COM2 port control  1  byte  Value Operation 0 Accept RTCM (default) 1 Accept commands 2 Accept RTCA 3-255 Reserved  '],
 ['4',
  'see table 50',
  'Secondary GPS COM2 communication protocol',
  'Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  ',
  'Secondary GPS COM2 communication protocol  4  See Table 50 Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  '],
 ['1',
  'byte',
  'Antenna frequency ',
  ' Value Operation 0 Accept L1 only 1 Accept L1/L2 2 Accept L2 only  ',
  'Antenna frequency (only applicable for Trimble Force5 GPS receivers)  1  byte  Value Operation 0 Accept L1 only 1 Accept L1/L2 2 Accept L2 only  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Secondary_GPS_Setup']=Secondary_GPS_Setup
structures["see table 51"]=Secondary_GPS_Setup
        
MESSAGE_ID_VALUES[31]='Secondary_GPS_Setup'

MESSAGE_VALUE_IDS['Secondary_GPS_Setup']=31

class Set_POS_IP_Address(BaseField):
    FieldTag="Set_POS_IP_Address"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 32  N/A  ',
  'Message ID  2  ushort  32  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 16  N/A  ',
  'Byte count  2  ushort  16  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'IP address: Network part 1',
  ' [1, 126] Class A (typical subnet mask 255.0.0.0) [128, 191] Class B (typical subnet mask 255.255.0.0 [192, 223] Class C (typical subnet mask 255.255.255.0) default = 129  N/A  ',
  'IP address: Network part 1  1  byte  [1, 126] Class A (typical subnet mask 255.0.0.0) [128, 191] Class B (typical subnet mask 255.255.0.0 [192, 223] Class C (typical subnet mask 255.255.255.0) default = 129  N/A  '],
 ['1',
  'byte',
  'IP address: Network part 2',
  ' [0, 255] default = 100  N/A  ',
  'IP address: Network part 2  1  byte  [0, 255] default = 100  N/A  '],
 ['1',
  'byte',
  'IP address: Host part 1',
  ' [0, 255] default = 0  N/A  ',
  'IP address: Host part 1  1  byte  [0, 255] default = 0  N/A  '],
 ['1',
  'byte',
  'IP address: Host part 2',
  ' [1, 254] default = 219  N/A  ',
  'IP address: Host part 2  1  byte  [1, 254] default = 219  N/A  '],
 ['1',
  'byte',
  'Subnet mask: Network part 1',
  ' [255] default = 255 * see conditions below  ',
  'Subnet mask: Network part 1  1  byte  [255] default = 255 * see conditions below  '],
 ['1',
  'byte',
  'Subnet mask: Network part 2',
  ' [0, 255] default = 255 * see conditions below  ',
  'Subnet mask: Network part 2  1  byte  [0, 255] default = 255 * see conditions below  '],
 ['1',
  'byte',
  'Subnet mask: Host part 1',
  ' [0, 255] default = 0 * see conditions below  ',
  'Subnet mask: Host part 1  1  byte  [0, 255] default = 0 * see conditions below  '],
 ['1',
  'byte',
  'Subnet mask: Host part 2',
  ' [0, 254] default = 0 * see conditions below  ',
  'Subnet mask: Host part 2  1  byte  [0, 254] default = 0 * see conditions below  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Set_POS_IP_Address']=Set_POS_IP_Address
structures["see table 52"]=Set_POS_IP_Address
        
MESSAGE_ID_VALUES[32]='Set_POS_IP_Address'

MESSAGE_VALUE_IDS['Set_POS_IP_Address']=32

class Event_Discrete_Setup(BaseField):
    FieldTag="Event_Discrete_Setup"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 33  N/A  ',
  'Message ID  2  ushort  33  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 28  N/A  ',
  'Byte count  2  ushort  28  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Output:  Transaction number [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Output:  Transaction number [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Event 1 trigger',
  ' Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  ',
  'Event 1 trigger  1  byte  Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  '],
 ['1',
  'byte',
  'Event 2 trigger',
  ' Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  ',
  'Event 2 trigger  1  byte  Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  '],
 ['1',
  'byte',
  'Event 3 trigger',
  ' Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  ',
  'Event 3 trigger  1  byte  Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  '],
 ['1',
  'byte',
  'Event 4 trigger',
  ' Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  ',
  'Event 4 trigger  1  byte  Value 0 1 2-255  Command Positive edge (default) Negative edge Reserved  '],
 ['1',
  'byte',
  'Event 5 trigger',
  ' Value Command 0 Positive edge (default) 1 Negative edge 2-255 Reserved  ',
  'Event 5 trigger  1  byte  Value Command 0 Positive edge (default) 1 Negative edge 2-255 Reserved  '],
 ['1',
  'byte',
  'Event 6 trigger',
  ' Value Command 0 Positive edge (default) 1 Negative edge 2-255 Reserved  ',
  'Event 6 trigger  1  byte  Value Command 0 Positive edge (default) 1 Negative edge 2-255 Reserved  '],
 ['2',
  'ushort',
  'Event 1 Guard Time',
  ' [2, 10 000] (default 2)  msec  ',
  'Event 1 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  '],
 ['2',
  'ushort',
  'Event 2 Guard Time',
  ' [2, 10 000] (default 2)  msec  ',
  'Event 2 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  '],
 ['2',
  'ushort',
  'Event 3 Guard Time',
  ' [2, 10 000] (default 2)  msec  ',
  'Event 3 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  '],
 ['2',
  'ushort',
  'Event 4 Guard Time',
  ' [2, 10 000] (default 2)  msec  ',
  'Event 4 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  '],
 ['2',
  'ushort',
  'Event 5 Guard Time',
  ' [2, 10 000] (default 2)  msec  ',
  'Event 5 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  '],
 ['2',
  'ushort',
  'Event 6 Guard Time',
  ' [2, 10 000] (default 2)  msec  ',
  'Event 6 Guard Time  2  ushort  [2, 10 000] (default 2)  msec  '],
 ['1',
  'byte',
  'PPS Out polarity',
  ' Value Command 0 Positive pulse (default) 1 Negative pulse 2 Pass through1 3-255 Reserved  ',
  'PPS Out polarity  1  byte  Value Command 0 Positive pulse (default) 1 Negative pulse 2 Pass through1 3-255 Reserved  '],
 ['2',
  'ushort',
  'PPS Out pulse width',
  ' [1, 500] (default 1)  msec  ',
  'PPS Out pulse width  2  ushort  [1, 500] (default 1)  msec  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Event_Discrete_Setup']=Event_Discrete_Setup
structures["see table 53"]=Event_Discrete_Setup
        
MESSAGE_ID_VALUES[33]='Event_Discrete_Setup'

MESSAGE_VALUE_IDS['Event_Discrete_Setup']=33

class COM_Port_Setup(BaseField):
    FieldTag="COM_Port_Setup"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 34  N/A  ',
  'Message ID  2  ushort  34  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 12 + 8 x nPorts  N/A  ',
  'Byte count  2  ushort  12 + 8 x nPorts  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['2',
  'ushort',
  'Number of COM ports',
  ' [1,10] Number (nPorts) of COM ports assigned by this message.  N/A  ',
  'Number of COM ports  2  ushort  [1,10] Number (nPorts) of COM ports assigned by this message.  N/A  '],
 ['2',
  'ushort',
  'Port mask',
  ' Input: Bit positions indicate which port parameters are in message (port parameters must appear in order of increasing port number). Bit 0 ignored Bit n set COMn parameter in message Bit n clear COMn parameter not in message Output: Bit positions indicate which port numbers are available on the PCS for I/O configuration.  ',
  'Port mask  2  ushort  Input: Bit positions indicate which port parameters are in message (port parameters must appear in order of increasing port number). Bit 0 ignored Bit n set COMn parameter in message Bit n clear COMn parameter not in message Output: Bit positions indicate which port numbers are available on the PCS for I/O configuration.  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['COM_Port_Setup']=COM_Port_Setup
structures["see table 54"]=COM_Port_Setup
        
MESSAGE_ID_VALUES[34]='COM_Port_Setup'

MESSAGE_VALUE_IDS['COM_Port_Setup']=34

class COM_port_parameters(BaseField):
    FieldTag="COM_port_parameters"
    sdf_list = [['4',
  'see table 50',
  'Communication protocol',
  'Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  ',
  'Communication protocol  4  See Table 50 Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  '],
 ['2',
  'ushort',
  'Input select',
  ' Value Input 0 No input 1 Auxiliary 1 GNSS 2 Auxiliary 2 GNSS 3 Reserved 4 Base GNSS 1 5 Base GNSS 2 6 Reserved 7 GNSS 11 8 GNSS 21 9-255 No input  ',
  'Input select  2  ushort  Value Input 0 No input 1 Auxiliary 1 GNSS 2 Auxiliary 2 GNSS 3 Reserved 4 Base GNSS 1 5 Base GNSS 2 6 Reserved 7 GNSS 11 8 GNSS 21 9-255 No input  '],
 ['2',
  'ushort',
  'Output select',
  ' Value 0 1 2 3 4 5 6 7 8 9-255  Output No output NMEA messages Real-time binary Reserved Base GNSS 1 Base GNSS 2 Reserved GNSS 11 GNSS 21 No output  ',
  'Output select  2  ushort  Value 0 1 2 3 4 5 6 7 8 9-255  Output No output NMEA messages Real-time binary Reserved Base GNSS 1 Base GNSS 2 Reserved GNSS 11 GNSS 21 No output  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['COM_port_parameters']=COM_port_parameters
structures["see table 55"]=COM_port_parameters
        
class Base_GPS_1_2_Setup(BaseField):
    FieldTag="Base_GPS_1_2_Setup"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 37/38  N/A  ',
  'Message ID  2  ushort  37/38  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 248  N/A  ',
  'Byte count  2  ushort  248  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['2',
  'ushort',
  'Select Base GPS input type',
  ' Value Operation 0 Do not accept base GPS messages 1 Accept RTCM MSG 1/9 (default) 2 Accept RTCMv2.x MSG 3, 18/19 3 Accept CMR/CMR+ 4 Accept RTCA (Deprecated) 5 Accept RTCMv3.x 6-65535 Reserved  ',
  'Select Base GPS input type  2  ushort  Value Operation 0 Do not accept base GPS messages 1 Accept RTCM MSG 1/9 (default) 2 Accept RTCMv2.x MSG 3, 18/19 3 Accept CMR/CMR+ 4 Accept RTCA (Deprecated) 5 Accept RTCMv3.x 6-65535 Reserved  '],
 ['1',
  'byte',
  'Line control',
  ' Value Operation 0 Line used for Serial (default) 1 Line used for Modem 2-255 Reserved  ',
  'Line control  1  byte  Value Operation 0 Line used for Serial (default) 1 Line used for Modem 2-255 Reserved  '],
 ['1',
  'byte',
  'Modem control',
  ' Value Operation 0 Automatic control (default) 1 Manual control 2 Command control 3-255 Reserved  ',
  'Modem control  1  byte  Value Operation 0 Automatic control (default) 1 Manual control 2 Command control 3-255 Reserved  '],
 ['1',
  'byte',
  'Connection control',
  ' Value Operation 0 No action (default) 1 Connect 2 Disconnect/Hang-up 3 Send AT Command 4-255 No action  ',
  'Connection control  1  byte  Value Operation 0 No action (default) 1 Connect 2 Disconnect/Hang-up 3 Send AT Command 4-255 No action  '],
 ['32',
  'char',
  'Phone number',
  ' N/A  N/A  ',
  'Phone number  32  char  N/A  N/A  '],
 ['1',
  'byte',
  'Number of redials',
  ' [0, ) default = 0  N/A  ',
  'Number of redials  1  byte  [0, ) default = 0  N/A  '],
 ['64',
  'char',
  'Modem command string',
  ' N/A  N/A  ',
  'Modem command string  64  char  N/A  N/A  '],
 ['128',
  'char',
  'Modem initialization string',
  ' N/A  N/A  ',
  'Modem initialization string  128  char  N/A  N/A  '],
 ['2',
  'ushort',
  'Data timeout length',
  ' [0, 255] default = 0  seconds  ',
  'Data timeout length  2  ushort  [0, 255] default = 0  seconds  '],
 ['2',
  'ushort',
  'Datum Type',
  ' Value 0 1  Operation WGS 84 (default) NAD 83  ',
  'Datum Type  2  ushort  Value 0 1  Operation WGS 84 (default) NAD 83  '],
 ['1',
  'byte',
  'Communication Protocol',
  ' Value 0 1 2  Protocol COM (default) TCP UDP  ',
  'Communication Protocol  1  byte  Value 0 1 2  Protocol COM (default) TCP UDP  '],
 ['1',
  'byte',
  'IP address: Network part 1',
  ' [1,126], [128, 223]  ',
  'IP address: Network part 1  1  byte  [1,126], [128, 223]  '],
 ['1',
  'byte',
  'IP address: Network part 2',
  ' [0, 255]  ',
  'IP address: Network part 2  1  byte  [0, 255]  '],
 ['1',
  'byte',
  'IP address: Host part 1',
  ' [0, 255]  ',
  'IP address: Host part 1  1  byte  [0, 255]  '],
 ['1',
  'byte',
  'IP address: Host part 2',
  ' [1, 254]  ',
  'IP address: Host part 2  1  byte  [1, 254]  '],
 ['2',
  'ushort',
  'Port Number',
  ' (0,65535]  ',
  'Port Number  2  ushort  (0,65535]  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Base_GPS_1_2_Setup']=Base_GPS_1_2_Setup
structures["see table 56"]=Base_GPS_1_2_Setup
        
MESSAGE_ID_VALUES[37]='Base_GPS_1_2_Setup'

MESSAGE_VALUE_IDS['Base_GPS_1_2_Setup']=37

MESSAGE_ID_VALUES[38]='Base_GPS_1_2_Setup'

MESSAGE_VALUE_IDS['Base_GPS_1_2_Setup']=38

class Aux_GNSS_Setup(BaseField):
    FieldTag="Aux_GNSS_Setup"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 39  N/A  ',
  'Message ID  2  ushort  39  N/A  '],
 ['2', 'ushort', 'Byte count', ' 8  N/A  ', 'Byte count  2  ushort  8  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Aux GNSS 1 protocol',
  ' Value 0 1  Protocol NMEA (default) NAVCOM  ',
  'Aux GNSS 1 protocol  1  Byte  Value 0 1  Protocol NMEA (default) NAVCOM  '],
 ['1',
  'byte',
  'Aux GNSS 2 protocol',
  ' Value 0 1  Protocol NMEA (default) NAVCOM  ',
  'Aux GNSS 2 protocol  1  Byte  Value 0 1  Protocol NMEA (default) NAVCOM  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Aux_GNSS_Setup']=Aux_GNSS_Setup
structures["see table 57"]=Aux_GNSS_Setup
        
MESSAGE_ID_VALUES[39]='Aux_GNSS_Setup'

MESSAGE_VALUE_IDS['Aux_GNSS_Setup']=39

class Primary_GPS_Receiver_Integrated_DGPS_Source_Control(BaseField):
    FieldTag="Primary_GPS_Receiver_Integrated_DGPS_Source_Control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 41  N/A  ',
  'Message ID  2  ushort  41  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 52  N/A  ',
  'Byte count  2  ushort  52  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'DGPS source mode',
  ' Source mode for DGPS corrections: 0 Disabled 2 MarineStar VBS only 5 MarineStar XP only 6 MarineStar HP only 7 MarineStar Auto mode 1, 3, 4 Reserved 8-11 Reserved 12 MarineStar G2 only 13 MarineStar HPXP 14 MarineStar HPG2  N/A  ',
  'DGPS source mode  1  byte  Source mode for DGPS corrections: 0 Disabled 2 MarineStar VBS only 5 MarineStar XP only 6 MarineStar HP only 7 MarineStar Auto mode 1, 3, 4 Reserved 8-11 Reserved 12 MarineStar G2 only 13 MarineStar HPXP 14 MarineStar HPG2  N/A  '],
 ['1',
  'byte',
  'Beacon Acquisition Mode',
  ' Beacon mode used to acquire DGPS signals : 0 Channel disabled 1 Manual mode 2 Auto Distance mode 3 Auto Power mode 4-255 Reserved  N/A  ',
  'Beacon Acquisition Mode  1  byte  Beacon mode used to acquire DGPS signals : 0 Channel disabled 1 Manual mode 2 Auto Distance mode 3 Auto Power mode 4-255 Reserved  N/A  '],
 ['2',
  'ushort',
  'Beacon Channel 0 Frequency',
  ' [2835-3250]  10 * kHz  ',
  'Beacon Channel 0 Frequency  2  ushort  [2835-3250]  10 * kHz  '],
 ['2',
  'ushort',
  'Beacon Channel 1 Frequency',
  ' [2835-3250]  10 * kHz  ',
  'Beacon Channel 1 Frequency  2  ushort  [2835-3250]  10 * kHz  '],
 ['1',
  'byte',
  'Satellite ID',
  ' 0-8 Reserved 9    MarineStar Auto ID Search 10-255 Reserved  N/A  ',
  'Satellite ID  1  byte  0-8 Reserved 9    MarineStar Auto ID Search 10-255 Reserved  N/A  '],
 ['2',
  'ushort',
  'Satellite bit rate',
  ' [600, 1200, 2400]  baud  ',
  'Satellite bit rate  2  ushort  [600, 1200, 2400]  baud  '],
 ['8',
  'double',
  'Satellite frequency',
  ' [1500e6-1600e6]  Hz  ',
  'Satellite frequency  8  double  [1500e6-1600e6]  Hz  '],
 ['1',
  'byte',
  'Request Database Source',
  ' 0 Unknown 1 Beacon Stations 2 LandStar Stations 3-255 Reserved  N/A  ',
  'Request Database Source  1  byte  0 Unknown 1 Beacon Stations 2 LandStar Stations 3-255 Reserved  N/A  '],
 ['1',
  'byte',
  'Landstar Correction Source',
  ' 0 Unknown 1 LandStar Stations 2 LandStar Network 3-255 Reserved  N/A  ',
  'Landstar Correction Source  1  byte  0 Unknown 1 LandStar Stations 2 LandStar Network 3-255 Reserved  N/A  '],
 ['25',
  'byte',
  'MarineSTAR Activation Code',
  ' 0 Unknown (0,) Enter service Provider Activation Information  N/A  ',
  'MarineSTAR Activation Code  25  byte  0 Unknown (0,) Enter service Provider Activation Information  N/A  '],
 ['1',
  'byte',
  'DGPS source mode 2',
  ' Source mode for DGPS corrections: 0 Disabled 8 WAAS mode 9 EGNOS mode 10 MSAS mode 1-7 Reserved 11-255 Reserved  N/A  ',
  'DGPS source mode 2  1  byte  Source mode for DGPS corrections: 0 Disabled 8 WAAS mode 9 EGNOS mode 10 MSAS mode 1-7 Reserved 11-255 Reserved  N/A  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Primary_GPS_Receiver_Integrated_DGPS_Source_Control']=Primary_GPS_Receiver_Integrated_DGPS_Source_Control
structures["see table 58"]=Primary_GPS_Receiver_Integrated_DGPS_Source_Control
        
MESSAGE_ID_VALUES[41]='Primary_GPS_Receiver_Integrated_DGPS_Source_Control'

MESSAGE_VALUE_IDS['Primary_GPS_Receiver_Integrated_DGPS_Source_Control']=41

class Navigation_mode_control(BaseField):
    FieldTag="Navigation_mode_control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 50  N/A  ',
  'Message ID  2  ushort  50  N/A  '],
 ['2', 'ushort', 'Byte count', ' 8  N/A  ', 'Byte count  2  ushort  8  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Navigation mode',
  ' Value 0 1 2 3-255  Mode No operation (default) Standby  Navigate Reserved  ',
  'Navigation mode  1  byte  Value 0 1 2 3-255  Mode No operation (default) Standby  Navigate Reserved  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Navigation_mode_control']=Navigation_mode_control
structures["see table 59"]=Navigation_mode_control
        
MESSAGE_ID_VALUES[50]='Navigation_mode_control'

MESSAGE_VALUE_IDS['Navigation_mode_control']=50

class Display_Port_Control(BaseField):
    FieldTag="Display_Port_Control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 51  N/A  ',
  'Message ID  2  ushort  51  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 10 + 2 x number of groups (+2 if pad bytes are required)  N/A  ',
  'Byte count  2  ushort  10 + 2 x number of groups (+2 if pad bytes are required)  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['2',
  'ushort',
  'Number of groups selected for Display Port',
  ' [4, 70] default = 4 (Groups 1,2,3,10 are always output on Display Port)  N/A  ',
  'Number of groups selected for Display Port  2  ushort  [4, 70] default = 4 (Groups 1,2,3,10 are always output on Display Port)  N/A  '],
 ['variable',
  'ushort',
  'Display Port output group identification',
  ' Group ID to output [1, 65534]  N/A  ',
  'Display Port output group identification  variable  ushort  Group ID to output [1, 65534]  N/A  '],
 ['2', 'ushort', 'Reserved', ' 0  N/A  ', 'Reserved  2  ushort  0  N/A  '],
 ['0 or 2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0 or 2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Display_Port_Control']=Display_Port_Control
structures["see table 60"]=Display_Port_Control
        
MESSAGE_ID_VALUES[51]='Display_Port_Control'

MESSAGE_VALUE_IDS['Display_Port_Control']=51

class Real_Time_Logging_Data_Port_Control(BaseField):
    FieldTag="Real_Time_Logging_Data_Port_Control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 52  N/A  ',
  'Message ID  2  ushort  52  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 15 + 2 x number of groups (+1 or 3 pad bytes)  N/A  ',
  'Byte count  2  ushort  15 + 2 x number of groups (+1 or 3 pad bytes)  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['2',
  'ushort',
  'Number of groups selected for Data Port',
  ' [0, 70] default = 0  N/A  ',
  'Number of groups selected for Data Port  2  ushort  [0, 70] default = 0  N/A  '],
 ['variable',
  'ushort',
  'Data Port output group identification',
  ' Group ID to output [1, 65534]  N/A  ',
  'Data Port output group identification  variable  ushort  Group ID to output [1, 65534]  N/A  '],
 ['2',
  'ushort',
  'Data Port output rate',
  ' Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 other values Reserved  ',
  'Data Port output rate  2  ushort  Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 other values Reserved  '],
 ['1',
  'byte',
  'Data Port Protocol',
  ' Value Protocol 0 TCP (default) 1 UDP Unicast 2 UDP Broadcast  ',
  'Data Port Protocol  1  byte  Value Protocol 0 TCP (default) 1 UDP Unicast 2 UDP Broadcast  '],
 ['1',
  'byte',
  'UDP Unicast IP Address: Network part 1',
  ' [128, 191] Class B, subnet mask 255.255.0.0 [192, 232] Class C, subnet mask 255.255.255.0 default = 192  N/A  ',
  'UDP Unicast IP Address: Network part 1  1  byte  [128, 191] Class B, subnet mask 255.255.0.0 [192, 232] Class C, subnet mask 255.255.255.0 default = 192  N/A  '],
 ['1',
  'byte',
  'UDP Unicast IP Address: Network part 2',
  ' [0, 255] default = 168  N/A  ',
  'UDP Unicast IP Address: Network part 2  1  byte  [0, 255] default = 168  N/A  '],
 ['1',
  'byte',
  'UDP Unicast IP Address: Host part 1',
  ' [0, 255] default = 53  N/A  ',
  'UDP Unicast IP Address: Host part 1  1  byte  [0, 255] default = 53  N/A  '],
 ['1',
  'byte',
  'UDP Unicast IP Address: Host part 2',
  ' [1, 253] default = 1  N/A  ',
  'UDP Unicast IP Address: Host part 2  1  byte  [1, 253] default = 1  N/A  '],
 ['1 or 3', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1 or 3  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Real_Time_Logging_Data_Port_Control']=Real_Time_Logging_Data_Port_Control
structures["see table 61"]=Real_Time_Logging_Data_Port_Control
        
MESSAGE_ID_VALUES[52]='Real_Time_Logging_Data_Port_Control'

MESSAGE_VALUE_IDS['Real_Time_Logging_Data_Port_Control']=52

MESSAGE_ID_VALUES[61]='Real_Time_Logging_Data_Port_Control'

MESSAGE_VALUE_IDS['Real_Time_Logging_Data_Port_Control']=61

class Logging_Port_Control(BaseField):
    FieldTag="Logging_Port_Control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 53  N/A  ',
  'Message ID  2  ushort  53  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 76 + 2 x number of groups (+2 if required for pad)  N/A  ',
  'Byte count  2  ushort  76 + 2 x number of groups (+2 if required for pad)  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['2',
  'ushort',
  'Number of groups selected for Logging Port',
  ' [0, 70] default = 0  N/A  ',
  'Number of groups selected for Logging Port  2  ushort  [0, 70] default = 0  N/A  '],
 ['variable',
  'ushort',
  'Logging Port output group identification',
  ' Group ID to Output [1, 65534]  N/A  ',
  'Logging Port output group identification  variable  ushort  Group ID to Output [1, 65534]  N/A  '],
 ['2',
  'ushort',
  'Logging Port output rate',
  ' Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 (NOT available for IMU type 17.) other values reserved  ',
  'Logging Port output rate  2  ushort  Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 (NOT available for IMU type 17.) other values reserved  '],
 ['1',
  'byte',
  'Select/deselect AutoLog',
  ' Value State 0 AutoLog disabled (default) 1 AutoLog enabled 2-255 No action  ',
  'Select/deselect AutoLog  1  byte  Value State 0 AutoLog disabled (default) 1 AutoLog enabled 2-255 No action  '],
 ['1',
  'byte',
  'Disk logging control',
  ' Value Command 0 Stop logging  (default) 1 Start logging 2-255 No action  ',
  'Disk logging control  1  byte  Value Command 0 Stop logging  (default) 1 Start logging 2-255 No action  '],
 ['0 or 2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0 or 2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Logging_Port_Control']=Logging_Port_Control
structures["see table 62"]=Logging_Port_Control
        
MESSAGE_ID_VALUES[53]='Logging_Port_Control'

MESSAGE_VALUE_IDS['Logging_Port_Control']=53

class Save_restore_parameters_control(BaseField):
    FieldTag="Save_restore_parameters_control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 54  N/A  ',
  'Message ID  2  ushort  54  N/A  '],
 ['2', 'ushort', 'Byte count', ' 8  N/A  ', 'Byte count  2  ushort  8  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Control',
  ' Value Operation 0 No operation 1 Save parameters in NVM 2 Restore user settings from NVM 3 Restore factory default settings 4-255 No operation  ',
  'Control  1  byte  Value Operation 0 No operation 1 Save parameters in NVM 2 Restore user settings from NVM 3 Restore factory default settings 4-255 No operation  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Save_restore_parameters_control']=Save_restore_parameters_control
structures["see table 63"]=Save_restore_parameters_control
        
MESSAGE_ID_VALUES[54]='Save_restore_parameters_control'

MESSAGE_VALUE_IDS['Save_restore_parameters_control']=54

class User_time_recovery(BaseField):
    FieldTag="User_time_recovery"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 55  N/A  ',
  'Message ID  2  ushort  55  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 24  N/A  ',
  'Byte count  2  ushort  24  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['8',
  'double',
  'User PPS time',
  ' [0, ) default = 0.0  seconds  ',
  'User PPS time  8  double  [0, ) default = 0.0  seconds  '],
 ['8',
  'double',
  'User time conversion factor',
  ' [0, ) default = 1.0  ./seconds  ',
  'User time conversion factor  8  double  [0, ) default = 1.0  ./seconds  '],
 ['2', 'short', 'Pad', ' 0  N/A  ', 'Pad  2  short  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['User_time_recovery']=User_time_recovery
structures["see table 64"]=User_time_recovery
        
MESSAGE_ID_VALUES[55]='User_time_recovery'

MESSAGE_VALUE_IDS['User_time_recovery']=55

class General_data(BaseField):
    FieldTag="General_data"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 56  N/A  ',
  'Message ID  2  ushort  56  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 80  N/A  ',
  'Byte count  2  ushort  80  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Time of day: Hours',
  ' [0, 23] default = 0  hours  ',
  'Time of day: Hours  1  byte  [0, 23] default = 0  hours  '],
 ['1',
  'byte',
  'Time of day: Minutes',
  ' [0, 59] default = 0  minutes  ',
  'Time of day: Minutes  1  byte  [0, 59] default = 0  minutes  '],
 ['1',
  'byte',
  'Time of day: Seconds',
  ' [0, 59] default = 0  seconds  ',
  'Time of day: Seconds  1  byte  [0, 59] default = 0  seconds  '],
 ['1',
  'byte',
  'Date: Month',
  ' [1, 12] default = 1  month  ',
  'Date: Month  1  byte  [1, 12] default = 1  month  '],
 ['1',
  'byte',
  'Date: Day',
  ' [1, 31] default = 1  day  ',
  'Date: Day  1  byte  [1, 31] default = 1  day  '],
 ['2',
  'ushort',
  'Date: Year',
  ' [0, 65534] default = 0  year  ',
  'Date: Year  2  ushort  [0, 65534] default = 0  year  '],
 ['1',
  'byte',
  'Initial alignment status',
  ' See Table 5  N/A  ',
  'Initial alignment status  1  byte  See Table 5  N/A  '],
 ['8',
  'double',
  'Initial latitude',
  ' [-90, +90]  default = 0  degrees  ',
  'Initial latitude  8  double  [-90, +90]  default = 0  degrees  '],
 ['8',
  'double',
  'Initial longitude',
  ' [-180, +180] default = 0  degrees  ',
  'Initial longitude  8  double  [-180, +180] default = 0  degrees  '],
 ['8',
  'double',
  'Initial altitude',
  ' [-1000, +10000] default = 0  meters  ',
  'Initial altitude  8  double  [-1000, +10000] default = 0  meters  '],
 ['4',
  'float',
  'Initial horizontal position CEP',
  ' [0, ) default = 0  meters  ',
  'Initial horizontal position CEP  4  float  [0, ) default = 0  meters  '],
 ['4',
  'float',
  'Initial altitude RMS uncertainty',
  ' [0, ) default = 0  meters  ',
  'Initial altitude RMS uncertainty  4  float  [0, ) default = 0  meters  '],
 ['8',
  'double',
  'Initial distance',
  ' [0, ) default = 0  meters  ',
  'Initial distance  8  double  [0, ) default = 0  meters  '],
 ['8',
  'double',
  'Initial roll',
  ' [-180, +180] default = 0  degrees  ',
  'Initial roll  8  double  [-180, +180] default = 0  degrees  '],
 ['8',
  'double',
  'Initial pitch',
  ' [-180, +180] default = 0  degrees  ',
  'Initial pitch  8  double  [-180, +180] default = 0  degrees  '],
 ['8',
  'double',
  'Initial heading',
  ' [0, 360) default = 0  degrees  ',
  'Initial heading  8  double  [0, 360) default = 0  degrees  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['General_data']=General_data
structures["see table 65"]=General_data
        
MESSAGE_ID_VALUES[56]='General_data'

MESSAGE_VALUE_IDS['General_data']=56

class Installation_calibration_control(BaseField):
    FieldTag="Installation_calibration_control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 57  N/A  ',
  'Message ID  2  ushort  57  N/A  '],
 ['2', 'ushort', 'Byte count', ' 9  N/A  ', 'Byte count  2  ushort  9  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Calibration action',
  ' Value Command 0 No action (default) 1 Stop all calibrations 2 Manual calibration 3 Auto-calibration 4 Normal calibrated parameter transfer 5 Forced calibrated parameter transfer 6-255 No action  ',
  'Calibration action  1  byte  Value Command 0 No action (default) 1 Stop all calibrations 2 Manual calibration 3 Auto-calibration 4 Normal calibrated parameter transfer 5 Forced calibrated parameter transfer 6-255 No action  '],
 ['2',
  'ushort',
  'Calibration select',
  ' Bit (set) Command 0 Calibrate primary GPS lever arm 1 Calibrate auxiliary 1 GPS lever arm 2 Calibrate auxiliary 2 GPS lever arm 3 - 7 reserved 8 Calibrate GAMS lever arm  ',
  'Calibration select  2  ushort  Bit (set) Command 0 Calibrate primary GPS lever arm 1 Calibrate auxiliary 1 GPS lever arm 2 Calibrate auxiliary 2 GPS lever arm 3 - 7 reserved 8 Calibrate GAMS lever arm  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Installation_calibration_control']=Installation_calibration_control
structures["see table 66"]=Installation_calibration_control
        
MESSAGE_ID_VALUES[57]='Installation_calibration_control'

MESSAGE_VALUE_IDS['Installation_calibration_control']=57

class GAMS_Calibration_Control(BaseField):
    FieldTag="GAMS_Calibration_Control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 58  N/A  ',
  'Message ID  2  ushort  58  N/A  '],
 ['2', 'ushort', 'Byte count', ' 8  N/A  ', 'Byte count  2  ushort  8  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'GAMS calibration control',
  ' Value Command 0 Stop calibration (default) (deprecated) 1 Begin or resume calibration 2 Suspend calibration (deprecated) 3 Force calibration (deprecated) 4-255 No action  ',
  'GAMS calibration control  1  byte  Value Command 0 Stop calibration (default) (deprecated) 1 Begin or resume calibration 2 Suspend calibration (deprecated) 3 Force calibration (deprecated) 4-255 No action  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GAMS_Calibration_Control']=GAMS_Calibration_Control
structures["see table 67"]=GAMS_Calibration_Control
        
MESSAGE_ID_VALUES[58]='GAMS_Calibration_Control'

MESSAGE_VALUE_IDS['GAMS_Calibration_Control']=58

class Second_Data_PortControl(BaseField):
    FieldTag="Second_Data_PortControl"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 52 or 61  N/A  ',
  'Message ID  2  ushort  52 or 61  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 10 + 2 x number of groups (+2 if pad bytes are required)  N/A  ',
  'Byte count  2  ushort  10 + 2 x number of groups (+2 if pad bytes are required)  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['2',
  'ushort',
  'Number of groups selected for Data Port',
  ' [0, 70] default = 0  N/A  ',
  'Number of groups selected for Data Port  2  ushort  [0, 70] default = 0  N/A  '],
 ['variable',
  'ushort',
  'Data Port output group identification',
  ' Group ID to output [1, 65534]  N/A  ',
  'Data Port output group identification  variable  ushort  Group ID to output [1, 65534]  N/A  '],
 ['2',
  'ushort',
  'Data Port output rate',
  ' Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 other values Reserved  ',
  'Data Port output rate  2  ushort  Value Rate (Hz) 1 1 (default) 2 2 10 10 20 20 25 25 50 50 100 100 200 200 other values Reserved  '],
 ['0 or 2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0 or 2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Second_Data_PortControl']=Second_Data_PortControl
structures["see table 68"]=Second_Data_PortControl
        
MESSAGE_ID_VALUES[52]='Second_Data_PortControl'

MESSAGE_VALUE_IDS['Second_Data_PortControl']=52

MESSAGE_ID_VALUES[61]='Second_Data_PortControl'

MESSAGE_VALUE_IDS['Second_Data_PortControl']=61

class Program_Control(BaseField):
    FieldTag="Program_Control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 90  N/A  ',
  'Message ID  2  ushort  90  N/A  '],
 ['2', 'ushort', 'Byte count', ' 8  N/A  ', 'Byte count  2  ushort  8  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['2',
  'ushort',
  'Control',
  ' Value Command 000 Controller alive 001 Terminate TCP/IP connection 100 Reset GAMS 101 Reset POS 102 Shutdown POS all other values are reserved  ',
  'Control  2  ushort  Value Command 000 Controller alive 001 Terminate TCP/IP connection 100 Reset GAMS 101 Reset POS 102 Shutdown POS all other values are reserved  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Program_Control']=Program_Control
structures["see table 69"]=Program_Control
        
MESSAGE_ID_VALUES[90]='Program_Control'

MESSAGE_VALUE_IDS['Program_Control']=90

class GPS_control(BaseField):
    FieldTag="GPS_control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 91  N/A  ',
  'Message ID  2  ushort  91  N/A  '],
 ['2', 'ushort', 'Byte count', ' 8  N/A  ', 'Byte count  2  ushort  8  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Control command',
  ' Value 0 1 2 3 4-255  Command Send primary GPS configuration Send primary GPS reset command Send secondary GPS configuration Send secondary GPS reset command No action  ',
  'Control command  1  byte  Value 0 1 2 3 4-255  Command Send primary GPS configuration Send primary GPS reset command Send secondary GPS configuration Send secondary GPS reset command No action  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GPS_control']=GPS_control
structures["see table 70"]=GPS_control
        
MESSAGE_ID_VALUES[91]='GPS_control'

MESSAGE_VALUE_IDS['GPS_control']=91

class Heave_Filter_Set_up(BaseField):
    FieldTag="Heave_Filter_Set_up"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 106  N/A  ',
  'Message ID  2  ushort  106  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 16  N/A  ',
  'Byte count  2  ushort  16  N/A  '],
 ['2',
  'ushort',
  'Transaction',
  ' Input: Transaction number set by client Output: [65533, 65535]  N/A  ',
  'Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  '],
 ['4',
  'float',
  'Heave Corner Period',
  ' (10.0, ) (default = 200.0)  seconds  ',
  'Heave Corner Period  4  float  (10.0, ) (default = 200.0)  seconds  '],
 ['4',
  'float',
  'Heave Damping Ratio',
  ' (0, 1.0) (default = 0.707)  N/A  ',
  'Heave Damping Ratio  4  float  (0, 1.0) (default = 0.707)  N/A  '],
 ['1',
  'byte',
  'Heave Phase Corrector',
  ' (1,0) = (on,off) (default = 0)  N/A  ',
  'Heave Phase Corrector  1  byte  (1,0) = (on,off) (default = 0)  N/A  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Heave_Filter_Set_up']=Heave_Filter_Set_up
structures["see table 71"]=Heave_Filter_Set_up
        
MESSAGE_ID_VALUES[106]='Heave_Filter_Set_up'

MESSAGE_VALUE_IDS['Heave_Filter_Set_up']=106

class Password_Protection_Control(BaseField):
    FieldTag="Password_Protection_Control"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 111  N/A  ',
  'Message ID  2  ushort  111  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 48  N/A  ',
  'Byte count  2  ushort  48  N/A  '],
 ['2',
  'ushort',
  'Transaction',
  ' Input: Transaction number set by client Output: [65533, 65535]  N/A  ',
  'Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Password Control',
  ' Value Command 0 Login 1 Change Password  N/A  ',
  'Password Control  1  byte  Value Command 0 Login 1 Change Password  N/A  '],
 ['20',
  'char',
  'Password',
  ' String value of current Password, terminated by "null" if less than 20 characters, or 20 (non-null) characters. Default: pcsPasswd  N/A  ',
  'Password  20  char  String value of current Password, terminated by "null" if less than 20 characters, or 20 (non-null) characters. Default: pcsPasswd  N/A  '],
 ['20',
  'char',
  'New Password',
  ' If Password Control = 0: N/A If Password Control = 1: String value of new (user-selected) Password, terminated by "null" if less than 20 characters, or 20 (non-null) characters.  N/A  ',
  'New Password  20  char  If Password Control = 0: N/A If Password Control = 1: String value of new (user-selected) Password, terminated by "null" if less than 20 characters, or 20 (non-null) characters.  N/A  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Password_Protection_Control']=Password_Protection_Control
structures["see table 72"]=Password_Protection_Control
        
MESSAGE_ID_VALUES[111]='Password_Protection_Control'

MESSAGE_VALUE_IDS['Password_Protection_Control']=111

class Sensor_Parameter_Set_up(BaseField):
    FieldTag="Sensor_Parameter_Set_up"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 120  N/A  ',
  'Message ID  2  ushort  120  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 68  N/A  ',
  'Byte count  2  ushort  68  N/A  '],
 ['2',
  'ushort',
  'Transaction',
  ' Input: Transaction number set by client Output: [65533, 65535]  N/A  ',
  'Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  '],
 ['4',
  'float',
  'X Sensor 1 wrt reference frame mounting angle',
  ' [-180, +180] default = 0  deg  ',
  'X Sensor 1 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  '],
 ['4',
  'float',
  'Y Sensor 1 wrt reference frame mounting angle',
  ' [-180, +180] default = 0  deg  ',
  'Y Sensor 1 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  '],
 ['4',
  'float',
  'Z Sensor 1 wrt reference frame mounting angle',
  ' [-180, +180] default = 0  deg  ',
  'Z Sensor 1 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  '],
 ['4',
  'float',
  'X Sensor 2 wrt reference frame mounting angle',
  ' [-180, +180] default = 0  deg  ',
  'X Sensor 2 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  '],
 ['4',
  'float',
  'Y Sensor 2 wrt reference frame mounting angle',
  ' [-180, +180] default = 0  deg  ',
  'Y Sensor 2 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  '],
 ['4',
  'float',
  'Z Sensor 2 wrt reference frame mounting angle',
  ' [-180, +180] default = 0  deg  ',
  'Z Sensor 2 wrt reference frame mounting angle  4  float  [-180, +180] default = 0  deg  '],
 ['4',
  'float',
  'Reference to Sensor 1 X lever arm',
  ' ( , ) default = 0  m  ',
  'Reference to Sensor 1 X lever arm  4  float  ( , ) default = 0  m  '],
 ['4',
  'float',
  'Reference to Sensor 1 Y lever arm',
  ' ( , ) default = 0  m  ',
  'Reference to Sensor 1 Y lever arm  4  float  ( , ) default = 0  m  '],
 ['4',
  'float',
  'Reference to Sensor 1 Z lever arm',
  ' ( , ) default = 0  m  ',
  'Reference to Sensor 1 Z lever arm  4  float  ( , ) default = 0  m  '],
 ['4',
  'float',
  'Reference to Sensor 2 X lever arm',
  ' ( , ) default = 0  m  ',
  'Reference to Sensor 2 X lever arm  4  float  ( , ) default = 0  m  '],
 ['4',
  'float',
  'Reference to Sensor 2 Y lever arm',
  ' ( , )  default = 0  m  ',
  'Reference to Sensor 2 Y lever arm  4  float  ( , )  default = 0  m  '],
 ['4',
  'float',
  'Reference to Sensor 2 Z lever arm',
  ' ( , )  default = 0  m  ',
  'Reference to Sensor 2 Z lever arm  4  float  ( , )  default = 0  m  '],
 ['4',
  'float',
  'Reference to CoR X lever arm',
  ' ( , )  default = 0  m  ',
  'Reference to CoR X lever arm  4  float  ( , )  default = 0  m  '],
 ['4',
  'float',
  'Reference to CoR Y lever arm',
  ' ( , )  default = 0  m  ',
  'Reference to CoR Y lever arm  4  float  ( , )  default = 0  m  '],
 ['4',
  'float',
  'Reference to CoR Z lever arm',
  ' ( , )  default = 0  m  ',
  'Reference to CoR Z lever arm  4  float  ( , )  default = 0  m  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Sensor_Parameter_Set_up']=Sensor_Parameter_Set_up
structures["see table 73"]=Sensor_Parameter_Set_up
        
MESSAGE_ID_VALUES[120]='Sensor_Parameter_Set_up'

MESSAGE_VALUE_IDS['Sensor_Parameter_Set_up']=120

class Vessel_Installation_Parameter_Set_up(BaseField):
    FieldTag="Vessel_Installation_Parameter_Set_up"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 121  N/A  ',
  'Message ID  2  ushort  121  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 20  N/A  ',
  'Byte count  2  ushort  20  N/A  '],
 ['2',
  'ushort',
  'Transaction',
  ' Input: Transaction number set by client Output: [65533, 65535]  N/A  ',
  'Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  '],
 ['4',
  'float',
  'Reference to Vessel X lever arm',
  ' ( , )  default = 0  m  ',
  'Reference to Vessel X lever arm  4  float  ( , )  default = 0  m  '],
 ['4',
  'float',
  'Reference to Vessel Y lever arm',
  ' ( , )  default = 0  m  ',
  'Reference to Vessel Y lever arm  4  float  ( , )  default = 0  m  '],
 ['4',
  'float',
  'Reference to Vessel Z lever arm',
  ' ( , )  default = 0  m  ',
  'Reference to Vessel Z lever arm  4  float  ( , )  default = 0  m  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Vessel_Installation_Parameter_Set_up']=Vessel_Installation_Parameter_Set_up
structures["see table 74"]=Vessel_Installation_Parameter_Set_up
        
MESSAGE_ID_VALUES[121]='Vessel_Installation_Parameter_Set_up'

MESSAGE_VALUE_IDS['Vessel_Installation_Parameter_Set_up']=121

class NMEA_Port_Definition(BaseField):
    FieldTag="NMEA_Port_Definition"
    sdf_list = [['1',
  'byte',
  'Port Number',
  ' [1, 10]  N/A  ',
  'Port Number  1  byte  [1, 10]  N/A  '],
 ['4',
  'ulong',
  'Nmea Formula Select',
  ' Bit (set) Format Formula 0 $xxGST NMEA (pseudorange measurement noise stats) 1 (default) $xxGGA NMEA (Global Position System Fix) 2 $xxHDT NMEA (heading) 3 $xxZDA NMEA (date & time) 4,5 reserved 6 $xxVTG NMEA (track and speed) 7 $PASHR NMEA (attitude (Tate-Bryant)) 8 $PASHR NMEA (attitude (TSS)) 9 $PRDID NMEA (attitude (Tate-Bryant) 10 $PRDID NMEA (attitude (TSS) 11 $xxGGK NMEA (Global Position System Fix) 12 $UTC UTC date and time 13 reserved 14 $xxPPS UTC time of PPS pulse 15 reserved 16 $xxRMC NMEA (Global Position System Fix) 21 $xxGLL NMEA (Global Position System Fix) 22 UTCT UTC Time Trimble Format 23 $xxGGAT NMEA (Trimble expanded GGA) xx - is substituted by the Talker ID  N/A  ',
  'Nmea Formula Select  4  ulong  Bit (set) Format Formula 0 $xxGST NMEA (pseudorange measurement noise stats) 1 (default) $xxGGA NMEA (Global Position System Fix) 2 $xxHDT NMEA (heading) 3 $xxZDA NMEA (date & time) 4,5 reserved 6 $xxVTG NMEA (track and speed) 7 $PASHR NMEA (attitude (Tate-Bryant)) 8 $PASHR NMEA (attitude (TSS)) 9 $PRDID NMEA (attitude (Tate-Bryant) 10 $PRDID NMEA (attitude (TSS) 11 $xxGGK NMEA (Global Position System Fix) 12 $UTC UTC date and time 13 reserved 14 $xxPPS UTC time of PPS pulse 15 reserved 16 $xxRMC NMEA (Global Position System Fix) 21 $xxGLL NMEA (Global Position System Fix) 22 UTCT UTC Time Trimble Format 23 $xxGGAT NMEA (Trimble expanded GGA) xx - is substituted by the Talker ID  N/A  '],
 ['2',
  'ushort',
  'Nmea output rate',
  ' Value Rate (Hz) 0 N/A  Hz  ',
  'Nmea output rate  2  ushort  Value Rate (Hz) 0 N/A  Hz  '],
 ['1',
  'byte',
  'Talker ID',
  ' Value ID 0 IN (default) 1 GP  N/A  ',
  'Talker ID  1  byte  Value ID 0 IN (default) 1 GP  N/A  '],
 ['1',
  'byte',
  'Roll Sense',
  ' Value Digital +ve 0 port up (default) 1 starboard up  N/A  ',
  'Roll Sense  1  byte  Value Digital +ve 0 port up (default) 1 starboard up  N/A  '],
 ['1',
  'byte',
  'Pitch Sense',
  ' Value Digital +ve 0 bow up (default) 1 stern up  N/A  ',
  'Pitch Sense  1  byte  Value Digital +ve 0 bow up (default) 1 stern up  N/A  '],
 ['1',
  'byte',
  'Heave Sense',
  ' Value Digital +ve 0 up (default) 1 down  N/A  ',
  'Heave Sense  1  byte  Value Digital +ve 0 up (default) 1 down  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['NMEA_Port_Definition']=NMEA_Port_Definition
structures["see table 76"]=NMEA_Port_Definition
        
class Binary_Port_Definition(BaseField):
    FieldTag="Binary_Port_Definition"
    sdf_list = [['1',
  'byte',
  'Port Number',
  ' [1, 10]  N/A  ',
  'Port Number  1  byte  [1, 10]  N/A  '],
 ['4',
  'ushort',
  'Formula Select',
  ' Value Format Formula 0 - 2 reserved 3 Simrad1000 header (Tate-Bryant) roll = . pitch = . heave = heave heading = . 4 Simrad1000 header (TSS) roll = sin-1(sin.cos.) pitch = . heave = heave heading = . 5 Simrad3000 header (Tate-Bryant) roll = . pitch = . heave = heave heading = . 6 Simrad3000 header (TSS) roll = sin-1(sin.cos.) pitch = . heave = heave  N/A  ',
  'Formula Select  4  ushort  Value Format Formula 0 - 2 reserved 3 Simrad1000 header (Tate-Bryant) roll = . pitch = . heave = heave heading = . 4 Simrad1000 header (TSS) roll = sin-1(sin.cos.) pitch = . heave = heave heading = . 5 Simrad3000 header (Tate-Bryant) roll = . pitch = . heave = heave heading = . 6 Simrad3000 header (TSS) roll = sin-1(sin.cos.) pitch = . heave = heave  N/A  '],
 ['1',
  'byte',
  'Message Update Rate',
  ' Value Rate (Hz) 0 N/A 1 1 2 2 5 5 10 10 20 20 25 25 (default) 50 50 100 100 200 200  Hz  ',
  'Message Update Rate  1  byte  Value Rate (Hz) 0 N/A 1 1 2 2 5 5 10 10 20 20 25 25 (default) 50 50 100 100 200 200  Hz  '],
 ['1',
  'byte',
  'Roll Sense',
  ' Value Digital +ve 0 port up (default) 1 starboard up  N/A  ',
  'Roll Sense  1  byte  Value Digital +ve 0 port up (default) 1 starboard up  N/A  '],
 ['1',
  'byte',
  'Pitch Sense',
  ' Value Digital +ve 0 bow up (default) 1 stern up  N/A  ',
  'Pitch Sense  1  byte  Value Digital +ve 0 bow up (default) 1 stern up  N/A  '],
 ['1',
  'byte',
  'Heave Sense',
  ' Value Digital +ve 0 up (default) 1 down  N/A  ',
  'Heave Sense  1  byte  Value Digital +ve 0 up (default) 1 down  N/A  '],
 ['1',
  'byte',
  'Sensor Frame Output',
  ' Value Frame of Reference 0 sensor 1 frame (default) 1 sensor 2 frame  N/A  ',
  'Sensor Frame Output  1  byte  Value Frame of Reference 0 sensor 1 frame (default) 1 sensor 2 frame  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Binary_Port_Definition']=Binary_Port_Definition
structures["see table 78"]=Binary_Port_Definition
        
class Binary_Output_Diagnostics(BaseField):
    FieldTag="Binary_Output_Diagnostics"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 20102  N/A  ',
  'Message ID  2  ushort  20102  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 24  N/A  ',
  'Byte count  2  ushort  24  N/A  '],
 ['2',
  'ushort',
  'Transaction',
  ' Input: Transaction number set by client Output: [65533, 65535]  N/A  ',
  'Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  '],
 ['4',
  'float',
  'Operator roll input',
  ' (-180, 180] default = 0  deg  ',
  'Operator roll input  4  float  (-180, 180] default = 0  deg  '],
 ['4',
  'float',
  'Operator pitch input',
  ' (-180, 180] default = 0  deg  ',
  'Operator pitch input  4  float  (-180, 180] default = 0  deg  '],
 ['4',
  'float',
  'Operator heading input',
  ' [0, 360) default = 0  deg  ',
  'Operator heading input  4  float  [0, 360) default = 0  deg  '],
 ['4',
  'float',
  'Operator heave input',
  ' [-100 to 100] default = 0  m  ',
  'Operator heave input  4  float  [-100 to 100] default = 0  m  '],
 ['1',
  'byte',
  'Output Enable',
  ' Value Command 0 Disabled (default) Output navigation solution data 1 Enabled Output operator specified fixed values  ',
  'Output Enable  1  byte  Value Command 0 Disabled (default) Output navigation solution data 1 Enabled Output operator specified fixed values  '],
 ['1', 'byte', 'Pad', ' 0  N/A  ', 'Pad  1  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Binary_Output_Diagnostics']=Binary_Output_Diagnostics
structures["see table 79"]=Binary_Output_Diagnostics
        
MESSAGE_ID_VALUES[20102]='Binary_Output_Diagnostics'

MESSAGE_VALUE_IDS['Binary_Output_Diagnostics']=20102

class Byte_Format_MSBit_LSBit(BaseField):
    FieldTag="Byte_Format_MSBit_LSBit"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Byte_Format_MSBit_LSBit']=Byte_Format_MSBit_LSBit
structures["see table 80"]=Byte_Format_MSBit_LSBit
        
class Short_Integer_Format_MSB_LSB(BaseField):
    FieldTag="Short_Integer_Format_MSB_LSB"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Short_Integer_Format_MSB_LSB']=Short_Integer_Format_MSB_LSB
structures["see table 81"]=Short_Integer_Format_MSB_LSB
        
class Long_Integer_Format_MSB_LSB(BaseField):
    FieldTag="Long_Integer_Format_MSB_LSB"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Long_Integer_Format_MSB_LSB']=Long_Integer_Format_MSB_LSB
structures["see table 82"]=Long_Integer_Format_MSB_LSB
        
class Single_Precision_Real_Format(BaseField):
    FieldTag="Single_Precision_Real_Format"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Single_Precision_Real_Format']=Single_Precision_Real_Format
structures["see table 83"]=Single_Precision_Real_Format
        
class Double_Precision_Real_Format(BaseField):
    FieldTag="Double_Precision_Real_Format"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Double_Precision_Real_Format']=Double_Precision_Real_Format
structures["see table 84"]=Double_Precision_Real_Format
        
class Invalid_data_values(BaseField):
    FieldTag="Invalid_data_values"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Invalid_data_values']=Invalid_data_values
structures["see table 85"]=Invalid_data_values
        
class format(BaseField):
    FieldTag="format"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2',
  'ushort',
  'Group ID',
  ' Group number  N/A  ',
  'Group ID  2  ushort  Group number  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' Group dependent  bytes  ',
  'Byte count  2  ushort  Group dependent  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['0 to 3', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0 to 3  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['format']=format
structures["see table 2"]=format
        
class Primary_GNSS_status(BaseField):
    FieldTag="Primary_GNSS_status"
    sdf_list = [['4',
  'char',
  'Group start',
  ' $GRP  N/A  ',
  'Group start  4  char  $GRP  N/A  '],
 ['2', 'ushort', 'Group ID', ' 3  N/A  ', 'Group ID  2  ushort  3  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 76 + 20 x (number of channels)  bytes  ',
  'Byte count  2  ushort  76 + 20 x (number of channels)  bytes  '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  ' ',
  'Time/Distance Fields  26  See Table 3  '],
 ['1',
  'byte',
  'Navigation solution status',
  ' See Table 9  N/A  ',
  'Navigation solution status  1  byte  See Table 9  N/A  '],
 ['1',
  'byte',
  'Number of SV tracked',
  ' [0, 60]  N/A  ',
  'Number of SV tracked  1  byte  [0, 60]  N/A  '],
 ['2',
  'ushort',
  'Channel status byte count',
  ' [0, 1200]  bytes  ',
  'Channel status byte count  2  ushort  [0, 1200]  bytes  '],
 ['variable',
  'see table 8',
  'Channel status',
  ' ',
  'Channel status  variable  See Table 8  '],
 ['4', 'float', 'HDOP', ' ( , )  N/A  ', 'HDOP  4  float  ( , )  N/A  '],
 ['4', 'float', 'VDOP', ' ( , )  N/A  ', 'VDOP  4  float  ( , )  N/A  '],
 ['4',
  'float',
  'DGPS correction latency',
  ' [0, 999.9]  seconds  ',
  'DGPS correction latency  4  float  [0, 999.9]  seconds  '],
 ['2',
  'ushort',
  'DGPS reference ID',
  ' [0, 1023]  N/A  ',
  'DGPS reference ID  2  ushort  [0, 1023]  N/A  '],
 ['4',
  'ulong',
  'GPS/UTC week number',
  ' [0, 9999) 0 if not available  week  ',
  'GPS/UTC week number  4  ulong  [0, 9999) 0 if not available  week  '],
 ['8',
  'double',
  'GPS/UTC time offset ',
  ' ( , )  seconds  ',
  'GPS/UTC time offset (GPS time - UTC time)  8  double  ( , )  seconds  '],
 ['4',
  'float',
  'GNSS navigation message latency',
  ' Number of seconds from the PPS pulse to the start of the GNSS navigation data output  seconds  ',
  'GNSS navigation message latency  4  float  Number of seconds from the PPS pulse to the start of the GNSS navigation data output  seconds  '],
 ['4',
  'float',
  'Geoidal separation',
  ' ( , )  meters  ',
  'Geoidal separation  4  float  ( , )  meters  '],
 ['2',
  'ushort',
  'GNSS receiver type',
  ' See Table 12  N/A  ',
  'GNSS receiver type  2  ushort  See Table 12  N/A  '],
 ['4',
  'ulong',
  'GNSS status',
  ' GNSS summary status fields which depend on GNSS receiver type.  ',
  'GNSS status  4  ulong  GNSS summary status fields which depend on GNSS receiver type.  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Group end', ' $#  N/A  ', 'Group end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Primary_GNSS_status']=Primary_GNSS_status
structures["see table 7"]=Primary_GNSS_status
        
GROUP_ID_VALUES[3]='Primary_GNSS_status'

GROUP_VALUE_IDS['Primary_GNSS_status']=3

class Primary_GPS_Setup(BaseField):
    FieldTag="Primary_GPS_Setup"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 30  N/A  ',
  'Message ID  2  ushort  30  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' 16  N/A  ',
  'Byte count  2  ushort  16  N/A  '],
 ['2',
  'ushort',
  'Transaction number',
  ' Input: Transaction number Output: [65533, 65535]  N/A  ',
  'Transaction number  2  ushort  Input: Transaction number Output: [65533, 65535]  N/A  '],
 ['1',
  'byte',
  'Select/deselect GPS AutoConfig',
  ' Value State 0 AutoConfig disabled 1 AutoConfig enabled (default) 2-255 Reserved  ',
  'Select/deselect GPS AutoConfig  1  byte  Value State 0 AutoConfig disabled 1 AutoConfig enabled (default) 2-255 Reserved  '],
 ['1',
  'byte',
  'Primary GPS COM1 port message output rate ',
  ' Value Rate (Hz) 1 1 (default) 2 2 3 3 4 4 5 5 10 10 11-255 Reserved  ',
  'Primary GPS COM1 port message output rate (not supported)  1  byte  Value Rate (Hz) 1 1 (default) 2 2 3 3 4 4 5 5 10 10 11-255 Reserved  '],
 ['1',
  'byte',
  'Primary GPS COM2 port control',
  ' Value Operation 0 Accept RTCM (default) 1 Accept commands 2 Accept RTCA 3-255 Reserved  ',
  'Primary GPS COM2 port control  1  byte  Value Operation 0 Accept RTCM (default) 1 Accept commands 2 Accept RTCA 3-255 Reserved  '],
 ['4',
  'see table 50',
  'Primary GPS COM2 communication protocol',
  'Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  ',
  'Primary GPS COM2 communication protocol  4  See Table 50 Default: 9600 baud, no parity, 8 data bits, 1 stop bit, none  '],
 ['1',
  'byte',
  'Antenna frequency ',
  ' Value Operation 0 Accept L1 only 1 Accept L1/L2 2 Accept L2 only  ',
  'Antenna frequency (only applicable for Trimble Force5 GPS receivers)  1  byte  Value Operation 0 Accept L1 only 1 Accept L1/L2 2 Accept L2 only  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Primary_GPS_Setup']=Primary_GPS_Setup
structures["see table 49"]=Primary_GPS_Setup
        
MESSAGE_ID_VALUES[30]='Primary_GPS_Setup'

MESSAGE_VALUE_IDS['Primary_GPS_Setup']=30

class NMEA_Output_Set_up(BaseField):
    FieldTag="NMEA_Output_Set_up"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 135  N/A  ',
  'Message ID  2  ushort  135  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' For even #ports (16 + #ports x 10) For odd #ports (18 + #ports x 10)  N/A  ',
  'Byte count  2  ushort  For even #ports (16 + #ports x 10) For odd #ports (18 + #ports x 10)  N/A  '],
 ['2',
  'ushort',
  'Transaction',
  ' Input: Transaction number set by client Output: [65533, 65535]  N/A  ',
  'Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  '],
 ['9', 'byte', 'Reserved', ' N/A  N/A  ', 'Reserved  9  byte  N/A  N/A  '],
 ['1',
  'byte',
  'Number of Ports',
  ' [0, 10]  N/A  ',
  'Number of Ports  1  byte  [0, 10]  N/A  '],
 ['variable',
  'see table 76',
  'NMEA Port Definitions',
  ' NMEA Port Definition #ports x 10  ',
  'NMEA Port Definitions  variable  See Table 76: NMEA Port Definition #ports x 10  '],
 ['0 or 21', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0 or 21  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['NMEA_Output_Set_up']=NMEA_Output_Set_up
structures["see table 75"]=NMEA_Output_Set_up
        
MESSAGE_ID_VALUES[135]='NMEA_Output_Set_up'

MESSAGE_VALUE_IDS['NMEA_Output_Set_up']=135

MESSAGE_ID_VALUES[35]='NMEA_Output_Set_up'

MESSAGE_VALUE_IDS['NMEA_Output_Set_up']=35

class Binary_Output_Set_up(BaseField):
    FieldTag="Binary_Output_Set_up"
    sdf_list = [['4',
  'char',
  'Message start',
  ' $MSG  N/A  ',
  'Message start  4  char  $MSG  N/A  '],
 ['2',
  'ushort',
  'Message ID',
  ' 136  N/A  ',
  'Message ID  2  ushort  136  N/A  '],
 ['2',
  'ushort',
  'Byte count',
  ' For even #ports (16 + #ports x 10) For odd #ports (14 + #ports x 10)  N/A  ',
  'Byte count  2  ushort  For even #ports (16 + #ports x 10) For odd #ports (14 + #ports x 10)  N/A  '],
 ['2',
  'ushort',
  'Transaction',
  ' Input: Transaction number set by client Output: [65533, 65535]  N/A  ',
  'Transaction #  2  ushort  Input: Transaction number set by client Output: [65533, 65535]  N/A  '],
 ['7', 'byte', 'Reserved', ' N/A  N/A  ', 'Reserved  7  byte  N/A  N/A  '],
 ['1',
  'byte',
  'Number of Ports',
  ' [0, 10]  N/A  ',
  'Number of Ports  1  byte  [0, 10]  N/A  '],
 ['10',
  'see table 78',
  'Binary Port Definitions  #ports x',
  ' Binary Port Definition  ',
  'Binary Port Definitions  #ports x 10  See Table 78: Binary Port Definition  '],
 ['2', 'byte', 'Pad  0', ' 0  N/A  ', 'Pad  0, 2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Binary_Output_Set_up']=Binary_Output_Set_up
structures["see table 77"]=Binary_Output_Set_up
        
MESSAGE_ID_VALUES[136]='Binary_Output_Set_up'

MESSAGE_VALUE_IDS['Binary_Output_Set_up']=136

MESSAGE_ID_VALUES[36]='Binary_Output_Set_up'

MESSAGE_VALUE_IDS['Binary_Output_Set_up']=36
