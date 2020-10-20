import xml.etree.ElementTree as ElementTree
import os


class CARISObject:
    """A generic CARIS object with a name"""

    def __init__(self):
        """Initialize with empty name"""
        self.name = ''

    def __init__(self, name):
        """Initialize with a name provided"""
        self.name = name

    def set_name(self, name):
        """Set the name"""
        if name:
            self.name = name

    def get_name(self):
        """Return the name"""
        return self.name


class CARISSource(CARISObject):
    """A CARIS source object under Process Model 1.0"""

    def __init__(self):
        """Initialize with empty name, type and data"""
        self.name = ''
        self.stype = ''
        self.sdata = ''

    def set_type(self, dtype):
        """Set the type"""
        if dtype:
            self.stype = dtype

    def set_data(self, data):
        """Set the data"""
        if data:
            self.sdata = data

    def get_type(self):
        """Return the type"""
        return self.stype

    def get_data(self):
        """Return the data"""
        return self.sdata


class CARISLog():
    """A CARIS log object under Process Model 1.0"""

    def __init__(self):
        """Initialize with empty user, software, start/end times"""
        self.user = ''
        self.software = ''
        self.startTime = ''
        self.endTime = ''

    def set_user(self, user):
        """Set the user"""
        if user:
            self.user = user

    def set_software(self, software):
        """Set the software"""
        if software:
            self.software = software

    def set_start_time(self, startTime):
        """Set the start time"""
        if startTime:
            self.startTime = startTime

    def set_end_time(self, endTime):
        """Set the end time"""
        if endTime:
            self.endTime = endTime

    def get_user(self):
        """Return the user"""
        return self.user

    def get_software(self):
        """Return the software"""
        return self.software

    def get_start_time(self):
        """Return the start time"""
        return self.startTime

    def get_end_time(self):
        """Return the end time"""
        return self.endTime


class CARISPort(CARISObject):
    """A CARIS port under Process Model 1.0"""

    def __init__(self):
        """Initialize with empty name and sources list"""
        self.name = ''
        self.sources = []

    def set_sources(self, sources):
        """Set the sources list"""
        if sources:
            self.sources = sources

    def get_sources(self):
        """Get the sources list"""
        return self.sources

    def get_source(self, index):
        """Get a source by index"""
        return self.sources[index]


class CARISProcess(CARISObject):
    """ A CARIS Process under Process Model 1.0"""

    def __init__(self):
        """Initialize with empty name, version, ports dictionary, and log list"""
        self.name = ''
        self.version = ''
        self.ports = {}
        self.log = []

    def set_version(self, version):
        """Set the version"""
        if version:
            self.version = version

    def set_ports(self, ports):
        """Set the ports dictionary"""
        if ports:
            self.ports = ports

    def add_port(self, name, port):
        """Add a port to the dictionary"""
        if port:
            self.ports[name] = port

    def set_log(self, log):
        """Set the log list"""
        if log:
            self.log = log

    def get_version(self):
        """Return the version"""
        return self.version

    def get_ports(self):
        """Return the ports dictionary"""
        return self.ports

    def get_port(self, name):
        """Return a port value by key"""
        return self.ports[name]

    def get_log(self):
        """Return the log list"""
        return self.log


class HIPSLog:
    """
    A class representing a HIPS line log.
    Applicable only for logs created in HIPS v10.0.0 and above (Process.log)
    """

    def __init__(self):
        """Initialize with empty source path, process list and version"""
        self.source_path = ''
        self.processes = []
        self.version = ''

    def __init__(self, log_path):
        """Initialize from an existing log path, which processes all entries into this object."""
        self.source_path = log_path
        self.processes = []
        tree = ElementTree.parse(log_path)
        root = tree.getroot()
        self.version = root.find('version').text
        for process in root.findall('process'):
            proc_obj = self.__parse_process(process)
            self.processes.append(proc_obj)

    def set_source_path(self, path):
        """Set the source path"""
        if path:
            self.source_path = path

    def set_version(self, version):
        """Set the version"""
        if version:
            self.version = version

    def set_processes(self, process):
        """Set the processes list"""
        if process:
            self.processes = process

    def get_source_path(self):
        """Return the source path"""
        return self.source_path

    def get_version(self):
        """Return the version"""
        return self.version

    def get_processes(self):
        """Return the list of processes"""
        return self.processes

    def get_process(self, index):
        """Return a specific process object by index"""
        return self.processes[index]

    def get_last_process(self, process_name):
        """Returns the last log entry of the provided name."""
        return self.get_process(next(i for i, v in zip(list(range(len(
            self.processes) - 1, -1, -1)), reversed(self.processes)) if v.get_name() == process_name))

    def has_process(self, process_name):
        """Check if the process exists in the log"""
        return any(process_name in s.get_name() for s in self.processes)

    def __parse_process(self, process):
        """Internal process to parse the process XML"""
        proc_obj = CARISProcess()
        # set metadata
        proc_obj.set_name(process.find('id').text)
        proc_obj.set_version(process.find('version').text)
        log = process.find('log')
        log_obj = CARISLog()
        log_obj.set_user(log.find('user').text)
        log_obj.set_start_time(log.find('start').text)
        log_obj.set_end_time(log.find('end').text)
        soft = log.find('software')
        log_obj.set_software(
            soft.find('id').text +
            ' ' +
            soft.find('version').text)
        proc_obj.set_log(log_obj)
        # add ports
        for option in process.findall('port'):
            opt_obj = self.__parse_port(option)
            proc_obj.add_port(opt_obj.get_name(), opt_obj)
        return proc_obj

    def __parse_port(self, option):
        """Internal process to parse each port (option) of the log entry"""
        opt_obj = CARISPort()
        opt_obj.set_name(option.find('id').text)
        for source in option.findall('source'):
            src_obj = self.__parse_source(source)
            opt_obj.sources.append(src_obj)
        return opt_obj

    def __parse_source(self, source):
        """Internal process to parse each source of a given port"""
        src_obj = CARISSource()
        data = source.find('data')
        simple = data.find('simple')
        if simple:
            src_obj.set_name('simple')
            src_obj.set_type(simple.find('type').text)
            src_obj.set_data(simple.find('value').text)
        else:
            complex_v = data.find('complex')
            if complex_v:
                src_obj.set_name('complex')
                src_obj.set_type('complex')
                # simply store this part of the ETree
                src_obj.set_data(complex_v)
        return src_obj
