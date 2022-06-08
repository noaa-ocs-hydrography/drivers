import os
from datetime import datetime
import xml.etree.ElementTree as ElementTree
import re
import rtree

# in python 2.7 we had to load an alternate sqlite3 DLL.
# This PYD won't work in 3.6, so either need to load a new one or confirm the stock sqlite3 works with caris database
# from HSTB.drivers.hips_support import _sqlite3 as sqlite3
import sqlite3
# from HSTB.drivers.hips_support import _sqlite3 as sqlite3

#from utils import hips_utils


class HIPSObject:
    """A generic object with id and attributes"""

    def __init__(self):
        """Initialize empty ID and attributes dictionary"""
        self.id = 0
        self.attributes = {}

    def __init__(self, id):
        """Initialize from ID, empty attributes dictionary"""
        self.id = id
        self.attributes = {}

    def __init__(self, id, attributes):
        """Initialize from ID and attributes dictionary"""
        self.id = id
        self.attributes = attributes

    def set_attributes(self, attributes):
        """Set attributes dictionary"""
        self.attributes = attributes

    def set_attribute(self, name, value):
        """Set attribute value by key name"""
        self.attributes[name] = value

    def get_attributes(self):
        """Return entire attributes dictionary"""
        return self.attributes

    def get_attribute(self, attribute_name):
        """Return a dictionary value based on the key"""
        return self.attributes[attribute_name]


class NavSources:
    """A class for parsing the XML nav source string stored with a HIPS line object."""

    reader_types = ["POSDIRECT", "ASCII", "SBET", "NavLab",
                    "NovAtel", "TerraPos", "HDCS", "Starfix", "Simrad"]
    """Reader types as used for HIPS navigation sources"""

    def __init__(self, sources_string):
        """
        Initialize based on the provided nav sources string
        Store the root ElementTree and first sources element
        """
        self.root = ElementTree.fromstring(sources_string)
        self.sources = self.root[0]

    def is_reader_type(self, name):
        """Return true if the string is found in the reader_types list."""
        return name in self.reader_types

    def get_reader_types(self):
        """Return the reader_types list"""
        return self.reader_types

    def list_nav_sources(self):
        """Return a list of the nav sources"""
        names = []
        for Converter in self.sources:
            names.append(Converter.find("Element").text)
        return names

    def list_nav_source_paths(self):
        """Return a dictionary of converter names and paths"""
        paths = {}
        for Converter in self.sources:
            name = Converter.find("Element").text
            path = []
            srcs = Converter.find("Composite[@Name='Sources']")
            for src in srcs.findall("Composite[@Name='Source']"):
                path.append(src.find("Element").text)
            paths[name] = path
        return paths

    def update_nav_source_path(self, type, new_path):
        """
        UNFINISHED
        Update a nav path in the sources list.
        Currently does not handle multiple sources for a single nav type.
        """
        if type in self.list_nav_sources():
            found = False
            for Converter in self.sources:
                if Converter.find("Element").text == type:
                    Converter[2][0][0].text = new_path
                    found = True
            if not found:
                raise Exception('Nav source type ' +
                                type + ' not found in line.')
        else:
            raise Exception('Nav source type ' + type + ' does not exist.')

    def tostring(self):
        """Return the serialized tree"""
        return '<?xml version="1.0"?>' + \
            ElementTree.tostring(self.root, method="xml", encoding="unicode")


class HIPSLine(HIPSObject):
    """A class representing a HIPS track line object."""

    def get_nav_sources(self):
        """Return a list of NavSources for the line"""
        if 'Sources' in list(self.attributes.keys()):
            nav_line = NavSources(self.attributes['Sources'])
            return nav_line.list_nav_source_paths()
        else:
            return []

    def update_nav_source(self, type, new_path, hips_conn):
        """
        UNFINISHED
        Update a nav source path in the database.
        Currently can only handle a single path for a given source type.
        """
        nav_line = NavSources(self.attributes['Sources'])
        if not nav_line.is_reader_type(type):
            raise Exception(
                'Type ' +
                type +
                ' not recognized as a valid navigation source type.\nValid input types are ' +
                ','.join(
                    nav_line.get_reader_types()))
        try:
            nav_line.update_nav_source_path(type, new_path)  # set the new path
        except Exception:
            raise Exception
        nav_string = nav_line.tostring()  # convert it back to a string
        if len(nav_string) > 0:  # better hope it's correct...
            hips_conn.cursor.execute(
                'UPDATE concreteAttribute SET stringValue=? JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE concreteObjectId=? AND attribute.name="sources";', [
                    nav_string, line_id])
            hips_conn.commit()  # no turning back
        return self.get_nav_sources  # return the updated sources string


class HIPSProject(HIPSObject):
    """A class representing a HIPS project"""

    attribute_types = {1: 'int', 2: 'float', 3: 'string',
                       4: 'list', 5: 'list', 6: 'raster', 7: 'datetime'}
    """Attribute types under the process model 1.0"""

    def __init__(self, path_to_project):
        """
        Initialize with a path to an existing project.
        Creates the SQLite connection and retrieves project attributes.
        """
        if os.path.exists(path_to_project):
            self.sq_hips_conn = sqlite3.connect(path_to_project)
            self.sq_hips_cursor = self.sq_hips_conn.cursor()
        else:
            raise Exception("HIPS project file not found " + path_to_project)

        # build the Project attributes manually, since it's spread across a few
        # tables
        self.attributes = {}
        self.sq_hips_cursor.execute('SELECT name from dataset WHERE id=1;')
        self.attributes['Project Name'] = self.sq_hips_cursor.fetchall()[0][0]
        try:
            self.attributes['Project Extents'] = self.single_value_query(1, 'projectExtents')
        except:
            self.attributes['Project Extents'] = None
        self.sq_hips_cursor.execute('SELECT referenceSystem from dataset WHERE id=1;')
        self.attributes['Reference System'] = self.sq_hips_cursor.fetchall()[0][0]
        try:
            ex_attrs = self.get_attributes_by_id(1)
        except:
            ex_attrs = {}
            for name, value in list(ex_attrs.items()):
                self.attributes[name] = value


    #*************************************************#
    #                                                 #
    # Line functions                                  #
    #                                                 #
    #*************************************************#

    def search_line_ids(self, search_pattern):
        """
        Search the database based on a string.
        search_pattern can be any part of the folder path for a given PVDL structure.
        This function prepends/appends a wildcard to either side of the pattern, which 
        is why the query formatting is different.
        This function returns EVERY result so may explode on large projects.
        """
        query = """SELECT SimpleFeatureView.id FROM SimpleFeatureView JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE SimpleFeatureView.datasetId = 1 AND SimpleFeatureView.value LIKE "%""" + \
            search_pattern + """%" AND attribute.name = 'linePath' AND SimpleFeatureView.deleted IS NOT 1;"""
        self.sq_hips_cursor.execute(query)
        return self.sq_hips_cursor.fetchall()

    def get_line_from_path(self, line_path, verify=False):
        """
        Search the database for a line matching the provided file path.
        line_path is expected to be the full path on disk.
        'verify' will verify if the directory exists before searching.
        """

        # uncomment the following to support URI handling with hips_utils
        # if "file://" in line_path:
        # line_path = hips_utils.hips_uri_to_path(line_path)[0]

        if verify and not os.path.isdir(line_path):
            raise Exception("Line folder not found " + line_path)

        exp = line_path.split('\\')
        # rebuild the V/D/L portion of the string
        VDL = [exp[-3], exp[-2], exp[-1]]
        result = self.search_line_ids('\\'.join(VDL))
        if result:
            # always uses the first result, expecting only 1 result
            line_id = result[0][0]
            the_line = HIPSLine(line_id, self.get_attributes_by_id(line_id))
            return the_line
        else:
            return result

    def get_lines(self):
        """Return a list of all HIPS line objects in the database"""
        lines = []
        for line_id in self.get_line_ids():
            lines.append(HIPSLine(line_id, self.get_attributes_by_id(line_id)))
        return lines

    def get_line_by_id(self, line_id):
        """Return the line associated with the requested ID"""
        if self.is_line_by_id(line_id):
            return HIPSLine(line_id, self.get_attributes_by_id(line_id))
        else:
            return []

    def get_line_ids(self):
        """Return a list of IDs."""
        line_ids = []
        query = 'SELECT SimpleFeatureView.id FROM SimpleFeatureView JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE SimpleFeatureView.datasetId = 1 AND attribute.name="linePath" AND SimpleFeatureView.deleted IS NOT 1 ORDER BY SimpleFeatureView.id;'
        for row in self.sq_hips_cursor.execute(query):
            line_ids.append(row[0])
        return line_ids

    def update_line_nav_source(self, line, type, new_path):
        """
        UNFINISHED
        Updates the nav type with the new path.
        Currently only supports a single source path.
        """
        line_id = self.__id_or_object(line)
        the_line = HIPSLine(line_id, self.get_attributes_by_id(line_id))
        result = ''
        try:
            result = the_line.update_nav_source(
                type, new_path, self.sq_hips_conn)
        except Exception:
            raise Exception
        return result

    def get_critical_soundings_by_line(self, line):
        """Returns a list of critical soundings associated with the line."""
        cs = []
        line_id = self.__id_or_object(line)
        query = """SELECT SimpleFeatureView.id FROM simpleFeatureView JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE SimpleFeatureView.name = "Critical Sounding" AND SimpleFeatureView.value = '""" + str(
            line_id) + """' AND attribute.name = 'lineId';"""
        for row in self.sq_hips_cursor.execute(query):
            cs_id = row[0]
            the_crit = HIPSObject(cs_id, self.get_attributes_by_id(cs_id))
            cs.append(the_crit)
        return cs

    def get_contacts_by_line(self, line):
        """Returns a list of side scan contacts associated with the line."""
        contacts = []
        line_id = self.__id_or_object(line)
        query = """SELECT SimpleFeatureView.id FROM SimpleFeatureView JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE SimpleFeatureView.datasetId = 2 AND SimpleFeatureView.value = '""" + str(
            line_id) + """' AND attribute.name='lineId';"""
        for row in self.sq_hips_cursor.execute(query):
            contact_id = row[0]
            the_contact = HIPSObject(
                contact_id, self.get_attributes_by_id(contact_id))
            contacts.append(the_contact)
        return contacts

    def get_line_extents(self, line):
        """
        Returns the minX,maxX,minY,maxY coordinates of the line object.
        This requires the RTree extension for sqlite, which is not enabled in the 
        default Python package.
        The "sqlite3xx.dll" from any CARIS \bin folder can be used to replace the 
        Python DLL 'sqlite3.dll'.
        """
        line_id = self.__id_or_object(line)
        id = minX = maxX = minY = maxY = 0
        query = 'SELECT * from lineIndex WHERE id=?;'
        row = self.sq_hips_cursor.execute(query, [str(line)]).fetchone()
        if len(row) > 0:
            id, minX, maxX, minY, maxY = row
        return [minX, maxX, minY, maxY]

    def is_line_by_id(self, id):
        """Check if the id is a valid one"""
        return id in self.get_line_ids()

    #*************************************************#
    #                                                 #
    # SS Contact functions                            #
    #                                                 #
    #*************************************************#

    def get_contacts(self):
        """Return a list of all side scan contacts in the project."""
        contacts = []
        for contact_id in self.get_contact_ids():
            contacts.append(HIPSObject(
                contact_id, self.get_attributes_by_id(contact_id)))
        return contacts

    def get_contact_ids(self):
        """Return a list of all side scan contact IDs in the project."""
        contact_ids = []
        query = 'SELECT SimpleFeatureView.id FROM SimpleFeatureView JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE datasetId = 2 AND attribute.name="lineId" ORDER BY SimpleFeatureView.id;'
        for row in self.sq_hips_cursor.execute(query):
            contact_ids.append(row[0])
        return contact_ids

    #*************************************************#
    #                                                 #
    # Critical sounding functions                     #
    #                                                 #
    #*************************************************#

    def get_critical_soundings(self):
        """Return a list of all critical soundings in the project."""
        cs = []
        for cs_id in self.get_critical_sounding_ids():
            cs.append(HIPSObject(cs_id, self.get_attributes_by_id(cs_id)))
        return cs

    def get_critical_sounding_ids(self):
        """Return a list of all critical sounding IDs in the project."""
        cs_ids = []
        query = 'SELECT SimpleFeatureView.id FROM SimpleFeatureView JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE SimpleFeatureView.name = "Critical Sounding" AND attribute.name="lineId" ORDER BY SimpleFeatureView.id;'
        for row in self.sq_hips_cursor.execute(query):
            cs_ids.append(row[0])
        return cs_ids

    #*************************************************#
    #                                                 #
    # Misc functions                                  #
    #                                                 #
    #*************************************************#

    def convert_utc_time(self, time):
        """Convert a HIPS timestamp (float UTC) to ISO format"""
        return datetime.utcfromtimestamp(time / 1000).isoformat()

    def single_value_query(self, obj_id, attribute_id):
        """Return a single attribute value for a single database ID"""
        self.sq_hips_cursor.execute(
            'SELECT SimpleFeatureView.value FROM SimpleFeatureView JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE SimpleFeatureView.id=? AND attribute.name = ?;', [
                str(obj_id), str(attribute_id)])
        result = self.sq_hips_cursor.fetchall()
        if result:
            return result[0][0]  # we only expect a single result, return that
        else:
            return result

    def get_attributes_by_id(self, obj_id):
        """
        Return a dictionary of attributes for a single database ID
        This function attempts to handle the stored data type and performs an appropriate conversion.
        """
        attributes = {}
        for row in self.sq_hips_cursor.execute(
            'SELECT attribute.name,attribute.type,SimpleFeatureView.value FROM SimpleFeatureView JOIN attribute ON (SimpleFeatureView.attributeId = attribute.id) WHERE SimpleFeatureView.id=? ORDER BY SimpleFeatureView.attributeId;', [
                str(obj_id)]):
            name, type, value = row
            name = self.camel_to_string(name)
            if self.attribute_types[type] == 'int':
                value = int(value)
            elif self.attribute_types[type] == 'float':
                value = float(value)
            elif self.attribute_types[type] == 'string':
                value = str(value)
            # treat raster as a list, for this implementation
            elif self.attribute_types[type] == 'list' or self.attribute_types[type] == 'raster':
                # check for an existing list
                if name in list(attributes.keys()):
                    value = attributes[name] + ',' + str(value)
                else:
                    value = str(value)
            elif self.attribute_types[type] == 'datetime':
                value = self.convert_utc_time(float(value))
            attributes[name] = value
        return attributes

    def __id_or_object(self, obj):
        """Interal function to handle passing either ID or HIPSLine to any function"""
        id = 0
        if isinstance(obj, int):
            id = obj
        elif isinstance(obj, str):
            id = int(obj)
        elif isinstance(obj, HIPSLine):
            id = obj.id
        return id

    def camel_to_string(self, name):
        """Converts a camelCase string to Title Case"""
        return re.sub(
            r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', name).title()

    def delete_object(self, obj_id):
        """
        Delete a given object from the datase.
        This is obviously a dangerous method to include.
        """
        rows = self.sq_hips_cursor.execute(
            'DELETE FROM concreteObject WHERE id=?;', [str(obj_id)]).rowcount
        self.sq_hips_conn.commit()
        return rows + ' objects deleted.'

    def list_locks(self):
        """Returns a list of all locks set in the database."""
        locks = []
        for row in self.sq_hips_cursor.execute(
                'SELECT * FROM objectState WHERE locked = 1;'):
            locks.append(row)
        return locks

    def clear_locks(self):
        """Clears all locks from the database."""
        rows = self.sq_hips_cursor.execute(
            'UPDATE objectState SET locked = 0;').rowcount
        self.sq_hips_conn.commit()
        return str(rows) + ' locks cleared.'
