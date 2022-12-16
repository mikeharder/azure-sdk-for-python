# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os
import traceback

_DEFAULT_LENGTH = 1024 * 1024
_BYTE_BUFFER = [_DEFAULT_LENGTH, os.urandom(_DEFAULT_LENGTH)]


def get_random_bytes(buffer_length):
    if buffer_length > _BYTE_BUFFER[0]:
        _BYTE_BUFFER[1] = os.urandom(buffer_length)
        _BYTE_BUFFER[0] = buffer_length
    return _BYTE_BUFFER[1][:buffer_length]


_RANDOM_BYTES = os.urandom(1024 * 1024)

class RandomStream:
    def __init__(self, length):
        self._length = length
        self._position = 0
        self._buffer = _RANDOM_BYTES
        self._buffer_length = len(self._buffer)
        self._buffer_position = 0

    def reset(self):
        self._position = 0
        self._buffer_position = 0

    def read(self, size=None):
        traceback.print_stack()

        print("size: " + str(size))

        bytes_available = self._length - self._position
        buffer_bytes_available = self._buffer_length - self._buffer_position

        if size is None:
            size = bytes_available

        bytes_to_read = min(size, bytes_available, buffer_bytes_available)
        print("bytes_to_read: " + str(bytes_to_read))

        data = self._buffer[self._buffer_position:self._buffer_position + bytes_to_read]
        print("len(data): " + str(len(data)))

        self._buffer_position = self._buffer_position + bytes_to_read
        if self._buffer_position == self._buffer_length:
            self._buffer_position = 0
        print("self._buffer_position: " + str(self._buffer_position))

        self._position = self._position + bytes_to_read
        print("self._position: " + str(self._position))

        return data

    def tell(self):
        return self._position

    def seek(self, index, whence=0):
        if whence == 0:
            self._position = index
        elif whence == 1:
            self._position = self._position + index
        elif whence == 2:
            self._position = self._length - 1 + index

    def remaining(self):
        return self._length - self._position


class WriteStream:
    def __init__(self):
        self._position = 0

    def reset(self):
        self._position = 0

    def write(self, content):
        length = len(content)
        self._position += length
        return length

    def seek(self, index):
        self._position = index

    def seekable(self):
        return True

    def tell(self):
        return self._position
