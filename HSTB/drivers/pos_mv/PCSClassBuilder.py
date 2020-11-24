import re
import traceback
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

types = {"char": ctypes.c_char, "ushort": ctypes.c_uint16, "long": ctypes.c_int32, "short": ctypes.c_int16,
         "ulong": ctypes.c_uint32, "double": ctypes.c_double, "float": ctypes.c_float, "ubyte": ctypes.c_uint8,
         "byte": ctypes.c_uint8}

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
def CreateClassFile(fileobj, bDupCheck=False):
    import inspect
    here = inspect.getsourcelines(CreateClassFile)[-1]
    print(here)
    mysource = open(__file__).readlines()[:here - 1]
    fileobj.writelines(mysource)

    # See S57 module for examples
    floatingpointconv = {}  # define any fields that have conversion constants that we want to apply on read/write so the usage is natural to enduser.
    ReadFromFiles = {}

    classesToCreate = []
    for tablenum, spec in list(SplitPosMVStruct().items()):
        if _dHSTP:
            print(tablenum)
        classname, struct_list = ParseSpec(spec)
        classesToCreate.append([tablenum, classname, struct_list])

    classesToCreate.reverse()  # put them backwards as we're about to iterate and pop in reverse order.

    # check for duplicate structures

    print("\n\nClasses to export:")
    print(([(n, c) for n, c, d in classesToCreate]))  # @UnusedVariable
    print("\n\n")
    while classesToCreate:
        bProgressed = False
        for index in range(len(classesToCreate) - 1, -1, -1):
            tablenum, classname, struct_list = classesToCreate[index]
            if _dHSTP:
                print("Starting Processing of #%d" % index, tablenum)
            try:
                classdct = {}
                ParseFields(struct_list, classdct)
                structures["see " + tablenum] = True  # add to the global list of SDF structures to be available to other complex structures.
                classesToCreate.pop(index)
                bProgressed = True
                if _dHSTP:
                    print("Processed -- ", tablenum)
                # for k,v in classdct.iteritems(): #show the fields that were found
                #    print k,v
                try:
                    conv_funcs = floatingpointconv[tablenum]
                except KeyError:  # default of no conversions on read/write
                    conv_funcs = """
    def _float_decode(self, s57_fileobj=None):
        pass
    def _float_encode(self, s57_fileobj=None):
        pass
        """
                try:
                    conv_funcs += ReadFromFiles[tablenum]
                except KeyError:
                    conv_funcs += ''

                fileobj.write("""
class %s(BaseField):
    FieldTag="%s"
    sdf_list = %s
    def __init__(self, *args, **opts):
        BaseField.__init__(self, *args, **opts)
%s
structures['%s']=%s
structures["see %s"]=%s
        """ % (classname, classname, pprint.pformat(struct_list), conv_funcs, classname, classname, tablenum, classname))
                if "Message_ID" in classdct["subfields"]:
                    if not set(classdct["subfields"]["Message_ID"].split()).issuperset(set("Message dependent N/A".split())):
                        msg_id = int(re.match("\d+", classdct["subfields"]["Message_ID"]).group())
                        fileobj.write("\nMESSAGE_ID_VALUES[%d]='%s'\n" % (msg_id, classname))
                        fileobj.write("\nMESSAGE_VALUE_IDS['%s']=%d\n" % (classname, msg_id))
                        duplicate_ids = {37: 38, 135: 35, 136: 36, 52: 61}
                        try:
                            see_id = duplicate_ids[msg_id]
                            fileobj.write("\nMESSAGE_ID_VALUES[%d]='%s'\n" % (see_id, classname))
                            fileobj.write("\nMESSAGE_VALUE_IDS['%s']=%d\n" % (classname, see_id))
                        except KeyError:
                            pass

                if "Group_ID" in classdct["subfields"]:
                    if not set(classdct["subfields"]["Group_ID"].split()).issuperset(set("Group number N/A".split())):
                        # if classdct["subfields"]["Group_ID"] != "Group number N/A":
                        msg_id = int(re.match("\d+", classdct["subfields"]["Group_ID"]).group())
                        fileobj.write("\nGROUP_ID_VALUES[%d]='%s'\n" % (msg_id, classname))
                        fileobj.write("\nGROUP_VALUE_IDS['%s']=%d\n" % (classname, msg_id))
                        duplicate_ids = {21: 22, 23: 24, 5: 6, 12: 13, 102: 103, 104: 105, 10004: 10005, 10007: 10008, 10011: 10012}
                        try:
                            see_id = duplicate_ids[msg_id]
                            fileobj.write("\nGROUP_ID_VALUES[%d]='%s'\n" % (see_id, classname))
                            fileobj.write("\nGROUP_VALUE_IDS['%s']=%d\n" % (classname, see_id))
                        except KeyError:
                            pass

            except TypeError:
                if _dHSTP:
                    traceback.print_exc()
                    print(struct_list)
                    try:
                        for s in struct_list:
                            print(s)
                    except:
                        pass
                if _dHSTP:
                    print(tablenum, classname, "had sub dependencies that haven't been processed yet.")
            except Exception as e:
                raise e
        if not bProgressed:
            print("The following classes failed to create")
            print([(n, c) for n, c, d in classesToCreate])  # @UnusedVariable
            # print structures.keys()
            raise Exception("Failed to convert all types.")


def SplitPosMVStruct():
    txttables = re.split(r"(\nTable \d+:)", POSMV_UserManual.Structures)  # @UndefinedVariable
    tables = OrderedDict()
    for i, t in enumerate(txttables):
        if "Table 0:" in t:
            start = i
            break
    for i in range(start, len(txttables), 2):
        tables[txttables[i].replace("\n", "").replace(":", "").lower()] = txttables[i + 1]  # set the dictionary with tables["Table 11"]="Description of structure with datatypes etc"
    return tables


def ParseSpec(spec):
    # print spec
    # spec = spec.strip('\n').replace('\r\n ', '')  # to work with v5 POS MV ICD PDF saved as-is
    long_name = re.sub("((Group|Message) [\d/\d]*:?)?", "", spec.split("\n")[0])  # re.split("Group \d*", spec)[1].split("\n")[0] #first set of text after the "group x" tag
    name = long_name.strip().translate(trans).replace("__", "_").replace("__", "_")

    d2 = []
    for line in spec.split("\n"):
        # print "checking", line
        types_found = []
        for t in list(types.keys()) + ["See Table \d+"]:
            #  ^[^\.^(]*?  means no period or opening parenthesis before the data -- there were some data types buried in description that were being found
            #
            m = re.search(r"\W+(?P<cnt>\d+|variable|\d+(\W*(-|to|or)\W*)\d+)\W+(?P<dtype>%s)(\W|$)" % t, line, re.IGNORECASE)  # has
            if m:  # found a variable declaration
                if re.search(r"\.", line[:m.start()]):
                    print("\n***************************Warning Period  before Types on one line************************")
                    print("in", name)
                    print(line)
                    print("Skipping since this is usually a comment being mis-read")
                    # print(m.start(), line.find("."), line.find("("))
                    print("***************************End Warning Period before Types on one line************************\n")
                else:
                    types_found.append((t, m))
        if len(types_found) > 1:
            # don't allow more than one occurrence per line -- avoids accidentally reading description and finding a 2nd datatype
            #raise Exception("Multiple data types found on line " + line)
            print("\n***************************Warning Multiple Types on one line************************")
            print("in", name)
            print(line)
            print([(m.start(), t) for t, m in types_found])
            positions = [m.start() for t, m in types_found]
            use_index = positions.index(min(positions))
            print("Using ", types_found[use_index][0], "at position", types_found[use_index][1].start())
            print("***************************END Warning Multiple Types on one line************************\n")
        else:
            use_index = 0
        if types_found:
            t, m = types_found[use_index]
            varname = line[:m.start()]
            if varname.find("(") >= 0:
                print("\n***************************Warning REMOVING Parenthesis in the variable name************************")
                print("in", name)
                print(varname)
                varname = varname[:varname.find("(")]  # remove comments in parens in the variable name
                print("becomes", varname)
                print("***************************End Warning REMOVING Parenthesis in the variable name************************\n")
            if re.match(r"byte\W*count", varname.lower(), re.IGNORECASE):  # force byte count to a consistent case since it's used to determine size of record and the docs have different cases in few places.
                varname = "Byte count"
            if re.match(r"group\W*id", varname.lower(), re.IGNORECASE):  # force Group ID to a consistent case since it's used to determine size of record and the docs have different cases in few places.
                varname = "Group ID"
            d2.append([m.group('cnt'), m.group('dtype').lower(), varname, line[m.end():], line])  # bytesize, data type, text string, variable name, descr, full text line

    return name, d2


if __name__ == "__main__":
    # build the s57classes.py source file
    from HSTB.drivers.pos_mv import PUBS_ICD_004089_Rev10 as POSMV_UserManual
    print("processing", POSMV_UserManual.__file__)
    f = open("PCSclassesV5R10.py", "w")
    CreateClassFile(f)

    structures.clear()  # place finished data structures in this dictionary and other structures can then use them as a sub-type
    GROUP_ID_VALUES.clear()
    GROUP_VALUE_IDS.clear()
    MESSAGE_ID_VALUES.clear()
    MESSAGE_VALUE_IDS.clear()

    from HSTB.drivers.pos_mv import PUBS_ICD_004089_Rev9 as POSMV_UserManual
    print("processing", POSMV_UserManual.__file__)
    f = open("PCSclassesV5R9.py", "w")
    CreateClassFile(f)

    structures.clear()  # place finished data structures in this dictionary and other structures can then use them as a sub-type
    GROUP_ID_VALUES.clear()
    GROUP_VALUE_IDS.clear()
    MESSAGE_ID_VALUES.clear()
    MESSAGE_VALUE_IDS.clear()

    from HSTB.drivers.pos_mv import POSMV_V4_UserManual as POSMV_UserManual
    print("processing", POSMV_UserManual.__file__)
    f = open("PCSclassesV4.py", "w")
    CreateClassFile(f)
