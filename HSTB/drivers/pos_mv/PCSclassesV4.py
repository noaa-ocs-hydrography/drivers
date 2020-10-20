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
    sdf_list = [['8', 'double', 'Time 1', 'N/A seconds ', 'Time 1 8 double N/A seconds '],
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
  'Time types 1 byte Time 1 Select Value in bits 0-3 '],
 ['1',
  'byte',
  'Distance type',
  'Distance Select Value ',
  'Distance type 1 byte Distance Select Value ']]
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
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '1 N/A ', 'Group ID 2 ushort 1 N/A '],
 ['2', 'ushort', 'Byte count', '132 bytes ', 'Byte count 2 ushort 132 bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['8',
  'double',
  'Latitude',
  '(-90, 90] degrees ',
  'Latitude 8 double (-90, 90] degrees '],
 ['8',
  'double',
  'Longitude',
  '(-180, 180] degrees ',
  'Longitude 8 double (-180, 180] degrees '],
 ['8',
  'double',
  'Altitude',
  '( , ) meters ',
  'Altitude 8 double ( , ) meters '],
 ['4',
  'float',
  'North velocity',
  '( , ) meters/second ',
  'North velocity 4 float ( , ) meters/second '],
 ['4',
  'float',
  'East velocity',
  '( , ) meters/second ',
  'East velocity 4 float ( , ) meters/second '],
 ['4',
  'float',
  'Down velocity',
  '( , ) meters/second ',
  'Down velocity 4 float ( , ) meters/second '],
 ['8',
  'double',
  'Vessel roll',
  '(-180, 180] degrees ',
  'Vessel roll 8 double (-180, 180] degrees '],
 ['8',
  'double',
  'Vessel pitch',
  '(-90, 90] degrees ',
  'Vessel pitch 8 double (-90, 90] degrees '],
 ['8',
  'double',
  'Vessel heading',
  '[0, 360) degrees ',
  'Vessel heading 8 double [0, 360) degrees '],
 ['8',
  'double',
  'Vessel wander angle',
  '(-180, 180] degrees ',
  'Vessel wander angle 8 double (-180, 180] degrees '],
 ['4',
  'float',
  'Vessel track angle',
  '[0, 360) degrees ',
  'Vessel track angle 4 float [0, 360) degrees '],
 ['4',
  'float',
  'Vessel speed',
  '[0, ) meters/second ',
  'Vessel speed 4 float [0, ) meters/second '],
 ['4',
  'float',
  'Vessel angular rate about longitudinal axis',
  '( , ) degrees/second ',
  'Vessel angular rate about longitudinal axis 4 float ( , ) degrees/second '],
 ['4',
  'float',
  'Vessel angular rate about transverse axis',
  '( , ) degrees/second ',
  'Vessel angular rate about transverse axis 4 float ( , ) degrees/second '],
 ['4',
  'float',
  'Vessel angular rate about down axis',
  '( , ) degrees/second ',
  'Vessel angular rate about down axis 4 float ( , ) degrees/second '],
 ['4',
  'float',
  'Vessel longitudinal acceleration',
  '( , ) meters/second 2 ',
  'Vessel longitudinal acceleration 4 float ( , ) meters/second 2 '],
 ['4',
  'float',
  'Vessel transverse acceleration',
  '( , ) meters/second 2 ',
  'Vessel transverse acceleration 4 float ( , ) meters/second 2 '],
 ['4',
  'float',
  'Vessel down acceleration',
  '( , ) meters/second 2 ',
  'Vessel down acceleration 4 float ( , ) meters/second 2 '],
 ['1',
  'byte',
  'Alignment status',
  'See Table 5 N/A ',
  'Alignment status 1 byte See Table 5 N/A '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
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
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '2 N/A ', 'Group ID 2 ushort 2 N/A '],
 ['2', 'ushort', 'Byte count', '80 bytes ', 'Byte count 2 ushort 80 bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4',
  'float',
  'North position RMS error',
  '[0, ) meters ',
  'North position RMS error 4 float [0, ) meters '],
 ['4',
  'float',
  'East position RMS error',
  '[0, ) meters ',
  'East position RMS error 4 float [0, ) meters '],
 ['4',
  'float',
  'Down position RMS error',
  '[0, ) meters ',
  'Down position RMS error 4 float [0, ) meters '],
 ['4',
  'float',
  'North velocity RMS error',
  '[0, ) meters/second ',
  'North velocity RMS error 4 float [0, ) meters/second '],
 ['4',
  'float',
  'East velocity RMS error',
  '[0, ) meters/second ',
  'East velocity RMS error 4 float [0, ) meters/second '],
 ['4',
  'float',
  'Down velocity RMS error',
  '[0, ) meters/second ',
  'Down velocity RMS error 4 float [0, ) meters/second '],
 ['4',
  'float',
  'Roll RMS error',
  '[0, ) degrees ',
  'Roll RMS error 4 float [0, ) degrees '],
 ['4',
  'float',
  'Pitch RMS error',
  '[0, ) degrees ',
  'Pitch RMS error 4 float [0, ) degrees '],
 ['4',
  'float',
  'Heading RMS error',
  '[0, ) degrees ',
  'Heading RMS error 4 float [0, ) degrees '],
 ['4',
  'float',
  'Error ellipsoid semi-major',
  '[0, ) meters ',
  'Error ellipsoid semi-major 4 float [0, ) meters '],
 ['4',
  'float',
  'Error ellipsoid semi-minor',
  '[0, ) meters ',
  'Error ellipsoid semi-minor 4 float [0, ) meters '],
 ['4',
  'float',
  'Error ellipsoid orientation',
  '(0, 360] degrees ',
  'Error ellipsoid orientation 4 float (0, 360] degrees '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
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

class GPS_receiver_channel_status_data(BaseField):
    FieldTag="GPS_receiver_channel_status_data"
    sdf_list = [['2', 'ushort', 'SV PRN', '[1, 40] N/A ', 'SV PRN 2 ushort [1, 40] N/A '],
 ['2',
  'ushort',
  'Channel tracking status',
  'See Table 10 N/A ',
  'Channel tracking status 2 ushort See Table 10 N/A '],
 ['4',
  'float',
  'SV azimuth',
  '[0, 360) degrees ',
  'SV azimuth 4 float [0, 360) degrees '],
 ['4',
  'float',
  'SV elevation',
  '[0, 90] degrees ',
  'SV elevation 4 float [0, 90] degrees '],
 ['4', 'float', 'SV L1 SNR', '[0, ) dB ', 'SV L1 SNR 4 float [0, ) dB '],
 ['4', 'float', 'SV L2 SNR', '[0, ) dB ', 'SV L2 SNR 4 float [0, ) dB ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GPS_receiver_channel_status_data']=GPS_receiver_channel_status_data
structures["see table 8"]=GPS_receiver_channel_status_data
        
class GPS_navigation_solution_status(BaseField):
    FieldTag="GPS_navigation_solution_status"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GPS_navigation_solution_status']=GPS_navigation_solution_status
structures["see table 9"]=GPS_navigation_solution_status
        
class GPS_channel_status(BaseField):
    FieldTag="GPS_channel_status"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GPS_channel_status']=GPS_channel_status
structures["see table 10"]=GPS_channel_status
        
class GPS_receiver_type(BaseField):
    FieldTag="GPS_receiver_type"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GPS_receiver_type']=GPS_receiver_type
structures["see table 11"]=GPS_receiver_type
        
class Trimble_BD950_GPS_receiver_status(BaseField):
    FieldTag="Trimble_BD950_GPS_receiver_status"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Trimble_BD950_GPS_receiver_status']=Trimble_BD950_GPS_receiver_status
structures["see table 12"]=Trimble_BD950_GPS_receiver_status
        
class Time_tagged_IMU_data(BaseField):
    FieldTag="Time_tagged_IMU_data"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '4 N/A ', 'Group ID 2 ushort 4 N/A '],
 ['2', 'ushort', 'Byte count', '60 bytes ', 'Byte count 2 ushort 60 bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3'],
 ['29', 'byte', 'IMU Data', '', 'IMU Data 29 byte '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
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
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '5 or 6 N/A ', 'Group ID 2 ushort 5 or 6 N/A '],
 ['2', 'ushort', 'Byte count', '36 bytes ', 'Byte count 2 ushort 36 bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4',
  'ulong',
  'Event pulse number',
  '[0, ) N/A ',
  'Event pulse number 4 ulong [0, ) N/A '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
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
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '7 N/A ', 'Group ID 2 ushort 7 N/A '],
 ['2', 'ushort', 'Byte count', '36 bytes ', 'Byte count 2 ushort 36 bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4', 'ulong', 'PPS count', '[0, ) N/A ', 'PPS count 4 ulong [0, ) N/A '],
 ['1',
  'byte',
  'Time synchronization status',
  '0 Not synchronized ',
  'Time synchronization status 1 byte 0 Not synchronized '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group End', '$# N/A ', 'Group End 2 char $# N/A ']]
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

class GAMS_Solution_Status(BaseField):
    FieldTag="GAMS_Solution_Status"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '9 N/A ', 'Group ID 2 ushort 9 N/A '],
 ['2', 'ushort', 'Byte count', '72 bytes ', 'Byte count 2 ushort 72 bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['1',
  'ubyte',
  'Number of satellites',
  'N/A N/A ',
  'Number of satellites 1 ubyte N/A N/A '],
 ['4',
  'float',
  'A priori PDOP',
  '[0, 999] N/A ',
  'A priori PDOP 4 float [0, 999] N/A '],
 ['4',
  'float',
  'Computed antenna separation',
  '[0, ) meters ',
  'Computed antenna separation 4 float [0, ) meters '],
 ['1',
  'byte',
  'Solution Status',
  '0 fixed integer ',
  'Solution Status 1 byte 0 fixed integer '],
 ['12',
  'byte',
  'PRN assignment',
  'Each byte contains 0-32 where ',
  'PRN assignment 12 byte Each byte contains 0-32 where '],
 ['2',
  'ushort',
  'Cycle slip flag',
  'Bits 0-11: (k-1) th bit set to 1 implies cycle slip ',
  'Cycle slip flag 2 ushort Bits 0-11: (k-1) th bit set to 1 implies cycle slip '],
 ['8',
  'double',
  'GAMS heading',
  '[0,360) Degrees ',
  'GAMS heading 8 double [0,360) Degrees '],
 ['8',
  'double',
  'GAMS heading RMS error',
  '(0, ) Degrees ',
  'GAMS heading RMS error 8 double (0, ) Degrees '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GAMS_Solution_Status']=GAMS_Solution_Status
structures["see table 16"]=GAMS_Solution_Status
        
GROUP_ID_VALUES[9]='GAMS_Solution_Status'

GROUP_VALUE_IDS['GAMS_Solution_Status']=9

class General_and_FDIR_status(BaseField):
    FieldTag="General_and_FDIR_status"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '10 N/A ', 'Group ID 2 ushort 10 N/A '],
 ['2', 'ushort', 'Byte count', '56 Bytes ', 'Byte count 2 ushort 56 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4',
  'ulong',
  'General Status A',
  'Coarse levelling active bit 0: set ',
  'General Status A 4 ulong Coarse levelling active bit 0: set '],
 ['4',
  'ulong',
  'General Status B',
  'User attitude RMS performance bit 0: set ',
  'General Status B 4 ulong User attitude RMS performance bit 0: set '],
 ['4',
  'ulong',
  'General Status C',
  'Gimbal input ON bit 0: set ',
  'General Status C 4 ulong Gimbal input ON bit 0: set '],
 ['4',
  'ulong',
  'FDIR Level 1 status',
  'IMU-POS checksum error bit 0: set ',
  'FDIR Level 1 status 4 ulong IMU-POS checksum error bit 0: set '],
 ['2',
  'ushort',
  'FDIR Level 1 IMU failures',
  'Shows number of FDIR Level 1 Status IMU failures ',
  'FDIR Level 1 IMU failures 2 ushort Shows number of FDIR Level 1 Status IMU failures '],
 ['2',
  'ushort',
  'FDIR Level 2 status',
  'Inertial speed exceeds max bit 0: set ',
  'FDIR Level 2 status 2 ushort Inertial speed exceeds max bit 0: set '],
 ['2',
  'ushort',
  'FDIR Level 3 status',
  'Spare bits: 0-15 ',
  'FDIR Level 3 status 2 ushort Spare bits: 0-15 '],
 ['2',
  'ushort',
  'FDIR Level 4 status',
  'Primary GPS position rejected bit 0: set ',
  'FDIR Level 4 status 2 ushort Primary GPS position rejected bit 0: set '],
 ['2',
  'ushort',
  'FDIR Level 5 status',
  'X accelerometer failure bit 0: set ',
  'FDIR Level 5 status 2 ushort X accelerometer failure bit 0: set '],
 ['0', 'byte', 'Pad', '0 N/A ', 'Pad 0 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['General_and_FDIR_status']=General_and_FDIR_status
structures["see table 17"]=General_and_FDIR_status
        
GROUP_ID_VALUES[10]='General_and_FDIR_status'

GROUP_VALUE_IDS['General_and_FDIR_status']=10

class Secondary_GPS_status(BaseField):
    FieldTag="Secondary_GPS_status"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '11 N/A ', 'Group ID 2 ushort 11 N/A '],
 ['2',
  'ushort',
  'Byte count',
  '76 + 20 x (number of ',
  'Byte count 2 ushort 76 + 20 x (number of '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['1',
  'byte',
  'Navigation solution status',
  'See Table 9 N/A ',
  'Navigation solution status 1 byte See Table 9 N/A '],
 ['1',
  'byte',
  'Number of SV tracked',
  '[0, 12] N/A ',
  'Number of SV tracked 1 byte [0, 12] N/A '],
 ['2',
  'ushort',
  'Channel status byte count',
  '[0, 240] Bytes ',
  'Channel status byte count 2 ushort [0, 240] Bytes '],
 ['variable',
  'see table 8',
  'Channel status',
  '',
  'Channel status variable See Table 8 '],
 ['4', 'float', 'HDOP', '(0, ) N/A ', 'HDOP 4 float (0, ) N/A '],
 ['4', 'float', 'VDOP', '(0, ) N/A ', 'VDOP 4 float (0, ) N/A '],
 ['4',
  'float',
  'DGPS correction latency',
  '[0, 99.9] Seconds ',
  'DGPS correction latency 4 float [0, 99.9] Seconds '],
 ['2',
  'ushort',
  'DGPS reference ID',
  '[0, 1023] N/A ',
  'DGPS reference ID 2 ushort [0, 1023] N/A '],
 ['4',
  'ulong',
  'GPS/UTC week number',
  '[0, 1023] 0 if not available Week ',
  'GPS/UTC week number 4 ulong [0, 1023] 0 if not available Week '],
 ['8',
  'double',
  'GPS/UTC time offset',
  '( , 0] (GPS time - UTC time) Seconds ',
  'GPS/UTC time offset 8 double ( , 0] (GPS time - UTC time) Seconds '],
 ['4',
  'float',
  'GPS navigation message latency',
  '[0, ) Seconds ',
  'GPS navigation message latency 4 float [0, ) Seconds '],
 ['4',
  'float',
  'Geoidal separation',
  '( , ) Meters ',
  'Geoidal separation 4 float ( , ) Meters '],
 ['2',
  'ushort',
  'GPS receiver type',
  'See Table 11 N/A ',
  'GPS receiver type 2 ushort See Table 11 N/A '],
 ['4',
  'ulong',
  'GPS status',
  'GPS summary status fields which depend ',
  'GPS status 4 ulong GPS summary status fields which depend '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Secondary_GPS_status']=Secondary_GPS_status
structures["see table 18"]=Secondary_GPS_status
        
GROUP_ID_VALUES[11]='Secondary_GPS_status'

GROUP_VALUE_IDS['Secondary_GPS_status']=11

class Auxiliary_1_2_GPS_status(BaseField):
    FieldTag="Auxiliary_1_2_GPS_status"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  '12 or 13 N/A ',
  'Group ID 2 ushort 12 or 13 N/A '],
 ['2',
  'ushort',
  'Byte count',
  '72 + 20 x (number of ',
  'Byte count 2 ushort 72 + 20 x (number of '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['1',
  'byte',
  'Navigation solution status',
  'See Table 9 N/A ',
  'Navigation solution status 1 byte See Table 9 N/A '],
 ['1',
  'byte',
  'Number of SV Tracked',
  '[0, 40] N/A ',
  'Number of SV Tracked 1 byte [0, 40] N/A '],
 ['2',
  'ushort',
  'Channel status byte count',
  '[0, ) Bytes ',
  'Channel status byte count 2 ushort [0, ) Bytes '],
 ['variable',
  'see table 8',
  'Channel status',
  '',
  'Channel status variable See Table 8 '],
 ['4', 'float', 'HDOP', '(0, ) N/A ', 'HDOP 4 float (0, ) N/A '],
 ['4', 'float', 'VDOP', '(0, ) N/A ', 'VDOP 4 float (0, ) N/A '],
 ['4',
  'float',
  'DGPS correction latency',
  '(0, ) Seconds ',
  'DGPS correction latency 4 float (0, ) Seconds '],
 ['2',
  'ushort',
  'DGPS reference ID',
  '[0, 1023] N/A ',
  'DGPS reference ID 2 ushort [0, 1023] N/A '],
 ['4',
  'ulong',
  'GPS/UTC week number',
  '[0, 1023] ',
  'GPS/UTC week number 4 ulong [0, 1023] '],
 ['8',
  'double',
  'GPS time offset',
  '( , 0] Seconds (GPS time - UTC time) ',
  'GPS time offset 8 double ( , 0] Seconds (GPS time - UTC time) '],
 ['4',
  'float',
  'GPS navigation message latency',
  '[0, ) Seconds ',
  'GPS navigation message latency 4 float [0, ) Seconds '],
 ['4',
  'float',
  'Geoidal separation',
  'N/A Meters ',
  'Geoidal separation 4 float N/A Meters '],
 ['2',
  'ushort',
  'NMEA messages Received',
  'Bit (set) NMEA Message ',
  'NMEA messages Received 2 ushort Bit (set) NMEA Message '],
 ['1',
  'byte',
  'Aux 1/2 in Use 1',
  '0 Not in use ',
  'Aux 1/2 in Use 1 1 byte 0 Not in use '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Auxiliary_1_2_GPS_status']=Auxiliary_1_2_GPS_status
structures["see table 19"]=Auxiliary_1_2_GPS_status
        
GROUP_ID_VALUES[12]='Auxiliary_1_2_GPS_status'

GROUP_VALUE_IDS['Auxiliary_1_2_GPS_status']=12

GROUP_ID_VALUES[13]='Auxiliary_1_2_GPS_status'

GROUP_VALUE_IDS['Auxiliary_1_2_GPS_status']=13

class Calibrated_installation_parameters(BaseField):
    FieldTag="Calibrated_installation_parameters"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '14 N/A ', 'Group ID 2 ushort 14 N/A '],
 ['2', 'ushort', 'Byte count', '116 Bytes ', 'Byte count 2 ushort 116 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['2',
  'ushort',
  'Calibration status',
  'See Table 21 for bitfield ',
  'Calibration status 2 ushort See Table 21 for bitfield '],
 ['4',
  'float',
  'Reference to Primary GPS X lever arm',
  '( , ) Meters ',
  'Reference to Primary GPS X lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to Primary GPS Y lever arm',
  '( , ) Meters ',
  'Reference to Primary GPS Y lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to Primary GPS Z lever arm',
  '( , ) Meters ',
  'Reference to Primary GPS Z lever arm 4 float ( , ) Meters '],
 ['2',
  'ushort',
  'Reference to Primary GPS lever arm calibration FOM',
  '[0, 100] N/A ',
  'Reference to Primary GPS lever arm calibration FOM 2 ushort [0, 100] N/A '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS X lever arm',
  '( , ) Meters ',
  'Reference to Auxiliary 1 GPS X lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS Y lever arm',
  '( , ) Meters ',
  'Reference to Auxiliary 1 GPS Y lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS Z lever arm',
  '( , ) Meters ',
  'Reference to Auxiliary 1 GPS Z lever arm 4 float ( , ) Meters '],
 ['2',
  'ushort',
  'Reference to Auxiliary 1 GPS lever arm calibration FOM',
  '[0, 100] N/A ',
  'Reference to Auxiliary 1 GPS lever arm calibration FOM 2 ushort [0, 100] N/A '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS X lever arm',
  '( , ) Meters ',
  'Reference to Auxiliary 2 GPS X lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS Y lever arm',
  '( , ) Meters ',
  'Reference to Auxiliary 2 GPS Y lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS Z lever arm',
  '( , ) Meters ',
  'Reference to Auxiliary 2 GPS Z lever arm 4 float ( , ) Meters '],
 ['2',
  'ushort',
  'Reference to Auxiliary 2 GPS lever arm calibration FOM',
  '[0, 100] N/A ',
  'Reference to Auxiliary 2 GPS lever arm calibration FOM 2 ushort [0, 100] N/A '],
 ['4',
  'float',
  'Reference to DMI X lever arm',
  '( , ) Meters ',
  'Reference to DMI X lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to DMI Y lever arm',
  '( , ) Meters ',
  'Reference to DMI Y lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to DMI Z lever arm',
  '( , ) Meters ',
  'Reference to DMI Z lever arm 4 float ( , ) Meters '],
 ['2',
  'ushort',
  'Reference to DMI lever arm calibration FOM',
  '[0, 100] N/A ',
  'Reference to DMI lever arm calibration FOM 2 ushort [0, 100] N/A '],
 ['4',
  'float',
  'DMI scale factor',
  '( , ) % ',
  'DMI scale factor 4 float ( , ) % '],
 ['2',
  'ushort',
  'DMI scale factor calibration FOM',
  '[0, 100] N/A ',
  'DMI scale factor calibration FOM 2 ushort [0, 100] N/A '],
 ['4',
  'float',
  'Reference to DVS X lever arm',
  '( , ) Meters ',
  'Reference to DVS X lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to DVS Y lever arm',
  '( , ) Meters ',
  'Reference to DVS Y lever arm 4 float ( , ) Meters '],
 ['4',
  'float',
  'Reference to DVS Z lever arm',
  '( , ) meters ',
  'Reference to DVS Z lever arm 4 float ( , ) meters '],
 ['4',
  'float',
  'DVS scale factor',
  '( , ) % ',
  'DVS scale factor 4 float ( , ) % '],
 ['2',
  'ushort',
  'DVS scale factor calibration FOM',
  '[0, 100] N/A ',
  'DVS scale factor calibration FOM 2 ushort [0, 100] N/A '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Calibrated_installation_parameters']=Calibrated_installation_parameters
structures["see table 20"]=Calibrated_installation_parameters
        
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
structures["see table 21"]=IIN_Calibration_Status
        
class User_Time_Status(BaseField):
    FieldTag="User_Time_Status"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '17 N/A ', 'Group ID 2 ushort 17 N/A '],
 ['2', 'ushort', 'Byte count', '40 Bytes ', 'Byte count 2 ushort 40 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4',
  'ulong',
  'Number of Time Synch message rejections',
  '[0, ) N/A ',
  'Number of Time Synch message rejections 4 ulong [0, ) N/A '],
 ['4',
  'ulong',
  'Number of User Time resynchronizations',
  '[0, ) N/A ',
  'Number of User Time resynchronizations 4 ulong [0, ) N/A '],
 ['1',
  'byte',
  'User time valid',
  '1 or 0 N/A ',
  'User time valid 1 byte 1 or 0 N/A '],
 ['1',
  'byte',
  'Time Synch message received',
  '1 or 0 N/A ',
  'Time Synch message received 1 byte 1 or 0 N/A '],
 ['0', 'byte', 'Pad', '0 N/A ', 'Pad 0 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['User_Time_Status']=User_Time_Status
structures["see table 22"]=User_Time_Status
        
GROUP_ID_VALUES[17]='User_Time_Status'

GROUP_VALUE_IDS['User_Time_Status']=17

class IIN_solution_status(BaseField):
    FieldTag="IIN_solution_status"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '20 N/A ', 'Group ID 2 ushort 20 N/A '],
 ['2', 'ushort', 'Byte count', '60 Bytes ', 'Byte count 2 ushort 60 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['2',
  'ushort',
  'Number of satellites',
  '[0, 12] N/A ',
  'Number of satellites 2 ushort [0, 12] N/A '],
 ['4',
  'float',
  'A priori PDOP',
  '[0, 999] N/A ',
  'A priori PDOP 4 float [0, 999] N/A '],
 ['4',
  'float',
  'Baseline length',
  '[0, ) Meters ',
  'Baseline length 4 float [0, ) Meters '],
 ['2',
  'ushort',
  'IIN processing status',
  '1 Fixed Narrow Lane RTK ',
  'IIN processing status 2 ushort 1 Fixed Narrow Lane RTK '],
 ['12',
  'byte',
  'PRN assignment 12',
  'Each byte contains 0-40 where ',
  'PRN assignment 12 12 byte Each byte contains 0-40 where '],
 ['2',
  'ushort',
  'L1 cycle slip flag',
  'Bits 0-11: (k-1) th bit set to 1 implies L1 cycle ',
  'L1 cycle slip flag 2 ushort Bits 0-11: (k-1) th bit set to 1 implies L1 cycle '],
 ['2',
  'ushort',
  'L2 cycle slip flag',
  'Bits 0-11: (k-1) th bit set to 1 implies L2 cycle ',
  'L2 cycle slip flag 2 ushort Bits 0-11: (k-1) th bit set to 1 implies L2 cycle '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['IIN_solution_status']=IIN_solution_status
structures["see table 23"]=IIN_solution_status
        
GROUP_ID_VALUES[20]='IIN_solution_status'

GROUP_VALUE_IDS['IIN_solution_status']=20

class Base_GPS_1_2_Modem_Status(BaseField):
    FieldTag="Base_GPS_1_2_Modem_Status"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  '21 or 22 N/A ',
  'Group ID 2 ushort 21 or 22 N/A '],
 ['2', 'ushort', 'Byte count', '116 Bytes ', 'Byte count 2 ushort 116 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['16',
  'char',
  'Modem response',
  'N/A N/A ',
  'Modem response 16 char N/A N/A '],
 ['48',
  'char',
  'Connection status',
  'N/A N/A ',
  'Connection status 48 char N/A N/A '],
 ['4',
  'ulong',
  'Number of redials per disconnect',
  '[0, ) N/A ',
  'Number of redials per disconnect 4 ulong [0, ) N/A '],
 ['4',
  'ulong',
  'Maximum number of redials per disconnect',
  '[0, ) N/A ',
  'Maximum number of redials per disconnect 4 ulong [0, ) N/A '],
 ['4',
  'ulong',
  'Number of disconnects',
  '[0, ) N/A ',
  'Number of disconnects 4 ulong [0, ) N/A '],
 ['4',
  'ulong',
  'Data gap length',
  '[0, ) N/A ',
  'Data gap length 4 ulong [0, ) N/A '],
 ['4',
  'ulong',
  'Maximum data gap length',
  '[0, ) N/A ',
  'Maximum data gap length 4 ulong [0, ) N/A '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Base_GPS_1_2_Modem_Status']=Base_GPS_1_2_Modem_Status
structures["see table 24"]=Base_GPS_1_2_Modem_Status
        
GROUP_ID_VALUES[21]='Base_GPS_1_2_Modem_Status'

GROUP_VALUE_IDS['Base_GPS_1_2_Modem_Status']=21

GROUP_ID_VALUES[22]='Base_GPS_1_2_Modem_Status'

GROUP_VALUE_IDS['Base_GPS_1_2_Modem_Status']=22

class Auxiliary_1_2_GPS_raw_display_data(BaseField):
    FieldTag="Auxiliary_1_2_GPS_raw_display_data"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  '10007 or 10008 N/A ',
  'Group ID 2 ushort 10007 or 10008 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'variable Bytes ',
  'Byte count 2 ushort variable Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['6', 'byte', 'Reserved', 'N/A N/A ', 'Reserved 6 byte N/A N/A '],
 ['2',
  'ushort',
  'Variable message byte count',
  '[0, ) Bytes ',
  'Variable message byte count 2 ushort [0, ) Bytes '],
 ['variable',
  'char',
  'Auxiliary GPS raw data',
  'N/A N/A ',
  'Auxiliary GPS raw data variable char N/A N/A '],
 ['0-3', 'byte', 'Pad', '0 N/A ', 'Pad 0-3 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Auxiliary_1_2_GPS_raw_display_data']=Auxiliary_1_2_GPS_raw_display_data
structures["see table 25"]=Auxiliary_1_2_GPS_raw_display_data
        
GROUP_ID_VALUES[10007]='Auxiliary_1_2_GPS_raw_display_data'

GROUP_VALUE_IDS['Auxiliary_1_2_GPS_raw_display_data']=10007

GROUP_ID_VALUES[10008]='Auxiliary_1_2_GPS_raw_display_data'

GROUP_VALUE_IDS['Auxiliary_1_2_GPS_raw_display_data']=10008

class Versions_and_statistics(BaseField):
    FieldTag="Versions_and_statistics"
    sdf_list = [['4', 'char', 'Group Start', '$GRP N/A ', 'Group Start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '99 N/A ', 'Group ID 2 ushort 99 N/A '],
 ['2', 'ushort', 'Byte count', '332 Bytes ', 'Byte Count 2 ushort 332 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['120',
  'char',
  'System version',
  'Product - Model, Version, ',
  'System version 120 char Product - Model, Version, '],
 ['80',
  'char',
  'Primary GPS version',
  'Available information is displayed, eg: ',
  'Primary GPS version 80 char Available information is displayed, eg: '],
 ['80',
  'char',
  'Secondary GPS version',
  'Available information is displayed, eg: ',
  'Secondary GPS version 80 char Available information is displayed, eg: '],
 ['4',
  'float',
  'Total hours',
  '[0, ) 0.1 hour resolution Hours ',
  'Total hours 4 float [0, ) 0.1 hour resolution Hours '],
 ['4',
  'ulong',
  'Number of runs',
  '[0, ) N/A ',
  'Number of runs 4 ulong [0, ) N/A '],
 ['4',
  'float',
  'Average length of run',
  '[0, ) 0.1 hour resolution Hours ',
  'Average length of run 4 float [0, ) 0.1 hour resolution Hours '],
 ['4',
  'float',
  'Longest run',
  '[0, ) 0.1 hour resolution Hours ',
  'Longest run 4 float [0, ) 0.1 hour resolution Hours '],
 ['4',
  'float',
  'Current run',
  '[0, ) 0.1 hour resolution Hours ',
  'Current run 4 float [0, ) 0.1 hour resolution Hours '],
 ['2', 'short', 'Pad', '0 N/A ', 'Pad 2 short 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group End', '$# N/A ', 'Group End 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Versions_and_statistics']=Versions_and_statistics
structures["see table 26"]=Versions_and_statistics
        
GROUP_ID_VALUES[99]='Versions_and_statistics'

GROUP_VALUE_IDS['Versions_and_statistics']=99

class Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics(BaseField):
    FieldTag="Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  '102 or 103 N/A ',
  'Group ID 2 ushort 102 or 103 N/A '],
 ['2', 'ushort', 'Byte count', '128 Bytes ', 'Byte count 2 ushort 128 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['8',
  'double',
  'Latitude',
  '(-90, 90] Deg ',
  'Latitude 8 double (-90, 90] Deg '],
 ['8',
  'double',
  'Longitude',
  '(-180, 180] Deg ',
  'Longitude 8 double (-180, 180] Deg '],
 ['8', 'double', 'Altitude', '( , ) M ', 'Altitude 8 double ( , ) M '],
 ['4',
  'float',
  'Along track velocity',
  '( , ) m/s ',
  'Along track velocity 4 float ( , ) m/s '],
 ['4',
  'float',
  'Across track velocity',
  '( , ) m/s ',
  'Across track velocity 4 float ( , ) m/s '],
 ['4',
  'float',
  'Down velocity',
  '( , ) m/s ',
  'Down velocity 4 float ( , ) m/s '],
 ['8', 'double', 'Roll', '(-180, 180] Deg ', 'Roll 8 double (-180, 180] Deg '],
 ['8', 'double', 'Pitch', '(-90, 90] Deg ', 'Pitch 8 double (-90, 90] Deg '],
 ['8', 'double', 'Heading', '[0, 360) Deg ', 'Heading 8 double [0, 360) Deg '],
 ['8',
  'double',
  'Wander angle',
  '(-180, 180] Deg ',
  'Wander angle 8 double (-180, 180] Deg '],
 ['4', 'float', 'Heave 1', '( , ) M ', 'Heave 1 4 float ( , ) M '],
 ['4',
  'float',
  'Angular rate about longitudinal axis',
  '( , ) deg/s ',
  'Angular rate about longitudinal axis 4 float ( , ) deg/s '],
 ['4',
  'float',
  'Angular rate about transverse axis',
  '( , ) deg/s ',
  'Angular rate about transverse axis 4 float ( , ) deg/s '],
 ['4',
  'float',
  'Angular rate about down axis',
  '( , ) deg/s ',
  'Angular rate about down axis 4 float ( , ) deg/s '],
 ['4',
  'float',
  'Longitudinal acceleration',
  '( , ) m/s 2 ',
  'Longitudinal acceleration 4 float ( , ) m/s 2 '],
 ['4',
  'float',
  'Transverse acceleration',
  '( , ) m/s 2 ',
  'Transverse acceleration 4 float ( , ) m/s 2 '],
 ['4',
  'float',
  'Down acceleration',
  '( , ) m/s 2 ',
  'Down acceleration 4 float ( , ) m/s 2 '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics']=Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics
structures["see table 27"]=Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics
        
GROUP_ID_VALUES[102]='Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics'

GROUP_VALUE_IDS['Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics']=102

GROUP_ID_VALUES[103]='Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics'

GROUP_VALUE_IDS['Sensor_1_2_Position_Velocity_Attitude_Heave_Dynamics']=103

class Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics(BaseField):
    FieldTag="Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  '104 or 105 N/A ',
  'Group ID 2 ushort 104 or 105 N/A '],
 ['2', 'ushort', 'Byte count', '68 Bytes ', 'Byte count 2 ushort 68 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4',
  'float',
  'N position RMS',
  '[0, ) M ',
  'N position RMS 4 float [0, ) M '],
 ['4',
  'float',
  'E position RMS',
  '[0, ) M ',
  'E position RMS 4 float [0, ) M '],
 ['4',
  'float',
  'D position RMS',
  '[0, ) M ',
  'D position RMS 4 float [0, ) M '],
 ['4',
  'float',
  'Along track velocity RMS error',
  '[0, ) m/s ',
  'Along track velocity RMS error 4 float [0, ) m/s '],
 ['4',
  'float',
  'Across track velocity RMS error',
  '[0, ) m/s ',
  'Across track velocity RMS error 4 float [0, ) m/s '],
 ['4',
  'float',
  'Down velocity RMS error',
  '[0, ) m/s ',
  'Down velocity RMS error 4 float [0, ) m/s '],
 ['4',
  'float',
  'Roll RMS error',
  '[0, ) Deg ',
  'Roll RMS error 4 float [0, ) Deg '],
 ['4',
  'float',
  'Pitch RMS error',
  '[0, ) Deg ',
  'Pitch RMS error 4 float [0, ) Deg '],
 ['4',
  'float',
  'Heading RMS error',
  '[0, ) Deg ',
  'Heading RMS error 4 float [0, ) Deg '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics']=Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics
structures["see table 28"]=Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics
        
GROUP_ID_VALUES[104]='Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics'

GROUP_VALUE_IDS['Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics']=104

GROUP_ID_VALUES[105]='Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics'

GROUP_VALUE_IDS['Sensor_1_2_Position_Velocity_and_Attitude_Performance_Metrics']=105

class MV_General_Status_FDIR(BaseField):
    FieldTag="MV_General_Status_FDIR"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '110 N/A ', 'Group ID 2 ushort 110 N/A '],
 ['2', 'ushort', 'Byte count', '32 Bytes ', 'Byte count 2 ushort 32 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4',
  'ulong',
  'General Status',
  'User logged in bit 0: set -- doc error; said 2 byte ulong, but need 32 bits (4 byte ulong)  ',
  'General Status 4 ulong User logged in bit 0: set -- doc error; said 2 byte ulong, but need 32 bits (4 byte ulong)  '],
 ['2',
  'byte',
  'Pad',
  '0 -- doc error, with general status as 4 then pad needs to be 2 ',
  'Pad 2 byte 0 -- doc error, with general status as 4 then pad needs to be 2 '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['MV_General_Status_FDIR']=MV_General_Status_FDIR
structures["see table 29"]=MV_General_Status_FDIR
        
GROUP_ID_VALUES[110]='MV_General_Status_FDIR'

GROUP_VALUE_IDS['MV_General_Status_FDIR']=110

class Heave_True_Heave_Data(BaseField):
    FieldTag="Heave_True_Heave_Data"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '111 N/A ', 'Group ID 2 ushort 111 N/A '],
 ['2', 'ushort', 'Byte count', '76 Bytes ', 'Byte count 2 ushort 76 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4', 'float', 'True Heave', '( , ) M ', 'True Heave 4 float ( , ) M '],
 ['4',
  'float',
  'True Heave RMS',
  '[0, ) M ',
  'True Heave RMS 4 float [0, ) M '],
 ['4',
  'ulong',
  'Status',
  'True Heave Valid bit 0: set ',
  'Status 4 ulong True Heave Valid bit 0: set '],
 ['4', 'float', 'Heave', '( , ) M ', 'Heave 4 float ( , ) M '],
 ['4', 'float', 'Heave RMS', '[0, ) M ', 'Heave RMS 4 float [0, ) M '],
 ['8', 'double', 'Heave Time 1', 'N/A Sec ', 'Heave Time 1 8 double N/A Sec '],
 ['8', 'double', 'Heave Time 2', 'N/A Sec ', 'Heave Time 2 8 double N/A Sec '],
 ['4',
  'ulong',
  'Rejected IMU Data Count',
  '[0, ) N/A ',
  'Rejected IMU Data Count 4 ulong [0, ) N/A '],
 ['4',
  'ulong',
  'Out of Range IMU Data Count',
  '[0, ) N/A ',
  'Out of Range IMU Data Count 4 ulong [0, ) N/A '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Heave_True_Heave_Data']=Heave_True_Heave_Data
structures["see table 30"]=Heave_True_Heave_Data
        
GROUP_ID_VALUES[111]='Heave_True_Heave_Data'

GROUP_VALUE_IDS['Heave_True_Heave_Data']=111

class NMEA_Strings(BaseField):
    FieldTag="NMEA_Strings"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '112 N/A ', 'Group ID 2 ushort 112 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'variable Bytes ',
  'Byte count 2 ushort variable Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['2',
  'ushort',
  'Variable group byte count',
  '[0, ) N/A- error in docs list this as 2 byte float, guessing it should be a ushort',
  'Variable group byte count 2 ushort [0, ) N/A- error in docs list this as 2 byte float, guessing it should be a ushort'],
 ['variable',
  'char',
  'NMEA strings',
  'N/A N/A ',
  'NMEA strings variable char N/A N/A '],
 ['0-3', 'byte', 'Pad', '0 N/A ', 'Pad 0-3 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['NMEA_Strings']=NMEA_Strings
structures["see table 31"]=NMEA_Strings
        
GROUP_ID_VALUES[112]='NMEA_Strings'

GROUP_VALUE_IDS['NMEA_Strings']=112

class Heave_True_Heave_Performance_Metrics(BaseField):
    FieldTag="Heave_True_Heave_Performance_Metrics"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '113 N/A ', 'Group ID 2 ushort 113 N/A '],
 ['2', 'ushort', 'Byte count', '68 Bytes ', 'Byte count 2 ushort 68 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['8', 'double', 'Heave Time 1', 'N/A Sec ', 'Heave Time 1 8 double N/A Sec '],
 ['8',
  'double',
  'Quality Control 1',
  'N/A N/A ',
  'Quality Control 1 8 double N/A N/A '],
 ['8',
  'double',
  'Quality Control 2',
  'N/A N/A ',
  'Quality Control 2 8 double N/A N/A '],
 ['8',
  'double',
  'Quality Control 3',
  'N/A N/A ',
  'Quality Control 3 8 double N/A N/A '],
 ['4',
  'ulong',
  'Status',
  'Quality Control 1 Valid bit 0: set ',
  'Status 4 ulong Quality Control 1 Valid bit 0: set '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Heave_True_Heave_Performance_Metrics']=Heave_True_Heave_Performance_Metrics
structures["see table 32"]=Heave_True_Heave_Performance_Metrics
        
GROUP_ID_VALUES[113]='Heave_True_Heave_Performance_Metrics'

GROUP_VALUE_IDS['Heave_True_Heave_Performance_Metrics']=113

class TrueZ_TrueTide_Data(BaseField):
    FieldTag="TrueZ_TrueTide_Data"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '114 N/A ', 'Group ID 2 ushort 114 N/A '],
 ['2', 'ushort', 'Byte count', '76 Bytes ', 'Byte count 2 ushort 76 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4', 'float', 'Delayed TrueZ', '( , ) M ', 'Delayed TrueZ 4 float ( , ) M '],
 ['4',
  'float',
  'Delayed TrueZ RMS',
  '[0, ) M ',
  'Delayed TrueZ RMS 4 float [0, ) M '],
 ['4',
  'float',
  'Delayed TrueTide',
  '( , ) M ',
  'Delayed TrueTide 4 float ( , ) M '],
 ['4',
  'ulong',
  'Status',
  'Delayed TrueZ Valid bit 0: set ',
  'Status 4 ulong Delayed TrueZ Valid bit 0: set '],
 ['4', 'float', 'TrueZ', '( , ) M ', 'TrueZ 4 float ( , ) M '],
 ['4', 'float', 'TrueZ RMS', '[0, ) M ', 'TrueZ RMS 4 float [0, ) M '],
 ['4', 'float', 'TrueTide', '( , ) M ', 'TrueTide 4 float ( , ) M '],
 ['8', 'double', 'TrueZ Time 1', 'N/A Sec ', 'TrueZ Time 1 8 double N/A Sec '],
 ['8', 'double', 'TrueZ Time 2', 'N/A Sec ', 'TrueZ Time 2 8 double N/A Sec '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['TrueZ_TrueTide_Data']=TrueZ_TrueTide_Data
structures["see table 33"]=TrueZ_TrueTide_Data
        
GROUP_ID_VALUES[114]='TrueZ_TrueTide_Data'

GROUP_VALUE_IDS['TrueZ_TrueTide_Data']=114

class Primary_GPS_data_stream(BaseField):
    FieldTag="Primary_GPS_data_stream"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '10001 N/A ', 'Group ID 2 ushort 10001 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'variable Bytes ',
  'Byte count 2 ushort variable Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['2',
  'ushort',
  'GPS receiver type',
  'See Table 11 N/A ',
  'GPS receiver type 2 ushort See Table 11 N/A '],
 ['4', 'long', 'Reserved', 'N/A N/A ', 'Reserved 4 long N/A N/A '],
 ['2',
  'ushort',
  'Variable message byte count',
  '[0, ) Bytes ',
  'Variable message byte count 2 ushort [0, ) Bytes '],
 ['variable',
  'char',
  'GPS Receiver raw data',
  'N/A N/A ',
  'GPS Receiver raw data variable char N/A N/A '],
 ['0-3', 'byte', 'Pad', '0 N/A ', 'Pad 0-3 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Primary_GPS_data_stream']=Primary_GPS_data_stream
structures["see table 34"]=Primary_GPS_data_stream
        
GROUP_ID_VALUES[10001]='Primary_GPS_data_stream'

GROUP_VALUE_IDS['Primary_GPS_data_stream']=10001

class Raw_IMU_LN200_data(BaseField):
    FieldTag="Raw_IMU_LN200_data"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '10002 N/A ', 'Group ID 2 ushort 10002 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'Variable Bytes ',
  'Byte count 2 ushort Variable Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['6',
  'char',
  'IMU header',
  '$IMUnn where nn identifies the IMU ',
  'IMU header 6 char $IMUnn where nn identifies the IMU '],
 ['2',
  'ushort',
  'Variable message byte count',
  '[0, ) Bytes ',
  'Variable message byte count 2 ushort [0, ) Bytes '],
 ['2',
  'short',
  'X delta velocity',
  ' 2-14 metres/sec/pulse count  pulse counts  ',
  'X delta velocity  2  short  2-14 metres/sec/pulse count  pulse counts  '],
 ['2',
  'short',
  'Yneg delta velocity',
  ' 2-14 metres/sec/pulse count  pulse counts  ',
  'Yneg delta velocity  2  short  2-14 metres/sec/pulse count  pulse counts  '],
 ['2',
  'short',
  'Zneg delta velocity',
  ' 2-14 metres/sec/pulse count  pulse counts  ',
  'Zneg delta velocity  2  short  2-14 metres/sec/pulse count  pulse counts  '],
 ['2',
  'short',
  'X delta theta',
  ' 2-18 radians/pulse count  pulse counts  ',
  'X delta theta  2  short  2-18 radians/pulse count  pulse counts  '],
 ['2',
  'short',
  'Yneg delta theta',
  ' 2-18 radians/pulse count  pulse counts  ',
  'Yneg delta theta  2  short  2-18 radians/pulse count  pulse counts  '],
 ['2',
  'short',
  'Zneg delta theta',
  ' 2-18 radians/pulse count  pulse counts  ',
  'Zneg delta theta  2  short  2-18 radians/pulse count  pulse counts  '],
 ['2',
  'short',
  'IMU Status Summary',
  ' N/A  N/A  ',
  'IMU Status Summary  2  short  N/A  N/A  '],
 ['2',
  'short',
  'Mode bit/MUX ID',
  ' N/A  N/A  ',
  'Mode bit/MUX ID  2  short  N/A  N/A  '],
 ['2',
  'short',
  'MUX data word',
  ' N/A  N/A  ',
  'MUX data word  2  short  N/A  N/A  '],
 ['2',
  'short',
  'X raw gyro count',
  ' 1 pulse/pulse count  pulse counts  ',
  'X raw gyro count  2  short  1 pulse/pulse count  pulse counts  '],
 ['2',
  'short',
  'Y raw gyro count',
  ' 1 pulse/pulse count  pulse counts  ',
  'Y raw gyro count  2  short  1 pulse/pulse count  pulse counts  '],
 ['2',
  'short',
  'Z raw gyro count',
  ' 1 pulse/pulse count  pulse counts  ',
  'Z raw gyro count  2  short  1 pulse/pulse count  pulse counts  '],
 ['2',
  'short',
  'IMU Checksum',
  ' N/A  N/A  ',
  'IMU Checksum  2  short  N/A  N/A  '],
 ['2', 'short', 'Data Checksum', 'N/A N/A ', 'Data Checksum 2 short N/A N/A '],
 ['0', 'byte', 'Pad', '0 N/A ', 'Pad 0 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Raw_IMU_LN200_data']=Raw_IMU_LN200_data
structures["see table 35"]=Raw_IMU_LN200_data
        
GROUP_ID_VALUES[10002]='Raw_IMU_LN200_data'

GROUP_VALUE_IDS['Raw_IMU_LN200_data']=10002

class Raw_PPS(BaseField):
    FieldTag="Raw_PPS"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '10003 N/A ', 'Group ID 2 ushort 10003 N/A '],
 ['2', 'ushort', 'Byte count', '36 Bytes ', 'Byte count 2 ushort 36 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4',
  'ulong',
  'PPS pulse count',
  '[0, ) N/A ',
  'PPS pulse count 4 Ulong [0, ) N/A '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 Byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Raw_PPS']=Raw_PPS
structures["see table 36"]=Raw_PPS
        
GROUP_ID_VALUES[10003]='Raw_PPS'

GROUP_VALUE_IDS['Raw_PPS']=10003

class Raw_Event_1_2(BaseField):
    FieldTag="Raw_Event_1_2"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  '10004 or 10005 N/A ',
  'Group ID 2 ushort 10004 or 10005 N/A '],
 ['2', 'ushort', 'Byte count', '36 Bytes ', 'Byte count 2 ushort 36 Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['4',
  'ulong',
  'Event 1 pulse count',
  '[0, ) N/A ',
  'Event 1 pulse count 4 ulong [0, ) N/A '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Raw_Event_1_2']=Raw_Event_1_2
structures["see table 37"]=Raw_Event_1_2
        
GROUP_ID_VALUES[10004]='Raw_Event_1_2'

GROUP_VALUE_IDS['Raw_Event_1_2']=10004

GROUP_ID_VALUES[10005]='Raw_Event_1_2'

GROUP_VALUE_IDS['Raw_Event_1_2']=10005

class Auxiliary_1_2_GPS_data_streams(BaseField):
    FieldTag="Auxiliary_1_2_GPS_data_streams"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  '10007 or 10008 N/A ',
  'Group ID 2 ushort 10007 or 10008 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'variable Bytes ',
  'Byte count 2 ushort variable Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['2', 'byte', 'reserved', 'N/A N/A ', 'reserved 2 byte N/A N/A '],
 ['4', 'long', 'reserved', 'N/A N/A ', 'reserved 4 long N/A N/A '],
 ['2',
  'ushort',
  'Variable message byte count',
  '[0, ) Bytes ',
  'Variable message byte count 2 ushort [0, ) Bytes '],
 ['variable',
  'char',
  'Auxiliary GPS raw data',
  'N/A N/A ',
  'Auxiliary GPS raw data variable char N/A N/A '],
 ['0-3', 'byte', 'Pad', '0 N/A ', 'Pad 0-3 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Auxiliary_1_2_GPS_data_streams']=Auxiliary_1_2_GPS_data_streams
structures["see table 38"]=Auxiliary_1_2_GPS_data_streams
        
GROUP_ID_VALUES[10007]='Auxiliary_1_2_GPS_data_streams'

GROUP_VALUE_IDS['Auxiliary_1_2_GPS_data_streams']=10007

GROUP_ID_VALUES[10008]='Auxiliary_1_2_GPS_data_streams'

GROUP_VALUE_IDS['Auxiliary_1_2_GPS_data_streams']=10008

class Secondary_GPS_data_stream(BaseField):
    FieldTag="Secondary_GPS_data_stream"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '10009 N/A ', 'Group ID 2 ushort 10009 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'Variable Bytes ',
  'Byte count 2 ushort Variable Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['2',
  'ushort',
  'GPS receiver type',
  'See Table 11 N/A ',
  'GPS receiver type 2 ushort See Table 11 N/A '],
 ['4', 'byte', 'Reserved', 'N/A N/A ', 'Reserved 4 byte N/A N/A '],
 ['2',
  'ushort',
  'Variable message byte count',
  '[0, ) Bytes ',
  'Variable message byte count 2 ushort [0, ) Bytes '],
 ['variable',
  'char',
  'GPS Receiver Message',
  'N/A N/A ',
  'GPS Receiver Message variable char N/A N/A '],
 ['0-3', 'byte', 'Pad', '0 N/A ', 'Pad 0-3 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Secondary_GPS_data_stream']=Secondary_GPS_data_stream
structures["see table 39"]=Secondary_GPS_data_stream
        
GROUP_ID_VALUES[10009]='Secondary_GPS_data_stream'

GROUP_VALUE_IDS['Secondary_GPS_data_stream']=10009

class Base_GPS_1_2_data_stream(BaseField):
    FieldTag="Base_GPS_1_2_data_stream"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  '10011 or 10012 N/A ',
  'Group ID 2 ushort 10011 or 10012 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'variable Bytes ',
  'Byte count 2 ushort variable Bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['6', 'byte', 'reserved', 'N/A N/A ', 'reserved 6 byte N/A N/A '],
 ['2',
  'ushort',
  'Variable message byte count',
  '[0, ) Bytes ',
  'Variable message byte count 2 ushort [0, ) Bytes '],
 ['variable',
  'byte',
  'Base GPS raw data',
  'N/A N/A ',
  'Base GPS raw data variable byte N/A N/A '],
 ['0-3', 'byte', 'Pad', '0 N/A ', 'Pad 0-3 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Base_GPS_1_2_data_stream']=Base_GPS_1_2_data_stream
structures["see table 40"]=Base_GPS_1_2_data_stream
        
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
structures["see table 41"]=Control_messages_output_data_rates
        
class format(BaseField):
    FieldTag="format"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2',
  'ushort',
  'Message ID',
  'Message dependent N/A ',
  'Message ID 2 ushort Message dependent N/A '],
 ['2',
  'ushort',
  'Byte count',
  'Message dependent N/A ',
  'Byte count 2 ushort Message dependent N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['0', 'byte', 'Pad', '0 N/A ', 'Pad 0 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['format']=format
structures["see table 42"]=format
        
class Acknowledge(BaseField):
    FieldTag="Acknowledge"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '0 N/A ', 'Message ID 2 ushort 0 N/A '],
 ['2', 'ushort', 'Byte count', '44 N/A ', 'Byte count 2 ushort 44 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Transaction number sent by ',
  'Transaction number 2 ushort Transaction number sent by '],
 ['2',
  'ushort',
  'ID of received message',
  'Any valid message number. N/A ',
  'ID of received message 2 ushort Any valid message number. N/A '],
 ['2',
  'ushort',
  'Response code',
  'See Table 44 N/A ',
  'Response code 2 ushort See Table 44 N/A '],
 ['1',
  'byte',
  'New parameters status',
  'Value Message ',
  'New parameters status 1 byte Value Message '],
 ['32',
  'char',
  'Parameter name',
  'Name of rejected parameter on ',
  'Parameter name 32 char Name of rejected parameter on '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Acknowledge']=Acknowledge
structures["see table 43"]=Acknowledge
        
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
structures["see table 44"]=response_codes
        
class General_Installation_and_Processing_Parameters(BaseField):
    FieldTag="General_Installation_and_Processing_Parameters"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '20 N/A ', 'Message ID 2 ushort 20 N/A '],
 ['2', 'ushort', 'Byte count', '84 N/A ', 'Byte count 2 ushort 84 N/A '],
 ['2',
  'ushort',
  'Transaction Number',
  'Input: Transaction number ',
  'Transaction Number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Time types',
  'Value (bits 0-3) Time type 1 ',
  'Time types 1 byte Value (bits 0-3) Time type 1 '],
 ['1',
  'byte',
  'Distance type',
  'Value State ',
  'Distance type 1 byte Value State '],
 ['1',
  'byte',
  'Select/deselect AutoStart',
  'Value State ',
  'Select/deselect AutoStart 1 byte Value State '],
 ['4',
  'float',
  'Reference to IMU X lever arm',
  '( , ) default = 0 meters ',
  'Reference to IMU X lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to IMU Y lever arm',
  '( , ) default = 0 meters ',
  'Reference to IMU Y lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to IMU Z lever arm',
  '( , ) default = 0 meters ',
  'Reference to IMU Z lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Primary GPS X lever arm',
  '( , ) default = 0 meters ',
  'Reference to Primary GPS X lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Primary GPS Y lever arm',
  '( , ) default = 0 meters ',
  'Reference to Primary GPS Y lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Primary GPS Z lever arm',
  '( , ) default = 0 meters ',
  'Reference to Primary GPS Z lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS X lever arm',
  '( , ) default = 0 meters ',
  'Reference to Auxiliary 1 GPS X lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS Y lever arm',
  '( , ) default = 0 meters ',
  'Reference to Auxiliary 1 GPS Y lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Auxiliary 1 GPS Z lever arm',
  '( , ) default = 0 meters ',
  'Reference to Auxiliary 1 GPS Z lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS X lever arm',
  '( , ) default = 0 meters ',
  'Reference to Auxiliary 2 GPS X lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS Y lever arm',
  '( , ) default = 0 meters ',
  'Reference to Auxiliary 2 GPS Y lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Reference to Auxiliary 2 GPS Z lever arm',
  '( , ) default = 0 meters ',
  'Reference to Auxiliary 2 GPS Z lever arm 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'X IMU wrt Reference frame mounting angle',
  '[-180, +180] default = 0 degrees ',
  'X IMU wrt Reference frame mounting angle 4 float [-180, +180] default = 0 degrees '],
 ['4',
  'float',
  'Y IMU wrt Reference frame mounting angle',
  '[-180, +180] default = 0 degrees ',
  'Y IMU wrt Reference frame mounting angle 4 float [-180, +180] default = 0 degrees '],
 ['4',
  'float',
  'Z IMU wrt Reference frame mounting angle',
  '[-180, +180] default = 0 degrees ',
  'Z IMU wrt Reference frame mounting angle 4 float [-180, +180] default = 0 degrees '],
 ['4',
  'float',
  'X Reference frame wrt Vessel frame mounting angle',
  '[-180, +180] default = 0 degrees ',
  'X Reference frame wrt Vessel frame mounting angle 4 float [-180, +180] default = 0 degrees '],
 ['4',
  'float',
  'Y Reference frame wrt Vessel frame mounting angle',
  '[-180, +180] default = 0 degrees ',
  'Y Reference frame wrt Vessel frame mounting angle 4 float [-180, +180] default = 0 degrees '],
 ['4',
  'float',
  'Z Reference frame wrt Vessel frame mounting angle',
  '[-180, +180] default = 0 degrees ',
  'Z Reference frame wrt Vessel frame mounting angle 4 float [-180, +180] default = 0 degrees '],
 ['1',
  'byte',
  'Multipath environment',
  'Value Multipath ',
  'Multipath environment 1 byte Value Multipath '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['General_Installation_and_Processing_Parameters']=General_Installation_and_Processing_Parameters
structures["see table 45"]=General_Installation_and_Processing_Parameters
        
MESSAGE_ID_VALUES[20]='General_Installation_and_Processing_Parameters'

MESSAGE_VALUE_IDS['General_Installation_and_Processing_Parameters']=20

class GAMS_installation_parameters(BaseField):
    FieldTag="GAMS_installation_parameters"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '21 N/A ', 'Message ID 2 ushort 21 N/A '],
 ['2', 'ushort', 'Byte count', '32 N/A ', 'Byte count 2 ushort 32 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['4',
  'float',
  'Primary-secondary antenna separation',
  '[0, ) default = 0 Meters ',
  'Primary-secondary antenna separation 4 float [0, ) default = 0 Meters '],
 ['4',
  'float',
  'Baseline vector X component',
  '( , ) default = 0 Meters ',
  'Baseline vector X component 4 float ( , ) default = 0 Meters '],
 ['4',
  'float',
  'Baseline vector Y component',
  '( , ) default = 0 meters ',
  'Baseline vector Y component 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Baseline vector Z component',
  '( , ) default = 0 meters ',
  'Baseline vector Z component 4 float ( , ) default = 0 meters '],
 ['4',
  'float',
  'Maximum heading error RMS for calibration',
  '[0, ) default = 3 degrees ',
  'Maximum heading error RMS for calibration 4 float [0, ) default = 3 degrees '],
 ['4',
  'float',
  'Heading correction',
  '( , ) default = 0 degrees ',
  'Heading correction 4 float ( , ) default = 0 degrees '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GAMS_installation_parameters']=GAMS_installation_parameters
structures["see table 46"]=GAMS_installation_parameters
        
MESSAGE_ID_VALUES[21]='GAMS_installation_parameters'

MESSAGE_VALUE_IDS['GAMS_installation_parameters']=21

class User_accuracy_specifications(BaseField):
    FieldTag="User_accuracy_specifications"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '24 N/A ', 'Message ID 2 ushort 24 N/A '],
 ['2', 'ushort', 'Byte count', '24 N/A ', 'Byte count 2 ushort 24 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['4',
  'float',
  'User attitude accuracy',
  '(0, ) default = 0.05 degrees ',
  'User attitude accuracy 4 float (0, ) default = 0.05 degrees '],
 ['4',
  'float',
  'User heading accuracy',
  '(0, ) default = 0.05 degrees ',
  'User heading accuracy 4 float (0, ) default = 0.05 degrees '],
 ['4',
  'float',
  'User position accuracy',
  '(0, ) default = 2 meters ',
  'User position accuracy 4 float (0, ) default = 2 meters '],
 ['4',
  'float',
  'User velocity accuracy',
  '(0, ) default = 0.5 meters/second ',
  'User velocity accuracy 4 float (0, ) default = 0.5 meters/second '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['User_accuracy_specifications']=User_accuracy_specifications
structures["see table 47"]=User_accuracy_specifications
        
MESSAGE_ID_VALUES[24]='User_accuracy_specifications'

MESSAGE_VALUE_IDS['User_accuracy_specifications']=24

class RS_232_422_communication_protocol_settings(BaseField):
    FieldTag="RS_232_422_communication_protocol_settings"
    sdf_list = [['1',
  'byte',
  'RS-232/422 port baud rate',
  'Value Rate ',
  'RS-232/422 port baud rate 1 byte Value Rate '],
 ['1', 'byte', 'Parity', 'Value Parity ', 'Parity 1 byte Value Parity '],
 ['1',
  'byte',
  'Data/Stop Bits',
  'Value Data/Stop Bits ',
  'Data/Stop Bits 1 byte Value Data/Stop Bits '],
 ['1',
  'byte',
  'Flow Control',
  'Value Flow Control ',
  'Flow Control 1 byte Value Flow Control ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['RS_232_422_communication_protocol_settings']=RS_232_422_communication_protocol_settings
structures["see table 49"]=RS_232_422_communication_protocol_settings
        
class Secondary_GPS_Setup(BaseField):
    FieldTag="Secondary_GPS_Setup"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '31 N/A ', 'Message ID 2 ushort 31 N/A '],
 ['2', 'ushort', 'Byte count', '16 N/A ', 'Byte count 2 ushort 16 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Select/deselect GPS AutoConfig',
  'Value State ',
  'Select/deselect GPS AutoConfig 1 byte Value State '],
 ['1',
  'byte',
  'Secondary GPS COM1 port message output rate',
  'Value Rate (Hz) ',
  'Secondary GPS COM1 port message output rate 1 byte Value Rate (Hz) '],
 ['1',
  'byte',
  'Secondary GPS COM2 port control',
  'Value Operation ',
  'Secondary GPS COM2 port control 1 byte Value Operation '],
 ['4',
  'see table 49',
  'Secondary GPS COM2 communication protocol',
  '',
  'Secondary GPS COM2 communication protocol 4 See Table 49 '],
 ['1',
  'byte',
  'Antenna frequency',
  'Value Operation ',
  'Antenna frequency 1 byte Value Operation '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Secondary_GPS_Setup']=Secondary_GPS_Setup
structures["see table 50"]=Secondary_GPS_Setup
        
MESSAGE_ID_VALUES[31]='Secondary_GPS_Setup'

MESSAGE_VALUE_IDS['Secondary_GPS_Setup']=31

class Set_POS_IP_Address(BaseField):
    FieldTag="Set_POS_IP_Address"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '32 N/A ', 'Message ID 2 ushort 32 N/A '],
 ['2', 'ushort', 'Byte count', '16 N/A ', 'Byte count 2 ushort 16 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'IP address Network part 1',
  '[128, 191] Class B, subnet mask ',
  'IP address Network part 1 1 byte [128, 191] Class B, subnet mask '],
 ['1',
  'byte',
  'IP address Network part 2',
  '[0, 255] default = 100 N/A ',
  'IP address Network part 2 1 byte [0, 255] default = 100 N/A '],
 ['1',
  'byte',
  'IP address Host part 1',
  '[0, 255] default = 0 N/A ',
  'IP address Host part 1 1 byte [0, 255] default = 0 N/A '],
 ['1',
  'byte',
  'IP address Host part 2',
  '[1, 253] default = 219 N/A ',
  'IP address Host part 2 1 byte [1, 253] default = 219 N/A '],
 ['1',
  'byte',
  'Subnet mask Network part 1',
  '[255] default = 255 ',
  'Subnet mask Network part 1 1 byte [255] default = 255 '],
 ['1',
  'byte',
  'Subnet mask Network part 2',
  '[255] default = 255 ',
  'Subnet mask Network part 2 1 byte [255] default = 255 '],
 ['1',
  'byte',
  'Subnet mask Host part 1',
  '[0, 255] default = 255 ',
  'Subnet mask Host part 1 1 byte [0, 255] default = 255 '],
 ['1',
  'byte',
  'Subnet mask Host part 2',
  '[0, 254] default = 0 ',
  'Subnet mask Host part 2 1 byte [0, 254] default = 0 '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Set_POS_IP_Address']=Set_POS_IP_Address
structures["see table 51"]=Set_POS_IP_Address
        
MESSAGE_ID_VALUES[32]='Set_POS_IP_Address'

MESSAGE_VALUE_IDS['Set_POS_IP_Address']=32

class Event_Discrete_Setup(BaseField):
    FieldTag="Event_Discrete_Setup"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '33 N/A ', 'Message ID 2 ushort 33 N/A '],
 ['2', 'ushort', 'Byte count', '8 N/A ', 'Byte count 2 ushort 8 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Event 1 trigger',
  'Value Command ',
  'Event 1 trigger 1 byte Value Command '],
 ['1',
  'byte',
  'Event 2 trigger',
  'Value Command ',
  'Event 2 trigger 1 byte Value Command '],
 ['0', 'short', 'Pad', '0 N/A ', 'Pad 0 short 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Event_Discrete_Setup']=Event_Discrete_Setup
structures["see table 52"]=Event_Discrete_Setup
        
MESSAGE_ID_VALUES[33]='Event_Discrete_Setup'

MESSAGE_VALUE_IDS['Event_Discrete_Setup']=33

class COM_port_parameters(BaseField):
    FieldTag="COM_port_parameters"
    sdf_list = [['4',
  'see table 49',
  'Communication protocol',
  '',
  'Communication protocol 4 See Table 49 '],
 ['2',
  'ushort',
  'Input select',
  'Value Input ',
  'Input select 2 ushort Value Input '],
 ['2',
  'ushort',
  'Output select',
  'Value Output ',
  'Output select 2 ushort Value Output ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['COM_port_parameters']=COM_port_parameters
structures["see table 54"]=COM_port_parameters
        
class Base_GPS_1_2_Setup(BaseField):
    FieldTag="Base_GPS_1_2_Setup"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '37/38 N/A ', 'Message ID 2 ushort 37/38 N/A '],
 ['2', 'ushort', 'Byte count', '240 N/A ', 'Byte count 2 ushort 240 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['2',
  'ushort',
  'Select Base GPS input type',
  'Value Operation ',
  'Select Base GPS input type 2 ushort Value Operation '],
 ['1',
  'byte',
  'Line control',
  'Value Operation ',
  'Line control 1 byte Value Operation '],
 ['1',
  'byte',
  'Modem control',
  'Value Operation ',
  'Modem control 1 byte Value Operation '],
 ['1',
  'byte',
  'Connection control',
  'Value Operation ',
  'Connection control 1 byte Value Operation '],
 ['32', 'char', 'Phone number', 'N/A N/A ', 'Phone number 32 char N/A N/A '],
 ['1',
  'byte',
  'Number of redials',
  '[0, ) default = 0 N/A ',
  'Number of redials 1 byte [0, ) default = 0 N/A '],
 ['64',
  'char',
  'Modem command string',
  'N/A N/A ',
  'Modem command string 64 char N/A N/A '],
 ['128',
  'char',
  'Modem initialization string',
  'N/A N/A ',
  'Modem initialization string 128 char N/A N/A '],
 ['2',
  'ushort',
  'Data timeout length',
  '[0, 255] default = 0 seconds ',
  'Data timeout length 2 ushort [0, 255] default = 0 seconds '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Base_GPS_1_2_Setup']=Base_GPS_1_2_Setup
structures["see table 55"]=Base_GPS_1_2_Setup
        
MESSAGE_ID_VALUES[37]='Base_GPS_1_2_Setup'

MESSAGE_VALUE_IDS['Base_GPS_1_2_Setup']=37

MESSAGE_ID_VALUES[38]='Base_GPS_1_2_Setup'

MESSAGE_VALUE_IDS['Base_GPS_1_2_Setup']=38

class Navigation_mode_control(BaseField):
    FieldTag="Navigation_mode_control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '50 N/A ', 'Message ID 2 ushort 50 N/A '],
 ['2', 'ushort', 'Byte count', '8 N/A ', 'Byte count 2 ushort 8 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Navigation mode',
  'Value Mode ',
  'Navigation mode 1 byte Value Mode '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Navigation_mode_control']=Navigation_mode_control
structures["see table 56"]=Navigation_mode_control
        
MESSAGE_ID_VALUES[50]='Navigation_mode_control'

MESSAGE_VALUE_IDS['Navigation_mode_control']=50

class Display_Port_Control(BaseField):
    FieldTag="Display_Port_Control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '51 N/A ', 'Message ID 2 ushort 51 N/A '],
 ['2',
  'ushort',
  'Byte count',
  '10 + 2 x number of groups ',
  'Byte count 2 ushort 10 + 2 x number of groups '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['2',
  'ushort',
  'Number of groups selected for Display Port',
  '[4, 70] default = 4 ',
  'Number of groups selected for Display Port 2 ushort [4, 70] default = 4 '],
 ['variable',
  'ushort',
  'Display Port output group identification',
  'Group ID to output ',
  'Display Port output group identification variable ushort Group ID to output '],
 ['2', 'ushort', 'Reserved', '0 N/A ', 'Reserved 2 ushort 0 N/A '],
 ['0 or 2', 'byte', 'Pad', '0 N/A ', 'Pad 0 or 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Display_Port_Control']=Display_Port_Control
structures["see table 57"]=Display_Port_Control
        
MESSAGE_ID_VALUES[51]='Display_Port_Control'

MESSAGE_VALUE_IDS['Display_Port_Control']=51

class Real_Time_Logging_Data_Port_Control(BaseField):
    FieldTag="Real_Time_Logging_Data_Port_Control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2',
  'ushort',
  'Message ID',
  '52 or 61 N/A ',
  'Message ID 2 ushort 52 or 61 N/A '],
 ['2',
  'ushort',
  'Byte count',
  '10 + 2 x number of groups ',
  'Byte count 2 ushort 10 + 2 x number of groups '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['2',
  'ushort',
  'Number of groups selected for Data Port',
  '[0, 70] default = 0 N/A ',
  'Number of groups selected for Data Port 2 ushort [0, 70] default = 0 N/A '],
 ['variable',
  'ushort',
  'Data Port output group identification',
  'Group ID to output ',
  'Data Port output group identification variable ushort Group ID to output '],
 ['2',
  'ushort',
  'Data Port output rate',
  'Value Rate (Hz) ',
  'Data Port output rate 2 ushort Value Rate (Hz) '],
 ['0 or 2', 'byte', 'Pad', '0 N/A ', 'Pad 0 or 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Real_Time_Logging_Data_Port_Control']=Real_Time_Logging_Data_Port_Control
structures["see table 58"]=Real_Time_Logging_Data_Port_Control
        
MESSAGE_ID_VALUES[52]='Real_Time_Logging_Data_Port_Control'

MESSAGE_VALUE_IDS['Real_Time_Logging_Data_Port_Control']=52

MESSAGE_ID_VALUES[61]='Real_Time_Logging_Data_Port_Control'

MESSAGE_VALUE_IDS['Real_Time_Logging_Data_Port_Control']=61

class Save_restore_parameters_control(BaseField):
    FieldTag="Save_restore_parameters_control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '54 N/A ', 'Message ID 2 ushort 54 N/A '],
 ['2', 'ushort', 'Byte count', '8 N/A ', 'Byte count 2 ushort 8 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Control',
  'Value Operation ',
  'Control 1 byte Value Operation '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Save_restore_parameters_control']=Save_restore_parameters_control
structures["see table 59"]=Save_restore_parameters_control
        
MESSAGE_ID_VALUES[54]='Save_restore_parameters_control'

MESSAGE_VALUE_IDS['Save_restore_parameters_control']=54

class User_time_recovery(BaseField):
    FieldTag="User_time_recovery"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '55 N/A ', 'Message ID 2 ushort 55 N/A '],
 ['2', 'ushort', 'Byte count', '24 N/A ', 'Byte count 2 ushort 24 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['8',
  'double',
  'User PPS time',
  '[0, ) default = 0.0 seconds ',
  'User PPS time 8 double [0, ) default = 0.0 seconds '],
 ['8',
  'double',
  'User time conversion factor',
  '[0, ) default = 1.0 #/seconds  ',
  'User time conversion factor 8 double [0, ) default = 1.0 #/seconds  '],
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
structures["see table 60"]=User_time_recovery
        
MESSAGE_ID_VALUES[55]='User_time_recovery'

MESSAGE_VALUE_IDS['User_time_recovery']=55

class General_data(BaseField):
    FieldTag="General_data"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '56 N/A ', 'Message ID 2 ushort 56 N/A '],
 ['2', 'ushort', 'Byte count', '80 N/A ', 'Byte count 2 ushort 80 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Time of day: Hours',
  '[0, 23] default = 0 hours ',
  'Time of day: Hours 1 byte [0, 23] default = 0 hours '],
 ['1',
  'byte',
  'Time of day: Minutes',
  '[0, 59] default = 0 minutes ',
  'Time of day: Minutes 1 byte [0, 59] default = 0 minutes '],
 ['1',
  'byte',
  'Time of day: Seconds',
  '[0, 59] default = 0 seconds ',
  'Time of day: Seconds 1 byte [0, 59] default = 0 seconds '],
 ['1',
  'byte',
  'Date: Month',
  '[1, 12] default = 1 month ',
  'Date: Month 1 byte [1, 12] default = 1 month '],
 ['1',
  'byte',
  'Date: Day',
  '[1, 31] default = 1 day ',
  'Date: Day 1 byte [1, 31] default = 1 day '],
 ['2',
  'ushort',
  'Date: Year',
  '[0, 65534] default = 0 year ',
  'Date: Year 2 ushort [0, 65534] default = 0 year '],
 ['1',
  'byte',
  'Initial alignment status',
  'See Table 5 N/A ',
  'Initial alignment status 1 byte See Table 5 N/A '],
 ['8',
  'double',
  'Initial latitude',
  '[-90, +90] default = 0 degrees ',
  'Initial latitude 8 double [-90, +90] default = 0 degrees '],
 ['8',
  'double',
  'Initial longitude',
  '[-180, +180] default = 0 degrees ',
  'Initial longitude 8 double [-180, +180] default = 0 degrees '],
 ['8',
  'double',
  'Initial altitude',
  '[-1000, +10000] default = 0 meters ',
  'Initial altitude 8 double [-1000, +10000] default = 0 meters '],
 ['4',
  'float',
  'Initial horizontal position CEP',
  '[0, ) default = 0 meters ',
  'Initial horizontal position CEP 4 float [0, ) default = 0 meters '],
 ['4',
  'float',
  'Initial altitude RMS uncertainty',
  '[0, ) default = 0 meters ',
  'Initial altitude RMS uncertainty 4 float [0, ) default = 0 meters '],
 ['8',
  'double',
  'Initial distance',
  '[0, ) default = 0 meters ',
  'Initial distance 8 double [0, ) default = 0 meters '],
 ['8',
  'double',
  'Initial roll',
  '[-180, +180] default = 0 degrees ',
  'Initial roll 8 double [-180, +180] default = 0 degrees '],
 ['8',
  'double',
  'Initial pitch',
  '[-180, +180] default = 0 degrees ',
  'Initial pitch 8 double [-180, +180] default = 0 degrees '],
 ['8',
  'double',
  'Initial heading',
  '[0, 360) default = 0 degrees ',
  'Initial heading 8 double [0, 360) default = 0 degrees '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['General_data']=General_data
structures["see table 61"]=General_data
        
MESSAGE_ID_VALUES[56]='General_data'

MESSAGE_VALUE_IDS['General_data']=56

class Installation_calibration_control(BaseField):
    FieldTag="Installation_calibration_control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '57 N/A ', 'Message ID 2 ushort 57 N/A '],
 ['2', 'ushort', 'Byte count', '8 N/A ', 'Byte count 2 ushort 8 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Calibration action',
  'Value Command ',
  'Calibration action 1 byte Value Command '],
 ['1',
  'byte',
  'Calibration select',
  'Bit (set) Command ',
  'Calibration select 1 byte Bit (set) Command '],
 ['0', 'byte', 'Pad', '0 N/A ', 'Pad 0 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Installation_calibration_control']=Installation_calibration_control
structures["see table 62"]=Installation_calibration_control
        
MESSAGE_ID_VALUES[57]='Installation_calibration_control'

MESSAGE_VALUE_IDS['Installation_calibration_control']=57

class GAMS_Calibration_Control(BaseField):
    FieldTag="GAMS_Calibration_Control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '58 N/A ', 'Message ID 2 ushort 58 N/A '],
 ['2', 'ushort', 'Byte count', '8 N/A ', 'Byte count 2 ushort 8 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'GAMS calibration control',
  'Value Command ',
  'GAMS calibration control 1 byte Value Command '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GAMS_Calibration_Control']=GAMS_Calibration_Control
structures["see table 63"]=GAMS_Calibration_Control
        
MESSAGE_ID_VALUES[58]='GAMS_Calibration_Control'

MESSAGE_VALUE_IDS['GAMS_Calibration_Control']=58

class Program_Control(BaseField):
    FieldTag="Program_Control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '90 N/A ', 'Message ID 2 ushort 90 N/A '],
 ['2', 'ushort', 'Byte count', '8 N/A ', 'Byte count 2 ushort 8 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['2',
  'ushort',
  'Control',
  'Value Command ',
  'Control 2 ushort Value Command '],
 ['0', 'byte', 'Pad', '0 N/A ', 'Pad 0 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Program_Control']=Program_Control
structures["see table 64"]=Program_Control
        
MESSAGE_ID_VALUES[90]='Program_Control'

MESSAGE_VALUE_IDS['Program_Control']=90

class GPS_control(BaseField):
    FieldTag="GPS_control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '91 N/A ', 'Message ID 2 ushort 91 N/A '],
 ['2', 'ushort', 'Byte count', '8 N/A ', 'Byte count 2 ushort 8 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Control command',
  'Value Command ',
  'Control command 1 byte Value Command '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['GPS_control']=GPS_control
structures["see table 65"]=GPS_control
        
MESSAGE_ID_VALUES[91]='GPS_control'

MESSAGE_VALUE_IDS['GPS_control']=91

class Analog_Port_Set_up(BaseField):
    FieldTag="Analog_Port_Set_up"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '105 N/A ', 'Message ID 2 ushort 105 N/A '],
 ['2', 'ushort', 'Byte count', '24 N/A ', 'Byte count 2 ushort 24 N/A '],
 ['2',
  'ushort',
  'Transaction',
  'Input: Transaction number set by client ',
  'Transaction # 2 ushort Input: Transaction number set by client '],
 ['4',
  'float',
  'Roll Scale Factor',
  '# = (0, )  ',
  'Roll Scale Factor 4 float # = (0, )  '],
 ['4',
  'float',
  'Pitch Scale Factor',
  ' # = (0, )  (default = 1.0)  N/A  ',
  'Pitch Scale Factor 4  float  # = (0, )  (default = 1.0)  N/A  '],
 ['4',
  'float',
  'Heave Scale Factor',
  ' # = (0, )  ',
  'Heave Scale Factor 4  float  # = (0, )  '],
 ['1',
  'byte',
  'Roll Sense',
  ' Value  Analog +ve  ',
  'Roll Sense  1  byte  Value  Analog +ve  '],
 ['1',
  'byte',
  'Pitch Sense',
  ' Value  Analog +ve  ',
  'Pitch Sense  1  byte  Value  Analog +ve  '],
 ['1',
  'byte',
  'Heave Sense',
  ' Value  Analog +ve  ',
  'Heave Sense  1  byte  Value  Analog +ve  '],
 ['1',
  'byte',
  'Analog Formula Select',
  ' Value  Formula  ',
  'Analog Formula Select 1  byte  Value  Formula  '],
 ['1',
  'byte',
  'Analog Output',
  ' Value  Condition  ',
  'Analog Output  1  byte  Value  Condition  '],
 ['1',
  'byte',
  'Frame of Reference',
  ' Value  Condition  ',
  'Frame of Reference 1  byte  Value  Condition  '],
 ['0', 'byte', 'Pad', ' 0  N/A  ', 'Pad  0  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', ' N/A  N/A  ', 'Checksum  2  ushort  N/A  N/A  '],
 ['2', 'char', 'Message end', ' $#  N/A  ', 'Message end  2  char  $#  N/A  ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Analog_Port_Set_up']=Analog_Port_Set_up
structures["see table 66"]=Analog_Port_Set_up
        
MESSAGE_ID_VALUES[105]='Analog_Port_Set_up'

MESSAGE_VALUE_IDS['Analog_Port_Set_up']=105

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
  ' Input:  Transaction number set by client  ',
  'Transaction #  2  ushort  Input:  Transaction number set by client  '],
 ['4',
  'float',
  'Heave Corner Period',
  ' (10.0, ) (default = 200.0)  seconds  ',
  'Heave Corner Period 4  float  (10.0, ) (default = 200.0)  seconds  '],
 ['4',
  'float',
  'Heave Damping Ratio',
  ' (0, 1.0) (default = 0.707)  N/A  ',
  'Heave Damping Ratio 4  float  (0, 1.0) (default = 0.707)  N/A  '],
 ['2', 'byte', 'Pad', ' 0  N/A  ', 'Pad  2  byte  0  N/A  '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Heave_Filter_Set_up']=Heave_Filter_Set_up
structures["see table 67"]=Heave_Filter_Set_up
        
MESSAGE_ID_VALUES[106]='Heave_Filter_Set_up'

MESSAGE_VALUE_IDS['Heave_Filter_Set_up']=106

class Password_Protection_Control(BaseField):
    FieldTag="Password_Protection_Control"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '111 N/A ', 'Message ID 2 ushort 111 N/A '],
 ['2', 'ushort', 'Byte count', '48 N/A ', 'Byte count 2 ushort 48 N/A '],
 ['2',
  'ushort',
  'Transaction',
  'Input: Transaction number set by ',
  'Transaction # 2 ushort Input: Transaction number set by '],
 ['1',
  'byte',
  'Password Control',
  'Value Command ',
  'Password Control 1 byte Value Command '],
 ['20',
  'char',
  'Password',
  'String value of current Password, ',
  'Password 20 char String value of current Password, '],
 ['20',
  'char',
  'New Password',
  'If Password Control = 0: N/A ',
  'New Password 20 char If Password Control = 0: N/A '],
 ['1',
  'byte',
  'Pad',
  '0 N/A -- doc error; said one short, but pad normally in bytes and one byte here for message size to be a multiple of 4 ',
  'Pad 1 byte 0 N/A -- doc error; said one short, but pad normally in bytes and one byte here for message size to be a multiple of 4 '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Password_Protection_Control']=Password_Protection_Control
structures["see table 68"]=Password_Protection_Control
        
MESSAGE_ID_VALUES[111]='Password_Protection_Control'

MESSAGE_VALUE_IDS['Password_Protection_Control']=111

class Sensor_Parameter_Set_up(BaseField):
    FieldTag="Sensor_Parameter_Set_up"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '120 N/A ', 'Message ID 2 ushort 120 N/A '],
 ['2', 'ushort', 'Byte count', '68 N/A ', 'Byte count 2 ushort 68 N/A '],
 ['2',
  'ushort',
  'Transaction',
  'Input: Transaction number set by ',
  'Transaction # 2 ushort Input: Transaction number set by '],
 ['4',
  'float',
  'X Sensor 1',
  '[-180, +180] default = 0 deg wrt reference frame mounting angle ',
  'X Sensor 1 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle '],
 ['4',
  'float',
  'Y Sensor 1',
  '[-180, +180] default = 0 deg wrt reference frame mounting angle',
  'Y Sensor 1 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle'],
 ['4',
  'float',
  'Z Sensor 1',
  '[-180, +180] default = 0 deg wrt reference frame mounting angle',
  'Z Sensor 1 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle'],
 ['4',
  'float',
  'X Sensor 2',
  '[-180, +180] default = 0 deg wrt reference frame mounting angle',
  'X Sensor 2 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle'],
 ['4',
  'float',
  'Y Sensor 2',
  '[-180, +180] default = 0 deg wrt reference frame mounting angle',
  'Y Sensor 2 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle'],
 ['4',
  'float',
  'Z Sensor 2',
  '[-180, +180] default = 0 deg wrt reference frame mounting angle ',
  'Z Sensor 2 4 float [-180, +180] default = 0 deg wrt reference frame mounting angle '],
 ['4',
  'float',
  'Reference to Sensor 1 X lever arm',
  '( , ) default = 0 m ',
  'Reference to Sensor 1 X lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to Sensor 1 Y lever arm',
  '( , ) default = 0 m ',
  'Reference to Sensor 1 Y lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to Sensor 1 Z lever arm',
  '( , ) default = 0 m ',
  'Reference to Sensor 1 Z lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to Sensor 2 X lever arm',
  '( , ) default = 0 m ',
  'Reference to Sensor 2 X lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to Sensor 2 Y lever arm',
  '( , ) default = 0 m ',
  'Reference to Sensor 2 Y lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to Sensor 2 Z lever arm',
  '( , ) default = 0 m ',
  'Reference to Sensor 2 Z lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to CoR X lever arm',
  '( , ) default = 0 m ',
  'Reference to CoR X lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to CoR Y lever arm',
  '( , ) default = 0 m ',
  'Reference to CoR Y lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to CoR Z lever arm',
  '( , ) default = 0 m ',
  'Reference to CoR Z lever arm 4 float ( , ) default = 0 m '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Sensor_Parameter_Set_up']=Sensor_Parameter_Set_up
structures["see table 69"]=Sensor_Parameter_Set_up
        
MESSAGE_ID_VALUES[120]='Sensor_Parameter_Set_up'

MESSAGE_VALUE_IDS['Sensor_Parameter_Set_up']=120

class Vessel_Installation_Parameter_Set_up(BaseField):
    FieldTag="Vessel_Installation_Parameter_Set_up"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '121 N/A ', 'Message ID 2 ushort 121 N/A '],
 ['2', 'ushort', 'Byte count', '20 N/A ', 'Byte count 2 ushort 20 N/A '],
 ['2',
  'ushort',
  'Transaction',
  'Input: Transaction number set by client ',
  'Transaction # 2 ushort Input: Transaction number set by client '],
 ['4',
  'float',
  'Reference to Vessel X lever arm',
  '( , ) default = 0 m ',
  'Reference to Vessel X lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to Vessel Y lever arm',
  '( , ) default = 0 m ',
  'Reference to Vessel Y lever arm 4 float ( , ) default = 0 m '],
 ['4',
  'float',
  'Reference to Vessel Z lever arm',
  '( , ) default = 0 m ',
  'Reference to Vessel Z lever arm 4 float ( , ) default = 0 m '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Vessel_Installation_Parameter_Set_up']=Vessel_Installation_Parameter_Set_up
structures["see table 70"]=Vessel_Installation_Parameter_Set_up
        
MESSAGE_ID_VALUES[121]='Vessel_Installation_Parameter_Set_up'

MESSAGE_VALUE_IDS['Vessel_Installation_Parameter_Set_up']=121

class NMEA_Port_Definition(BaseField):
    FieldTag="NMEA_Port_Definition"
    sdf_list = [['1',
  'byte',
  'Port Number',
  '[1, 10] N/A ',
  'Port Number 1 byte [1, 10] N/A '],
 ['4',
  'ulong',
  'Nmea Formula Select',
  'Bit (set) Format Formula ',
  'Nmea Formula Select 4 ulong Bit (set) Format Formula '],
 ['1',
  'ubyte',
  'Nmea output rate',
  'Value Rate (Hz) ',
  'Nmea output rate 1 ubyte Value Rate (Hz) '],
 ['1', 'byte', 'Talker ID', 'Value ID ', 'Talker ID 1 byte Value ID '],
 ['1',
  'byte',
  'Roll Sense',
  'Value Digital +ve ',
  'Roll Sense 1 byte Value Digital +ve '],
 ['1',
  'byte',
  'Pitch Sense',
  'Value Digital +ve ',
  'Pitch Sense 1 byte Value Digital +ve '],
 ['1',
  'byte',
  'Heave Sense',
  'Value Digital +ve ',
  'Heave Sense 1 byte Value Digital +ve ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['NMEA_Port_Definition']=NMEA_Port_Definition
structures["see table 72"]=NMEA_Port_Definition
        
class Binary_Port_Definition(BaseField):
    FieldTag="Binary_Port_Definition"
    sdf_list = [['1',
  'byte',
  'Port Number',
  '[1, 10] N/A ',
  'Port Number 1 byte [1, 10] N/A '],
 ['4',
  'ushort',
  'Formula Select',
  'Value Format Formula ',
  'Formula Select 4 ushort Value Format Formula '],
 ['2',
  'ushort',
  'Message Update Rate',
  ' Value  Rate (Hz)  ',
  'Message Update Rate 2 ushort  Value  Rate (Hz)  '],
 ['1',
  'byte',
  'Roll Sense',
  ' Value  Digital +ve  ',
  'Roll Sense 1 byte  Value  Digital +ve  '],
 ['1',
  'byte',
  'Pitch Sense',
  ' Value  Digital +ve  ',
  'Pitch Sense 1 byte  Value  Digital +ve  '],
 ['1',
  'byte',
  'Heave Sense',
  'Value Digital +ve ',
  'Heave Sense 1 byte Value Digital +ve '],
 ['1',
  'byte',
  'Sensor Frame Output',
  'Value Frame of Reference ',
  'Sensor Frame Output 1 byte Value Frame of Reference ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Binary_Port_Definition']=Binary_Port_Definition
structures["see table 74"]=Binary_Port_Definition
        
class Binary_Output_Diagnostics(BaseField):
    FieldTag="Binary_Output_Diagnostics"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '20102 N/A ', 'Message ID 2 ushort 20102 N/A '],
 ['2', 'ushort', 'Byte count', '24 N/A ', 'Byte count 2 ushort 24 N/A '],
 ['2',
  'ushort',
  'Transaction',
  'Input: Transaction number set by client ',
  'Transaction # 2 ushort Input: Transaction number set by client '],
 ['4',
  'float',
  'Operator roll input',
  '(-180, 180] default = 0 deg ',
  'Operator roll input 4 float (-180, 180] default = 0 deg '],
 ['4',
  'float',
  'Operator pitch input',
  '(-180, 180] default = 0 deg ',
  'Operator pitch input 4 float (-180, 180] default = 0 deg '],
 ['4',
  'float',
  'Operator heading input',
  '[0, 360) default = 0 deg ',
  'Operator heading input 4 float [0, 360) default = 0 deg '],
 ['4',
  'float',
  'Operator heave input',
  '[-100 to 100] default = 0 m ',
  'Operator heave input 4 float [-100 to 100] default = 0 m '],
 ['1',
  'byte',
  'Output Enable',
  'Value Command ',
  'Output Enable 1 byte Value Command '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Binary_Output_Diagnostics']=Binary_Output_Diagnostics
structures["see table 75"]=Binary_Output_Diagnostics
        
MESSAGE_ID_VALUES[20102]='Binary_Output_Diagnostics'

MESSAGE_VALUE_IDS['Binary_Output_Diagnostics']=20102

class Analog_Port_Diagnostics(BaseField):
    FieldTag="Analog_Port_Diagnostics"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '20103 N/A ', 'Message ID 2 ushort 20103 N/A '],
 ['2', 'ushort', 'Byte count', '20 N/A ', 'Byte count 2 ushort 20 N/A '],
 ['2',
  'ushort',
  'Transaction',
  'Input: Transaction number set by client ',
  'Transaction # 2 ushort Input: Transaction number set by client '],
 ['4',
  'float',
  'Operator roll input',
  '(-180, 180] default = 0 deg ',
  'Operator roll input 4 float (-180, 180] default = 0 deg '],
 ['4',
  'float',
  'Operator pitch input',
  '(-180, 180] default = 0 deg ',
  'Operator pitch input 4 float (-180, 180] default = 0 deg '],
 ['4',
  'float',
  'Operator heave input',
  '[-100, 100] default = 0 m ',
  'Operator heave input 4 float [-100, 100] default = 0 m '],
 ['1',
  'byte',
  'Output Enable',
  'Value Command ',
  'Output Enable 1 byte Value Command '],
 ['1', 'byte', 'Pad', '0 N/A ', 'Pad 1 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Analog_Port_Diagnostics']=Analog_Port_Diagnostics
structures["see table 76"]=Analog_Port_Diagnostics
        
MESSAGE_ID_VALUES[20103]='Analog_Port_Diagnostics'

MESSAGE_VALUE_IDS['Analog_Port_Diagnostics']=20103

class Byte_Format(BaseField):
    FieldTag="Byte_Format"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Byte_Format']=Byte_Format
structures["see table 77"]=Byte_Format
        
class Short_Integer_Format(BaseField):
    FieldTag="Short_Integer_Format"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Short_Integer_Format']=Short_Integer_Format
structures["see table 78"]=Short_Integer_Format
        
class Long_Integer_Format(BaseField):
    FieldTag="Long_Integer_Format"
    sdf_list = []
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Long_Integer_Format']=Long_Integer_Format
structures["see table 79"]=Long_Integer_Format
        
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
structures["see table 80"]=Single_Precision_Real_Format
        
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
structures["see table 81"]=Double_Precision_Real_Format
        
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
structures["see table 82"]=Invalid_data_values
        
class format(BaseField):
    FieldTag="format"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2',
  'ushort',
  'Group ID',
  'Group number N/A ',
  'Group ID 2 ushort Group number N/A '],
 ['2',
  'ushort',
  'Byte count',
  'Group dependent bytes ',
  'Byte count 2 ushort Group dependent bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['format']=format
structures["see table 2"]=format
        
class Primary_GPS_status(BaseField):
    FieldTag="Primary_GPS_status"
    sdf_list = [['4', 'char', 'Group start', '$GRP N/A ', 'Group start 4 char $GRP N/A '],
 ['2', 'ushort', 'Group ID', '3 N/A ', 'Group ID 2 ushort 3 N/A '],
 ['2',
  'ushort',
  'Byte count',
  '76 + 20 x (number of channels) bytes ',
  'Byte count 2 ushort 76 + 20 x (number of channels) bytes '],
 ['26',
  'see table 3',
  'Time/Distance Fields',
  '',
  'Time/Distance Fields 26 See Table 3 '],
 ['1',
  'byte',
  'Navigation solution status',
  'See Table 9 N/A ',
  'Navigation solution status 1 byte See Table 9 N/A '],
 ['1',
  'byte',
  'Number of SV tracked',
  '[0, 12] N/A ',
  'Number of SV tracked 1 byte [0, 12] N/A '],
 ['2',
  'ushort',
  'Channel status byte count',
  '[0, 240] bytes ',
  'Channel status byte count 2 ushort [0, 240] bytes '],
 ['variable',
  'see table 8',
  'Channel status',
  '',
  'Channel status variable See Table 8 '],
 ['4', 'float', 'HDOP', '( , ) N/A ', 'HDOP 4 float ( , ) N/A '],
 ['4', 'float', 'VDOP', '( , ) N/A ', 'VDOP 4 float ( , ) N/A '],
 ['4',
  'float',
  'DGPS correction latency',
  '[0, 999.9] seconds ',
  'DGPS correction latency 4 float [0, 999.9] seconds '],
 ['2',
  'ushort',
  'DGPS reference ID',
  '[0, 1023] N/A ',
  'DGPS reference ID 2 ushort [0, 1023] N/A '],
 ['4',
  'ulong',
  'GPS/UTC week number',
  '[0, 1023] ',
  'GPS/UTC week number 4 ulong [0, 1023] '],
 ['8',
  'double',
  'GPS/UTC time offset',
  '( , ) seconds ',
  'GPS/UTC time offset 8 double ( , ) seconds '],
 ['4',
  'float',
  'GPS navigation message latency',
  'Number of seconds from the ',
  'GPS navigation message latency 4 float Number of seconds from the '],
 ['4',
  'float',
  'Geoidal separation',
  '( , ) meters ',
  'Geoidal separation 4 float ( , ) meters '],
 ['2',
  'ushort',
  'GPS receiver type',
  'See Table 11 N/A ',
  'GPS receiver type 2 ushort See Table 11 N/A '],
 ['4',
  'ulong',
  'GPS status',
  'GPS summary status fields which depend on GPS receiver type. ',
  'GPS status 4 ulong GPS summary status fields which depend on GPS receiver type. '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Group end', '$# N/A ', 'Group end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Primary_GPS_status']=Primary_GPS_status
structures["see table 7"]=Primary_GPS_status
        
GROUP_ID_VALUES[3]='Primary_GPS_status'

GROUP_VALUE_IDS['Primary_GPS_status']=3

class Primary_GPS_Setup(BaseField):
    FieldTag="Primary_GPS_Setup"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '30 N/A ', 'Message ID 2 ushort 30 N/A '],
 ['2', 'ushort', 'Byte count', '16 N/A ', 'Byte count 2 ushort 16 N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['1',
  'byte',
  'Select/deselect GPS AutoConfig',
  'Value State ',
  'Select/deselect GPS AutoConfig 1 byte Value State '],
 ['1',
  'byte',
  'Primary GPS COM1 port message output rate',
  'Value Rate (Hz) ',
  'Primary GPS COM1 port message output rate 1 byte Value Rate (Hz) '],
 ['1',
  'byte',
  'Primary GPS COM2 port control',
  'Value Operation ',
  'Primary GPS COM2 port control 1 byte Value Operation '],
 ['4',
  'see table 49',
  'Primary GPS COM2 communication protocol',
  '',
  'Primary GPS COM2 communication protocol 4 See Table 49 '],
 ['1',
  'byte',
  'Antenna frequency',
  'Value Operation ',
  'Antenna frequency 1 byte Value Operation '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Primary_GPS_Setup']=Primary_GPS_Setup
structures["see table 48"]=Primary_GPS_Setup
        
MESSAGE_ID_VALUES[30]='Primary_GPS_Setup'

MESSAGE_VALUE_IDS['Primary_GPS_Setup']=30

class COM_Port_Setup(BaseField):
    FieldTag="COM_Port_Setup"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '34 N/A ', 'Message ID 2 ushort 34 N/A '],
 ['2',
  'ushort',
  'Byte count',
  '12 + 8 x nPorts N/A ',
  'Byte count 2 ushort 12 + 8 x nPorts N/A '],
 ['2',
  'ushort',
  'Transaction number',
  'Input: Transaction number ',
  'Transaction number 2 ushort Input: Transaction number '],
 ['2',
  'ushort',
  'Number of COM ports',
  '[1,10] ',
  'Number of COM ports 2 ushort [1,10] '],
 ['variable',
  'see table 54',
  'COM Port Parameters',
  'One set of parameters for each of nPorts COM port. ',
  'COM Port Parameters variable See Table 54 One set of parameters for each of nPorts COM port. '],
 ['2', 'ushort', 'Port mask', 'Input: ', 'Port mask 2 ushort Input: '],
 ['2', 'byte', 'Pad', '0 N/A ', 'Pad 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['COM_Port_Setup']=COM_Port_Setup
structures["see table 53"]=COM_Port_Setup
        
MESSAGE_ID_VALUES[34]='COM_Port_Setup'

MESSAGE_VALUE_IDS['COM_Port_Setup']=34

class NMEA_Output_Set_up(BaseField):
    FieldTag="NMEA_Output_Set_up"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '135 N/A ', 'Message ID 2 ushort 135 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'For even #ports (16 + #ports x 10) ',
  'Byte count 2 ushort For even #ports (16 + #ports x 10) '],
 ['2',
  'ushort',
  'Transaction',
  'Input: Transaction number set by client ',
  'Transaction # 2 ushort Input: Transaction number set by client '],
 ['9', 'byte', 'Reserved', 'N/A N/A ', 'Reserved 9 byte N/A N/A '],
 ['1',
  'byte',
  'Number of Ports',
  '[0, 10] N/A ',
  'Number of Ports 1 byte [0, 10] N/A '],
 ['variable',
  'see table 72',
  'NMEA Port Definitions',
  ' NMEA Port Definition #ports x 10 ',
  'NMEA Port Definitions variable See Table 72: NMEA Port Definition #ports x 10 '],
 ['0 or 2', 'byte', 'Pad', '0 N/A ', 'Pad 0 or 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['NMEA_Output_Set_up']=NMEA_Output_Set_up
structures["see table 71"]=NMEA_Output_Set_up
        
MESSAGE_ID_VALUES[135]='NMEA_Output_Set_up'

MESSAGE_VALUE_IDS['NMEA_Output_Set_up']=135

MESSAGE_ID_VALUES[35]='NMEA_Output_Set_up'

MESSAGE_VALUE_IDS['NMEA_Output_Set_up']=35

class Binary_Output_Set_up(BaseField):
    FieldTag="Binary_Output_Set_up"
    sdf_list = [['4', 'char', 'Message start', '$MSG N/A ', 'Message start 4 char $MSG N/A '],
 ['2', 'ushort', 'Message ID', '136 N/A ', 'Message ID 2 ushort 136 N/A '],
 ['2',
  'ushort',
  'Byte count',
  'For even #ports (16 + #ports x 10) ',
  'Byte count 2 ushort For even #ports (16 + #ports x 10) '],
 ['2',
  'ushort',
  'Transaction',
  'Input: Transaction number set by client ',
  'Transaction # 2 ushort Input: Transaction number set by client '],
 ['7', 'byte', 'Reserved', 'N/A N/A ', 'Reserved 7 byte N/A N/A '],
 ['1',
  'byte',
  'Number of Ports',
  '[0, 10] N/A ',
  'Number of Ports 1 byte [0, 10] N/A '],
 ['variable',
  'see table 74',
  'Binary Port Definitions',
  ' Binary Port Definition #ports x 10 ',
  'Binary Port Definitions variable See Table 74: Binary Port Definition #ports x 10 '],
 ['0 or 2', 'byte', 'Pad', '0 N/A ', 'Pad 0 or 2 byte 0 N/A '],
 ['2', 'ushort', 'Checksum', 'N/A N/A ', 'Checksum 2 ushort N/A N/A '],
 ['2', 'char', 'Message end', '$# N/A ', 'Message end 2 char $# N/A ']]
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)

    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        
structures['Binary_Output_Set_up']=Binary_Output_Set_up
structures["see table 73"]=Binary_Output_Set_up
        
MESSAGE_ID_VALUES[136]='Binary_Output_Set_up'

MESSAGE_VALUE_IDS['Binary_Output_Set_up']=136

MESSAGE_ID_VALUES[36]='Binary_Output_Set_up'

MESSAGE_VALUE_IDS['Binary_Output_Set_up']=36
