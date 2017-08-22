

class Sensor(object):
    def __init__(self, short_name, value, unit=None, name=None, description=None):
        self._short_name = short_name
        self._value = value
        self._unit = unit
        self._name = name
        self._description = description
