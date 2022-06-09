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

    def __init__(self, id=0):
        """Initialize a HIPS Object"""
        self.id = id
        self.attributes = {}
        self.dirty = False

    def __init__(self, id, attributes):
        """Initialize from ID and attributes dictionary"""
        self.id = id
        self.attributes = attributes

    def set_attributes(self, attributes):
        """Set attributes dictionary"""
        self.attributes = attributes
        self.dirty = True

    def set_attribute(self, name, value):
        """Set attribute value by key name"""
        self.attributes[name] = value
        self.dirty = True

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
                path.append(src.find("Element[@Name='Path']").text)
            paths[name] = path
        return paths

    def update_nav_source_path(self, type, new_path):
        """
        Update a nav path in the sources list.
        The new file name must match the old file name, only the path will be updated
        """
        if type in self.list_nav_sources():
            found = False
            replaced = False
            path, f_name = os.path.split(new_path)
            for Converter in self.sources:
                if Converter.find("Element[@Name='Name']").text == type:
                    found = True
                    srcs = Converter.find("Composite[@Name='Sources']")
                    for src in srcs.findall("Composite[@Name='Source']"):
                        path_el = src.find("Element[@Name='Path']")
                        if f_name in path_el.text:
                            path_el.text = new_path
                            replaced = True
            if not found:
                raise Exception('Nav source type ' +
                                type + ' not found in line.')
            if not replaced:
                raise Exception('Nav source file ' +
                                f_name + ' not found in line.')
        else:
            raise Exception('Nav source type ' + type + ' does not exist.')

    def tostring(self):
        """Return the serialized tree"""
        return '<?xml version="1.0"?>' + \
            ElementTree.tostring(self.root, method="xml", encoding="unicode")


class HIPSLine(HIPSObject):
    """A class representing a HIPS track line object."""

    def get_nav_sources(self):
        """Return the NavSource object for the line"""
        if 'Sources' in self.attributes.keys():
            return NavSources(self.attributes['Sources'])
        else:
            return []

    def update_nav_source(self, nav_obj):
        """
        Update the nav source string based on a modified NavSource object
        """
        self.attributes['Sources'] = nav_obj.tostring()
        self.dirty = True


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

        self.attributes = {}

        # set the version first, this affects everything downstream
        result = self.select_query(columns='RELEASE_VERSION', table='hipsProjectVersion')
        self.attributes['Version'] = int(result[0][0])

        # get the object types in this database
        self.object_types = self.get_object_types()

        # build the Project attributes manually, since it's spread across a few
        # tables
        result = self.select_query(columns='name',
                                   table='dataset',
                                   where='id=?',
                                   params=(1,),
                                   )
        self.attributes['Project Name'] = result[0][0]

        result = self.select_query(columns='referenceSystem',
                                   table='dataset',
                                   where='id=?',
                                   params=(1,),
                                   )
        self.attributes['Reference System'] = result[0][0]

        # get the remaining attributes as normal
        ex_attrs = self.get_attributes_by_id(1)
        for name, value in ex_attrs.items():
            self.attributes[name] = value

    # *************************************************#
    #                                                 #
    # Line functions                                  #
    #                                                 #
    # *************************************************#

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
        """Return a list of line IDs."""
        return self.get_ids_by_type(type='Line')

    def search_line_ids(self, search_pattern):
        """
        Search the database based on a string.
        search_pattern can be any part of the folder path for a given PVDL structure.
        """
        return self.get_ids_by_type(type='Line', search=search_pattern)

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

        # use the line folder name only
        rel_line_path = line_path.split('\\')[-1]
        result = self.search_line_ids(rel_line_path)
        for line_id in result:
            the_line = HIPSLine(line_id, self.get_attributes_by_id(line_id))
            # make sure it is an exact match before returning,
            # search can return partial matches
            l_path = the_line.get_attribute('Line Path').split('\\')[-1]
            if l_path == rel_line_path:
                return the_line
        return []

    # def get_line_extents(self, line):
    # """
    # Returns the minX,maxX,minY,maxY coordinates of the line object.
    # This requires the RTree extension for sqlite, which is not enabled in the
    # default Python package.
    # The "sqlite3xx.dll" from any CARIS \bin folder can be used to replace the
    # Python DLL 'sqlite3.dll'.
    # """
    # exts = []
    # line_id = self.__id_or_object(line)
    # id = minX = maxX = minY = maxY = 0
    # result = self.select_query(table='lineIndex',where='id=?',params=(line,))
    # if len(result[0]) > 0:
    # id, minX, maxX, minY, maxY = result[0]
    # exts = [minX, maxX, minY, maxY]
    # return exts

    def is_line_by_id(self, id):
        """Check if the id is a valid one"""
        line_id = self.__id_or_object(id)
        return line_id in self.get_line_ids()

    # *************************************************#
    #                                                 #
    # SS Contact functions                            #
    #                                                 #
    # *************************************************#

    def get_contacts(self):
        """Return a list of all side scan contacts in the project."""
        contacts = []
        for contact_id in self.get_contact_ids():
            contacts.append(HIPSObject(
                contact_id, self.get_attributes_by_id(contact_id)))
        return contacts

    def get_contact_ids(self):
        """Return a list of all side scan contact IDs in the project."""
        return self.get_ids_by_type(type='Contact')

    def get_contacts_by_line(self, line):
        """Returns a list of side scan contacts associated with the line."""
        contacts = []
        line_id = self.__id_or_object(line)
        results = self.get_ids_by_type(type='Contact', related_id=line_id)
        for contact_id in results:
            the_contact = HIPSObject(
                contact_id, self.get_attributes_by_id(contact_id))
            contacts.append(the_contact)
        return contacts

    # *************************************************#
    #                                                 #
    # Critical sounding functions                     #
    #                                                 #
    # *************************************************#

    def get_critical_soundings(self):
        """Return a list of all critical soundings in the project."""
        cs = []
        for cs_id in self.get_critical_sounding_ids():
            cs.append(HIPSObject(cs_id, self.get_attributes_by_id(cs_id)))
        return cs

    def get_critical_sounding_ids(self):
        """Return a list of all critical sounding IDs in the project."""
        return self.get_ids_by_type(type='Critical Sounding')

    def get_critical_soundings_by_line(self, line):
        """Returns a list of critical soundings associated with the line."""
        cs = []
        line_id = self.__id_or_object(line)
        results = self.get_ids_by_type(
            type='Critical Sounding', related_id=line_id)
        for cs_id in results:
            the_crit = HIPSObject(cs_id, self.get_attributes_by_id(cs_id))
            cs.append(the_crit)
        return cs

    # *************************************************#
    #                                                 #
    # Vessel functions                                #
    #                                                 #
    # *************************************************#

    def get_vessels(self):
        """Returns a list of all vessels in the project."""
        vess = []
        if self.get_attribute('Version') == 1:
            for line in self.get_lines():
                l_path = line.get_attribute('Line Path')
                vess_name = l_path.split('\\')[-3:-2][0]  # first folder name after Project Dir
                vess_path = '..\\VesselConfig\\' + vess_name + '.hvf'  # we don't know absolute path, so return relative
                if not vess_path in (item[1] for item in vess):
                    # 2.0 format is (id,path,modtime) so let's fake it for 1.0
                    vess.append((len(vess) + 1, vess_path, 0))
        elif self.get_attribute('Version') == 2:
            results = self.select_query(table='vesselFile')
            for vessel in results:
                vess.append(vessel)

        return vess

    def get_vessel_by_id(self, vess_id):
        vess = self.select_query(table='vesselFile',
                                 where='id=?',
                                 params=(vess_id),
                                 )
        return vess[0]

    def update_vessel_source_path(self, id, new_path):
        """Sets the given vessel id to the new path."""
        result = self.update_query(table='vesselFile',
                                   change='path=?',
                                   where='id=?',
                                   params=(new_path, id,),
                                   )
        return result

    # *************************************************#
    #                                                 #
    # Database functions                              #
    #                                                 #
    # *************************************************#

    def select_query(self, columns='', table='', join='',
                     where='', order_by='', params=()):
        """Runs a SELECT query on the database"""
        result = []
        query = ''
        if table == '':
            return result
        if columns == '':
            columns = '*'
        query = ' '.join(['SELECT', columns, 'FROM', table])
        if join != '':
            query = ' '.join([query, 'JOIN', join])
        if where != '':
            query = ' '.join([query, 'WHERE', where])
        if order_by != '':
            query = ' '.join([query, 'ORDER', 'BY', order_by])
        query += ';'
        if not isinstance(params, tuple):
            params = (params,)

        self.sq_hips_cursor.execute(query, params)
        result = self.sq_hips_cursor.fetchall()
        return result

    def update_query(self, table='', change='', where='', params=()):
        """Runs an UPDATE query on the database"""
        query = ''
        if table == '':
            return 0
        query = ' '.join(['UPDATE', table, 'SET', change])
        if where != '':
            query = ' '.join([query, 'WHERE', where])
        query += ';'
        if not isinstance(params, tuple):
            params = (params,)

        rows = self.sq_hips_cursor.execute(query, params).rowcount
        self.sq_hips_conn.commit()
        return rows

    def get_ids_by_type(self, type, related_id=None, search=''):
        """
        get_ids_by_type handles most of the database interaction.
        type must be an object type defined in the schema, and found in the object table.
        if related_id is set, it will only return objects associated with that id.
        search is only applied if type is 'Line'.
        """

        class h_criteria():
            """A small helper class to build WHERE statements"""

            def __init__(self):
                self.query = ''
                self.params = ()

            def add_query(self, new_str, new_param=()):
                """Add a statement to the WHERE clause"""
                if '?' in new_str and not new_param:
                    return  # don't add the query if no parameter is provided
                if self.query != '':
                    self.query = self.query + ' AND ' + new_str
                else:
                    self.query = new_str
                if new_param:
                    self.params = self.params + (new_param,)

        ids = []
        results = []
        criteria = h_criteria()
        columns = table = join = order_by = ''

        # Build the query string
        if self.get_attribute('Version') == 1:
            """ HIPS project schema version 1 """
            if 'Contact' in type:
                # use datasetId instead of name for contacts, since they can
                # have many names
                criteria.add_query('SimpleFeatureView.datasetId=?', 2)
            else:
                criteria.add_query('SimpleFeatureView.name=?', type)

            if 'Line' in type:
                # search linePath instead of lineId
                criteria.add_query('attribute.name=?', 'linePath')
                criteria.add_query('SimpleFeatureView.deleted IS NOT 1')
                if search != '':
                    criteria.add_query(
                        'SimpleFeatureView.value LIKE ?',
                        '%' + search + '%')
            else:
                criteria.add_query('attribute.name=?', 'lineId')
                if related_id:
                    criteria.add_query('SimpleFeatureView.value=?', related_id)
            columns = 'SimpleFeatureView.id'
            table = 'SimpleFeatureView'
            join = 'attribute ON (SimpleFeatureView.attributeId=attribute.id)'
            order_by = 'SimpleFeatureView.id'
        elif self.get_attribute('Version') == 2:
            """ HIPS project schema version 2 """
            if 'Line' in type:
                criteria.add_query(
                    'Line.concreteObjectId NOT IN (SELECT objectState.concreteObjectId from objectState WHERE deleted=1)')
                if search != '':
                    criteria.add_query('linePath LIKE ?', '%' + search + '%')
            elif related_id:
                criteria.add_query('lineId=?', related_id)
            if ' ' in type:
                # handles 'Critical Sounding' case
                type = type.replace(' ', '_')
            columns = 'concreteObjectId'
            order_by = 'concreteObjectId'
            table = type
        else:
            return ids
        results = self.select_query(columns=columns,
                                    table=table,
                                    join=join,
                                    where=criteria.query,
                                    order_by=order_by,
                                    params=criteria.params,
                                    )
        for row in results:
            ids.append(row[0])
        return ids

    def single_value_query(self, obj_id, attribute_id):
        """Return a single attribute value for a single database ID"""
        result = []
        if self.get_attribute('Version') == 1:
            result = self.select_query(columns='SimpleFeatureView.value',
                                       table='SimpleFeatureView',
                                       join='attribute ON (SimpleFeatureView.attributeId=attribute.id)',
                                       where='SimpleFeatureView.id=? AND attribute.name=?',
                                       params=(str(obj_id), str(attribute_id)),
                                       )
        elif self.get_attribute('Version') == 2:
            obj_name = self.get_object_name(self.get_object_type(obj_id))
            result = self.select_query(columns=self.string_to_camel(attribute_id),
                                       table=obj_name,
                                       where='concreteObjectId=?',
                                       params=(str(obj_id),),
                                       )
        else:
            return []
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
        if self.get_attribute('Version') == 1:
            # v1 schema is one attribute per row, we iterate over them
            result = self.select_query(columns='attribute.name,attribute.type,SimpleFeatureView.value',
                                       table='SimpleFeatureView',
                                       join='attribute ON (SimpleFeatureView.attributeId=attribute.id)',
                                       where='SimpleFeatureView.id=?',
                                       params=(str(obj_id)),
                                       )
            for row in result:
                name, type, value = row
                name = self.camel_to_string(name)
                if self.attribute_types[type] == 'list' or self.attribute_types[type] == 'raster':
                    # check for an existing list
                    if name in attributes.keys():
                        value = attributes[name] + ',' + str(value)
                attributes[name] = self.value_to_type(type, value)
        elif self.get_attribute('Version') == 2:
            # v2 schema is one row per object (obj), we iterate attribute names
            # instead
            obj_name = self.get_object_name(self.get_object_type(obj_id))
            att_names = self.get_attribute_names(obj_name)
            result = self.select_query(table=obj_name,
                                       where=obj_name + '.concreteObjectId=?',
                                       params=(str(obj_id),),
                                       )
            obj = result[0]  # should only be one result
            for attribute in att_names:
                id, name, type = attribute
                if name == 'geometry':
                    continue
                name = self.camel_to_string(name)
                value = obj[id]
                if self.attribute_types[type] == 'list' or self.attribute_types[type] == 'raster':
                    if name in attributes.keys():
                        value = attributes[name] + ',' + str(value)
                attributes[name] = self.value_to_type(type, value)
        else:
            return []

        return attributes

    def get_object_types(self):
        """Retrieve a list of HIPS schema Object types."""
        types = {}
        result = self.select_query(columns='id,name',
                                   table='object',
                                   )
        for row in result:
            id, name = row
            types[int(id)] = name.replace(' ', '_')
        return types

    def get_attribute_names(self, table_name):
        """HIPS v2 schema only. Returns a list of attribute [id,name,type] from the table."""
        names = []
        query = 'PRAGMA table_info(' + table_name + ');'
        for row in self.sq_hips_cursor.execute(query):
            id, name, type, temp, default, pkey = row
            names.append([id, name, type])

        # clean up data types
        for name in names:
            if name[1] == 'id' or name[1] == 'concreteObjectId':
                name[2] = 1  # type int
            elif name[1] == 'geometry':
                name[2] = None
            else:
                result = self.select_query(columns='type',
                                           table='attribute',
                                           where='name=?',
                                           params=(str(name[1]),),
                                           )
                type = int(result[0][0])
                name[2] = type
        return names

    def get_object_type(self, id):
        """Get the Object type based on its ID."""
        result = self.select_query(columns='concreteObject.objectId',
                                   table='concreteObject',
                                   where='id=?',
                                   params=(str(id),)
                                   )
        if result:
            return int(result[0][0])  # we only expect a single result
        else:
            return 0

    def get_object_name(self, id):
        """Get the Object name based on its ID."""
        if id in self.object_types.keys():
            return self.object_types[id]
        else:
            return ''

    def delete_object(self, obj_id):
        """
        Delete a given object from the database.
        This is obviously a dangerous method to include.
        """
        rows = self.sq_hips_cursor.execute(
            'DELETE FROM concreteObject WHERE id=?;', [str(obj_id)]).rowcount
        self.sq_hips_conn.commit()
        return rows + ' objects deleted.'

    def save_object(self, obj):
        """Save any changes made to the object"""
        if obj.dirty:
            for key, value in obj.get_attributes().items():
                key = self.string_to_camel(key)
                if not value:
                    continue
                if self.get_attribute('Version') == 1:
                    data_type = ''
                    if isinstance(value, float):
                        data_type = 'floatValue'
                    elif isinstance(value, int):
                        data_type = 'integerValue'
                    else:  # assume string and hope for the best
                        data_type = 'stringValue'
                    self.update_query(table='concreteAttribute',
                                      change=data_type + '=?',
                                      where=' '.join(['concreteObjectId=?',
                                                      'AND attributeId IN',
                                                      '(SELECT attribute.id from attribute WHERE attribute.name=?)']),
                                      params=(str(value), str(obj.id), key)
                                      )
                elif self.get_attribute('Version') == 2:
                    obj_name = self.get_object_name(
                        self.get_object_type(obj.id))
                    self.update_query(table=obj_name,
                                      change=key + '=?',
                                      where=obj_name + '.concreteObjectId=?',
                                      params=(str(value), str(obj.id))
                                      )
            obj.dirty = False

    def list_locks(self):
        """Returns a list of all locks set in the database."""
        locks = []
        locks = self.select_query(
            table='objectState',
            where='locked=?',
            params=(
                1,
            ))
        return locks

    def clear_locks(self):
        """Clears all locks from the database."""
        rows = 0
        rows = self.update_query(
            table='objectState',
            change='locked=?',
            params=(
                0,
            ))
        return str(rows) + ' locks cleared.'

    # *************************************************#
    #                                                 #
    # Misc functions                                  #
    #                                                 #
    # *************************************************#

    def __id_or_object(self, obj):
        """Internal function to handle passing either ID or HIPSLine to any function"""
        id = 0
        if isinstance(obj, int):
            id = obj
        elif isinstance(obj, str):
            id = int(obj)
        elif isinstance(obj, HIPSObject):
            id = obj.id
        return id

    def value_to_type(self, type, value):
        """Handle type conversion from CARIS type to Python."""
        if value:
            if self.attribute_types[type] == 'int':
                return int(value)
            elif self.attribute_types[type] == 'float':
                return float(value)
            elif self.attribute_types[type] == 'string':
                return str(value)
            # treat raster as a list, for this implementation
            elif self.attribute_types[type] == 'list' or self.attribute_types[type] == 'raster':
                return str(value)
            elif self.attribute_types[type] == 'datetime':
                return float(value)
            else:
                return value
        return None

    def convert_utc_time_iso(self, time):
        """Convert a HIPS timestamp (float UTC) to ISO format"""
        return self.convert_utc_time(time).isoformat()

    def convert_utc_time(self, time):
        """Convert a HIPS timestamp (float UTC) to Python Datetime"""
        try:
            the_time = datetime.utcfromtimestamp(time / 1000)
        except BaseException:
            return time  # don't convert the value if it fails
        return the_time

    def camel_to_string(self, name):
        """Converts a camelCase string to Title Case"""
        return re.sub(
            r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', name).title()

    def string_to_camel(self, name):
        """Converts a Title Case string to camelCase"""
        name = name.replace(' ', '')
        return name[0].lower() + name[1:]