import json
from django.db import models
from django.forms import model_to_dict
import six


class DefaultContextSerializer(object):
    """
    Default class for serializing context data
    """

    def __init__(self, context):
        super(DefaultContextSerializer, self).__init__()
        self.context = context

    @property
    def data(self):
        """
        Data property that will return the serialized data
        :return:
        """

        # Create a serialized context dict
        serialized_context = self.serialize_value(self.context)

        # Return the serialized context
        return serialized_context

    def serialize_value(self, value):
        """
        Given a value, ensure that it is serialized properly
        :param value:
        :return:
        """
        # Create a list of serialize methods to run the value through
        serialize_methods = [
            self.serialize_model,
            self.serialize_json_string,
            self.serialize_list,
            self.serialize_dict
        ]

        # Run all of our serialize methods over our value
        for serialize_method in serialize_methods:
            value = serialize_method(value)

        # Return the serialized context value
        return value

    def serialize_model(self, value):
        """
        Serializes a model and all of its prefetched foreign keys
        :param value:
        :return:
        """

        # Check if the context value is a model
        if not isinstance(value, models.Model):
            return value

        # Serialize the model
        serialized_model = model_to_dict(value)

        # Check the model for cached foreign keys
        for model_field, model_value in serialized_model.items():
            cache_field = '_{0}_cache'.format(model_field)
            if hasattr(value, cache_field):
                serialized_model[model_field] = getattr(value, cache_field)

        # Return the serialized model
        return self.serialize_value(serialized_model)

    def serialize_json_string(self, value):
        """
        Tries to load an encoded json string back into an object
        :param json_string:
        :return:
        """

        # Check if the value might be a json string
        if not isinstance(value, six.string_types):
            return value

        # Make sure it starts with a brace
        if not value.startswith('{') or value.startswith('['):
            return value

        # Try to load the string
        try:
            return json.loads(value)
        except:
            return value

    def serialize_list(self, value):
        """
        Ensure that all values of a list or tuple are serialized
        :return:
        """

        # Check if this is a list or a tuple
        if not isinstance(value, (list, tuple)):
            return value

        # Loop over all the values and serialize the values
        return [
            self.serialize_value(list_value)
            for list_value in value
        ]

    def serialize_dict(self, value):
        """
        Ensure that all values of a dictionary are properly serialized
        :param value:
        :return:
        """

        # Check if this is a dict
        if not isinstance(value, dict):
            return value

        # Loop over all the values and serialize them
        return {
            dict_key: self.serialize_value(dict_value)
            for dict_key, dict_value in value.items()
        }
