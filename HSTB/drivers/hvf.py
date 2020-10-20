import xml.etree.ElementTree as ET
import datetime
import sets

import pandas


class HVF:
    # sensor_consts=enum
    sensors = {"DepthSensor"}

    def __init__(self, path_to_vessel_hvf):
        self.root = ET.fromstring(open(path_to_vessel_hvf).read())

    def get_sensor(self, sensor_name):
        """Returns a top level element (like DepthSensor) that matches the supplied name"""
        sensors = self.root.findall(sensor_name)
        if len(sensors) > 1:
            raise Exception("Unexpected multiple entries for {}".format(sensor_name))
        else:
            sensor = sensors[0]
        return sensor

    @staticmethod
    def timestamp_to_datetime(timestamp):
        """Change a caris HVF timestamp value into a python datetime object"""
        return datetime.datetime.strptime(timestamp, "%Y-%j %H:%M:%S")

    def get_sensor_at_time(self, sensor_name, dt):
        """Returns a top level element (like DepthSensor) AT or BEFORE the supplied datetime"""
        try:
            sensor = self.get_sensor(sensor_name)
            timestamps = sensor.findall("TimeStamp")
            return self.get_closest_timestamp(sensor, timestamps, dt)
        except:
            return None, None

    @staticmethod
    def get_closest_timestamp(sensor, timestamps, dt):
        """Given a top level element (like DepthSensor) return the closest TimeStamp element AT or BEFORE the supplied datetime"""
        datetimes = [HVF.timestamp_to_datetime(ts.attrib['value']) for ts in timestamps]
        df = pandas.DataFrame(timestamps, datetimes)
        i = df.index.searchsorted(dt, side="right")
        if i == 0:
            retval = None, None
        else:
            retval = df.index[i - 1].to_pydatetime(), df.iloc[i - 1, 0]
        return retval

    def get_all_timestamp_elements(self):
        """Returns a list of tuples of top level elements (like DepthSensor) and their timestamps"""
        recs = [(c, c.findall("TimeStamp")) for c in self.root]
        recs2 = [rec for rec in recs if rec[1]]
        return recs2

    def get_all_timestamps(self):
        """Returns a consolidated list of unique TimeStamp string values"""
        stamps = []
        for e, times in self.get_all_timestamp_elements():
            stamps.extend(times)
        all_times = list(sets.Set([s.attrib['value'] for s in stamps]))
        all_times.sort()
        return all_times

    def get_all_datetimes(self):
        """Returns a consolidated list of unique TimeStamps as datetime objects"""
        all_times = self.get_all_timestamps()
        all_datetimes = [self.timestamp_to_datetime(timestamp) for timestamp in all_times]
        return all_datetimes

    def get_all_at_time(self, dt):
        """Returns a list of tuples, each contains a top level element and it's TimeStamp children"""
        retval = []
        for elem, timestamps in self.get_all_timestamp_elements():
            rec_dt, data = self.get_closest_timestamp(elem, timestamps, dt)
            retval.append([elem, rec_dt, data])
        return retval
