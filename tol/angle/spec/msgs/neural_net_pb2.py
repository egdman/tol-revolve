# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: msgs/neural_net.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import msgs.parameter_pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='msgs/neural_net.proto',
  package='msgs',
  serialized_pb=_b('\n\x15msgs/neural_net.proto\x12\x04msgs\x1a\x14msgs/parameter.proto\"L\n\x10NeuralConnection\x12\x0b\n\x03src\x18\x01 \x02(\t\x12\x0b\n\x03\x64st\x18\x02 \x02(\t\x12\x0e\n\x06weight\x18\x03 \x02(\x01\x12\x0e\n\x06socket\x18\x04 \x01(\t\"a\n\x06Neuron\x12\n\n\x02id\x18\x01 \x02(\t\x12\r\n\x05layer\x18\x02 \x02(\t\x12\x0c\n\x04type\x18\x03 \x02(\t\x12\x0e\n\x06partId\x18\x04 \x01(\t\x12\x1e\n\x05param\x18\x05 \x03(\x0b\x32\x0f.msgs.Parameter\"Y\n\rNeuralNetwork\x12\x1c\n\x06neuron\x18\x01 \x03(\x0b\x32\x0c.msgs.Neuron\x12*\n\nconnection\x18\x02 \x03(\x0b\x32\x16.msgs.NeuralConnection\"K\n\x11SendNeuralNetwork\x12\n\n\x02id\x18\x01 \x02(\x05\x12*\n\rneuralNetwork\x18\x02 \x02(\x0b\x32\x13.msgs.NeuralNetwork')
  ,
  dependencies=[msgs.parameter_pb2.DESCRIPTOR,])
_sym_db.RegisterFileDescriptor(DESCRIPTOR)




_NEURALCONNECTION = _descriptor.Descriptor(
  name='NeuralConnection',
  full_name='msgs.NeuralConnection',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='src', full_name='msgs.NeuralConnection.src', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='dst', full_name='msgs.NeuralConnection.dst', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='weight', full_name='msgs.NeuralConnection.weight', index=2,
      number=3, type=1, cpp_type=5, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='socket', full_name='msgs.NeuralConnection.socket', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=53,
  serialized_end=129,
)


_NEURON = _descriptor.Descriptor(
  name='Neuron',
  full_name='msgs.Neuron',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='msgs.Neuron.id', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='layer', full_name='msgs.Neuron.layer', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='type', full_name='msgs.Neuron.type', index=2,
      number=3, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='partId', full_name='msgs.Neuron.partId', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='param', full_name='msgs.Neuron.param', index=4,
      number=5, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=131,
  serialized_end=228,
)


_NEURALNETWORK = _descriptor.Descriptor(
  name='NeuralNetwork',
  full_name='msgs.NeuralNetwork',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='neuron', full_name='msgs.NeuralNetwork.neuron', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='connection', full_name='msgs.NeuralNetwork.connection', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=230,
  serialized_end=319,
)


_SENDNEURALNETWORK = _descriptor.Descriptor(
  name='SendNeuralNetwork',
  full_name='msgs.SendNeuralNetwork',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='msgs.SendNeuralNetwork.id', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='neuralNetwork', full_name='msgs.SendNeuralNetwork.neuralNetwork', index=1,
      number=2, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=321,
  serialized_end=396,
)

_NEURON.fields_by_name['param'].message_type = msgs.parameter_pb2._PARAMETER
_NEURALNETWORK.fields_by_name['neuron'].message_type = _NEURON
_NEURALNETWORK.fields_by_name['connection'].message_type = _NEURALCONNECTION
_SENDNEURALNETWORK.fields_by_name['neuralNetwork'].message_type = _NEURALNETWORK
DESCRIPTOR.message_types_by_name['NeuralConnection'] = _NEURALCONNECTION
DESCRIPTOR.message_types_by_name['Neuron'] = _NEURON
DESCRIPTOR.message_types_by_name['NeuralNetwork'] = _NEURALNETWORK
DESCRIPTOR.message_types_by_name['SendNeuralNetwork'] = _SENDNEURALNETWORK

NeuralConnection = _reflection.GeneratedProtocolMessageType('NeuralConnection', (_message.Message,), dict(
  DESCRIPTOR = _NEURALCONNECTION,
  __module__ = 'msgs.neural_net_pb2'
  # @@protoc_insertion_point(class_scope:msgs.NeuralConnection)
  ))
_sym_db.RegisterMessage(NeuralConnection)

Neuron = _reflection.GeneratedProtocolMessageType('Neuron', (_message.Message,), dict(
  DESCRIPTOR = _NEURON,
  __module__ = 'msgs.neural_net_pb2'
  # @@protoc_insertion_point(class_scope:msgs.Neuron)
  ))
_sym_db.RegisterMessage(Neuron)

NeuralNetwork = _reflection.GeneratedProtocolMessageType('NeuralNetwork', (_message.Message,), dict(
  DESCRIPTOR = _NEURALNETWORK,
  __module__ = 'msgs.neural_net_pb2'
  # @@protoc_insertion_point(class_scope:msgs.NeuralNetwork)
  ))
_sym_db.RegisterMessage(NeuralNetwork)

SendNeuralNetwork = _reflection.GeneratedProtocolMessageType('SendNeuralNetwork', (_message.Message,), dict(
  DESCRIPTOR = _SENDNEURALNETWORK,
  __module__ = 'msgs.neural_net_pb2'
  # @@protoc_insertion_point(class_scope:msgs.SendNeuralNetwork)
  ))
_sym_db.RegisterMessage(SendNeuralNetwork)


# @@protoc_insertion_point(module_scope)
