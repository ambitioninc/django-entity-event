import json
from django.test.testcases import TransactionTestCase
from django_dynamic_fixture import G
from mock import patch, call
from entity_event.context_serializer import DefaultContextSerializer


class DefaultContextSerializerTests(TransactionTestCase):
    def setUp(self):
        super(DefaultContextSerializerTests, self).setUp()

        # Create some fake context to work with
        self.context = dict(
            test='test'
        )

        # Create a serializer to test with
        self.serializer = DefaultContextSerializer(self.context)

    @patch.object(DefaultContextSerializer, 'serialize_value', autospec=True)
    def test_data_property(self, mock_serialize_value):
        # Call the property
        response = self.serializer.data

        # Assert that we have a proper response
        self.assertEqual(response, mock_serialize_value.return_value)

    @patch.object(DefaultContextSerializer, 'serialize_model', autospec=True)
    @patch.object(DefaultContextSerializer, 'serialize_json_string', autospec=True)
    @patch.object(DefaultContextSerializer, 'serialize_list', autospec=True)
    @patch.object(DefaultContextSerializer, 'serialize_dict', autospec=True)
    def test_serialize_value(self, *serialize_methods):
        # Setup the return values of each method
        for serialize_method in serialize_methods:
            serialize_method.return_value = self.context

        # Call the method
        response = self.serializer.serialize_value(self.context)

        # Assert we have a proper response
        self.assertEqual(response, serialize_methods[0].return_value)

        # Assert that each serialize method was called properly
        for serialize_method in serialize_methods:
            serialize_method.assert_called_once_with(self.serializer, self.context)

    def test_serialize_model_non_model(self):
        # Call the method
        response = self.serializer.serialize_model('test')

        # Assert we have a proper response
        self.assertEqual(response, 'test')

    def test_serialize_model(self):
        from entity_event.tests.models import TestModel

        # Create a model to test with
        model = G(TestModel)

        # Fetch the model so we dont have the fks loaded and only select one related
        model = TestModel.objects.select_related('fk').get(id=model.id)

        # Call the method
        response = self.serializer.serialize_model(model)

        # Assert that we have a proper response
        self.assertEqual(
            response,
            {
                'fk_m2m': [],
                'fk2': model.fk2.id,
                'fk': {
                    'id': model.fk.id,
                    'value': model.fk.value
                },
                'id': model.id,
                'value': model.value
            }
        )

    def test_serialize_json_string_non_string(self):
        # Call the method
        response = self.serializer.serialize_json_string(dict())

        # Assert we have a proper response
        self.assertEqual(response, dict())

    def test_serialize_json_string_non_json_string(self):
        # Call the method
        response = self.serializer.serialize_json_string('test')

        # Assert we have a proper response
        self.assertEqual(response, 'test')

    def test_serialize_json_string_bad_json_string(self):
        # Call the method
        response = self.serializer.serialize_json_string('{test')

        # Assert we have a proper response
        self.assertEqual(response, '{test')

    def test_serialize_json_string(self):
        # Create a json string to test
        test_dict = dict(test='test')
        test_json = json.dumps(test_dict)

        # Call the method
        response = self.serializer.serialize_json_string(test_json)

        # Assert that we have a proper response
        self.assertEqual(
            response,
            test_dict
        )

    def test_serialize_list_non_list(self):
        # Call the method
        response = self.serializer.serialize_list('test')

        # Assert we have a proper response
        self.assertEqual(response, 'test')

    @patch.object(DefaultContextSerializer, 'serialize_value', autospec=True)
    def test_serialize_list_list(self, mock_serialize_value):
        # Setup a test list
        test_list = ['one', 'two', 'three']

        # Call the method
        response = self.serializer.serialize_list(test_list)

        # Assert that we have the proper response
        self.assertEqual(
            response,
            [
                mock_serialize_value.return_value,
                mock_serialize_value.return_value,
                mock_serialize_value.return_value,
            ]
        )

        # Assert that we called serialize value on on values of the list
        self.assertEqual(
            mock_serialize_value.mock_calls,
            [
                call(self.serializer, 'one'),
                call(self.serializer, 'two'),
                call(self.serializer, 'three'),
            ]
        )

    @patch.object(DefaultContextSerializer, 'serialize_value', autospec=True)
    def test_serialize_list_tuple(self, mock_serialize_value):
        # Setup a test tuple
        test_tuple = ('one', 'two', 'three')

        # Call the method
        response = self.serializer.serialize_list(test_tuple)

        # Assert that we have the proper response
        self.assertEqual(
            response,
            [
                mock_serialize_value.return_value,
                mock_serialize_value.return_value,
                mock_serialize_value.return_value,
            ]
        )

        # Assert that we called serialize value on on values of the list
        self.assertEqual(
            mock_serialize_value.mock_calls,
            [
                call(self.serializer, 'one'),
                call(self.serializer, 'two'),
                call(self.serializer, 'three'),
            ]
        )

    def test_serialize_dict_non_dict(self):
        # Call the method
        response = self.serializer.serialize_dict('test')

        # Assert we have a proper response
        self.assertEqual(response, 'test')

    @patch.object(DefaultContextSerializer, 'serialize_value', autospec=True)
    def test_serialize_dict(self, mock_serialize_value):
        # Setup a test dict
        test_dict = dict(one='one', two='two')

        # Call the method
        response = self.serializer.serialize_dict(test_dict)

        # Assert we have a proper response
        self.assertEqual(
            response,
            dict(
                one=mock_serialize_value.return_value,
                two=mock_serialize_value.return_value,
            )
        )

        # Assert that we called serialize value on on values of the dict
        mock_serialize_value.assert_has_calls([
            call(self.serializer, 'one'),
            call(self.serializer, 'two'),
        ], any_order=True)
