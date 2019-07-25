from __future__ import unicode_literals

try:
    import simplejson as json
except ImportError:
    import json

from collections import MutableMapping

try:
    import simplejson as json
except ImportError:
    import json

import sys
from decimal import Decimal

mapping_base = MutableMapping

GEO_INTERFACE_MARKER = "__geo_interface__"


class GeoJSON(dict):
    """
    A class representing a GeoJSON object.
    """

    def __init__(self, iterable=(), **extra):
        """
        Initialises a GeoJSON object

        :param iterable: iterable from which to draw the content of the GeoJSON
        object.
        :type iterable: dict, array, tuple
        :return: a GeoJSON object
        :rtype: GeoJSON
        """
        super(GeoJSON, self).__init__(iterable)
        self["type"] = getattr(self, "type", type(self).__name__)
        self.update(extra)

    def __repr__(self):
        return dumps(self, sort_keys=True)

    __str__ = __repr__

    def __getattr__(self, name):
        """
        Permit dictionary items to be retrieved like object attributes

        :param name: attribute name
        :type name: str, int
        :return: dictionary value
        """
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        """
        Permit dictionary items to be set like object attributes.

        :param name: key of item to be set
        :type name: str
        :param value: value to set item to
        """

        self[name] = value

    def __delattr__(self, name):
        """
        Permit dictionary items to be deleted like object attributes

        :param name: key of item to be deleted
        :type name: str
        """

        del self[name]

    @property
    def __geo_interface__(self):
        if self.type != "GeoJSON":
            return self

    @classmethod
    def to_instance(cls, ob, default=None, strict=False):
        """Encode a GeoJSON dict into an GeoJSON object.
        Assumes the caller knows that the dict should satisfy a GeoJSON type.

        :param cls: Dict containing the elements to be encoded into a GeoJSON
        object.
        :type cls: dict
        :param ob: GeoJSON object into which to encode the dict provided in
        `cls`.
        :type ob: GeoJSON
        :param default: A default instance to append the content of the dict
        to if none is provided.
        :type default: GeoJSON
        :param strict: Raise error if unable to coerce particular keys or
        attributes to a valid GeoJSON structure.
        :type strict: bool
        :return: A GeoJSON object with the dict's elements as its constituents.
        :rtype: GeoJSON.object
        :raises TypeError: If the input dict contains items that are not valid
        GeoJSON types.
        :raises UnicodeEncodeError: If the input dict contains items of a type
        that contain non-ASCII characters.
        :raises AttributeError: If the input dict contains items that are not
        valid GeoJSON types.
        """
        if ob is None and default is not None:
            instance = default()
        elif isinstance(ob, GeoJSON):
            instance = ob
        else:
            mapping = to_mapping(ob)
            d = {}
            for k in mapping:
                d[k] = mapping[k]
            try:
                type_ = d.pop("type")
                try:
                    type_ = str(type_)
                except UnicodeEncodeError:
                    # If the type contains non-ascii characters, we can assume
                    # it's not a valid GeoJSON type
                    raise AttributeError("{0} is not a GeoJSON type".format(type_))

                    # geojson_factory = getattr(all, type_)
                    # if not issubclass(geojson_factory, GeoJSON):
                    #     raise TypeError("""\
                    #     Not a valid GeoJSON type:
                    #     %r (geojson_factory: %r, cls: %r)
                    #     """ % (type_, geojson_factory, cls))
                    # instance = geojson_factory(**d)
            except (AttributeError, KeyError) as invalid:
                if strict:
                    msg = "Cannot coerce %r into a valid GeoJSON structure: %s"
                    msg %= (ob, invalid)
                    raise ValueError(msg)
                instance = ob
        return instance


class Geometry(GeoJSON):
    """
    Represents an abstract base class for a WGS84 geometry.
    """

    if sys.version_info[0] == 3:
        # Python 3.x has no long type
        __JSON_compliant_types = (float, int, Decimal)
    else:
        __JSON_compliant_types = (float, int, Decimal, long)  # noqa

    def __init__(self, coordinates=None, crs=None, **extra):
        """
        Initialises a Geometry object.

        :param coordinates: Coordinates of the Geometry object.
        :type coordinates: tuple
        :param crs: CRS
        :type crs: CRS object
        """

        super(Geometry, self).__init__(**extra)
        self["coordinates"] = coordinates or []
        self.clean_coordinates(self["coordinates"])
        if crs:
            self["crs"] = self.to_instance(crs, strict=True)

    @classmethod
    def clean_coordinates(cls, coords):
        for coord in coords:
            if isinstance(coord, (list, tuple)):
                cls.clean_coordinates(coord)
            elif not isinstance(coord, cls.__JSON_compliant_types):
                raise ValueError("%r is not JSON compliant number" % coord)


class GeometryCollection(GeoJSON):
    """
    Represents an abstract base class for collections of WGS84 geometries.
    """

    def __init__(self, geometries=None, **extra):
        super(GeometryCollection, self).__init__(**extra)
        self["geometries"] = geometries or []


# Marker classes.

class Point(Geometry):
    pass


class MultiPoint(Geometry):
    pass


class LineString(MultiPoint):
    pass


class MultiLineString(Geometry):
    pass


class Polygon(Geometry):
    pass


class MultiPolygon(Geometry):
    pass


class Default(object):
    """
    GeoJSON default object.
    """


class Feature(GeoJSON):
    """
    Represents a WGS84 GIS feature.
    """

    def __init__(self, id=None, geometry=None, properties=None, **extra):
        """
        Initialises a Feature object with the given parameters.

        :param id: Feature identifier, such as a sequential number.
        :type id: str, int
        :param geometry: Geometry corresponding to the feature.
        :param properties: Dict containing properties of the feature.
        :type properties: dict
        :return: Feature object
        :rtype: Feature
        """
        super(Feature, self).__init__(**extra)
        if id is not None:
            self["id"] = id
        self["geometry"] = (self.to_instance(geometry, strict=True)
                            if geometry else None)
        self["properties"] = properties or {}


class FeatureCollection(GeoJSON):
    """
    Represents a FeatureCollection, a set of multiple Feature objects.
    """

    def __init__(self, features, **extra):
        """
        Initialises a FeatureCollection object from the
        :param features: List of features to constitute the FeatureCollection.
        :type features: list
        :return: FeatureCollection object
        :rtype: FeatureCollection
        """
        super(FeatureCollection, self).__init__(**extra)
        self["features"] = features


class GeoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        return GeoJSON.to_instance(obj)


# Wrap the functions from json, providing encoder, decoders, and
# object creation hooks.
# Here the defaults are set to only permit valid JSON as per RFC 4267

def _enforce_strict_numbers(obj):
    if isinstance(obj, (int, float)):
        raise ValueError("Number %r is not JSON compliant" % obj)


def dump(obj, fp, cls=GeoJSONEncoder, allow_nan=False, **kwargs):
    return json.dump(to_mapping(obj),
                     fp, cls=cls, allow_nan=allow_nan, **kwargs)


def dumps(obj, cls=GeoJSONEncoder, allow_nan=False, **kwargs):
    return json.dumps(to_mapping(obj),
                      cls=cls, allow_nan=allow_nan, **kwargs)


def load(fp,
         cls=json.JSONDecoder,
         parse_constant=_enforce_strict_numbers,
         object_hook=GeoJSON.to_instance,
         **kwargs):
    return json.load(fp,
                     cls=cls, object_hook=object_hook,
                     parse_constant=parse_constant,
                     **kwargs)


def loads(s,
          cls=json.JSONDecoder,
          parse_constant=_enforce_strict_numbers,
          object_hook=GeoJSON.to_instance,
          **kwargs):
    return json.loads(s,
                      cls=cls, object_hook=object_hook,
                      parse_constant=parse_constant,
                      **kwargs)


# Backwards compatibility
PyGFPEncoder = GeoJSONEncoder


def is_mapping(obj):
    """
    Checks if the object is an instance of MutableMapping.

    :param obj: Object to be checked.
    :return: Truth value of whether the object is an instance of
    MutableMapping.
    :rtype: bool
    """
    return isinstance(obj, MutableMapping)


def to_mapping(obj):
    mapping = getattr(obj, GEO_INTERFACE_MARKER, None)

    if mapping is not None:
        return mapping

    if is_mapping(obj):
        return obj

    if isinstance(obj, GeoJSON):
        return dict(obj)

    return json.loads(json.dumps(obj))


class CoordinateReferenceSystem(GeoJSON):
    """
    Represents a CRS.
    """

    def __init__(self, properties=None, **extra):
        super(CoordinateReferenceSystem, self).__init__(**extra)
        self["properties"] = properties or {}


class Named(CoordinateReferenceSystem):
    """
    Represents a named CRS.
    """

    def __init__(self, properties=None, **extra):
        super(Named, self).__init__(properties=properties, **extra)
        self["type"] = "name"

    def __repr__(self):
        return super(Named, self).__repr__()


class Linked(CoordinateReferenceSystem):
    """
    Represents a linked CRS.
    """

    def __init__(self, properties=None, **extra):
        super(Linked, self).__init__(properties=properties, **extra)
        self["type"] = "link"


class CrsDefault(object):
    """GeoJSON default, long/lat WGS84, is not serialized."""


ALL = ([Point, LineString, Polygon, MultiLineString, MultiPoint, MultiPolygon, GeometryCollection, Feature,
        FeatureCollection, GeoJSON])

name = Named
link = Linked
