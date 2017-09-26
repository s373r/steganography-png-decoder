#!/usr/bin/env python3

# +---------+------------+--------------+---------+
# | Length  | Chunk type |  Chunk data  |   CRC   |
# +---------+------------+--------------+---------+
# | 4 bytes | 4 bytes    | Length bytes | 4 bytes |
# +---------+------------+--------------+---------+
#
# Critical chunks:
#
# IHDR - must be the first chunk; it contains (in this order) the image's width,
#        height, bit depth, color type, compression method, filter method, and
#        interlace method (13 data bytes total).
#
# PLTE - contains the palette; list of colors.
#
# IDAT - contains the image, which may be split among multiple IDAT chunks.
#        Such splitting increases filesize slightly, but makes it possible to
#        generate a PNG in a streaming manner. The IDAT chunk contains the
#        actual image data, which is the output stream of the compression
#        algorithm.
#
# IEND - marks the image end.
#
# Ancillary chunks:
#
# bKGD - gives the default background color. It is intended for use when there
#        is no better choice available, such as in standalone image viewers (but
#        not web browsers; see below for more details).
#
# cHRM - gives the chromaticity coordinates of the display primaries and white
#        point.
#
# dSIG - is for storing digital signatures.
#
# eXIf - stores Exif data.
#
# gAMA - specifies gamma.
#
# hIST - can store the histogram, or total amount of each color in the image.
#
# iCCP - is an ICC color profile.
#
# iTXt - contains a keyword and UTF-8 text, with encodings for possible
#        compression and translations marked with language tag. The Extensible
#        Metadata Platform (XMP) uses this chunk with a keyword
#        'XML:com.adobe.xmp'
#
# pHYs - holds the intended pixel size and/or aspect ratio of the image.
#
# sBIT - (significant bits) indicates the color-accuracy of the source data.
#
# sPLT - suggests a palette to use if the full range of colors is unavailable.
#
# sRGB - indicates that the standard sRGB color space is used.
#
# sTER - stereo-image indicator chunk for stereoscopic images.[15]
#
# tEXt - can store text that can be represented in ISO/IEC 8859-1, with one
#        key-value pair for each chunk. The "key" must be between 1 and 79
#        characters long. Separator is a null character. The "value" can be any
#        length, including zero up to the maximum permissible chunk size minus
#        the length of the keyword and separator. Neither "key" nor "value" can
#        contain null character. Leading or trailing spaces are also disallowed.
#
# tIME - stores the time that the image was last changed.
#
# tRNS - contains transparency information. For indexed images, it stores alpha
#        channel values for one or more palette entries. For truecolor and
#        grayscale images, it stores a single pixel value that is to be regarded
#        as fully transparent.
#
# zTXt - contains compressed text (and a compression method marker) with the
#        same limits as tEXt.
#
# (c) https://en.wikipedia.org/wiki/Portable_Network_Graphics#File_header

from enum import Enum
from mmap import ACCESS_READ, mmap

import argparse
import collections
import os
import struct
import sys

PNG_MAGIC_NUMBER = b'\x89PNG\r\n\x1a\n'
PNG_MAGIC_NUMBER_LENGTH = len(PNG_MAGIC_NUMBER)


class ChunkField(Enum):
    DATA_LENGTH = 4
    TYPE = 4
    CRC = 4

    def length(self):
        return self.value


# todo migrate to python 3.6 for using automatic values - auto()
class ChunkTypes(Enum):
    IHDR = 1
    PLTE = 2
    IDAT = 3
    IEND = 4
    bKGD = 5
    cHRM = 6
    dSIG = 7
    eXIf = 8
    gAMA = 9
    hIST = 10
    iCCP = 11
    iTXt = 12
    pHYs = 13
    sBIT = 14
    sPLT = 15
    sRGB = 16
    sTER = 17
    tEXt = 18
    tIME = 19
    tRNS = 20
    zTXt = 21

    def __str__(self):
        return self.name

    @staticmethod
    def contains(chunk_type_str):
        all_chunk_types = [name for name, _ in ChunkTypes.__members__.items()]
        return chunk_type_str in all_chunk_types

    @staticmethod
    def from_binary(data):
        if len(data) != ChunkField.TYPE.length():
            raise Exception('Incorrect a chunk type size {}!'.format(len(data)))

        chunk_type = data.decode('ascii')
        found_enums = [enum for name, enum in ChunkTypes.__members__.items()
                       if name == chunk_type]

        if len(found_enums) == 0:
            raise Exception('Unknown "{}" chunk type!'.format(chunk_type))

        return found_enums[0]

    @staticmethod
    def is_text_chunk(chunk_type):
        return chunk_type in [ChunkTypes.iTXt, ChunkTypes.tEXt, ChunkTypes.zTXt]


class Chunk:
    def __init__(self, type, data, crc, start_position):
        self._type = ChunkTypes.from_binary(type)
        self._data = data
        if ChunkTypes.is_text_chunk(self._type):
            self._data = self._data.replace(b'\x00', b' ').decode('utf-8')
        # todo check CRC
        self._crc = crc
        self._start_position = start_position

    @property
    def type(self):
        return self._type

    @property
    def crc(self):
        return self._crc

    @property
    def data(self):
        return self._data

    @property
    def length(self):
        return ChunkField.DATA_LENGTH.length() \
               + ChunkField.TYPE.length() \
               + len(self.data) \
               + ChunkField.CRC.length() \
               - 1

    @property
    def start_position(self):
        return self._start_position

    @property
    def end_position(self):
        return self.start_position + self.length


class ChunkIterator(collections.Iterator):
    def __init__(self, file):
        self._stop = False
        self._file = file

    def __iter__(self):
        return self

    def __next__(self):
        if self._stop:
            raise StopIteration

        start_position = self._file.tell()

        length = struct.unpack('>i', self._read_data_length())[0]
        type = self._read_type()
        data = self._read_data(length)
        crc = self._read_crc()

        current_chunk = Chunk(type, data, crc, start_position)

        if current_chunk.type is ChunkTypes.IEND:
            self._stop = True

        return current_chunk

    def _read_data_length(self):
        return self._file.read(ChunkField.DATA_LENGTH.length())

    def _read_type(self):
        return self._file.read(ChunkField.TYPE.length())

    def _read_data(self, chunk_length):
        return self._file.read(chunk_length)

    def _read_crc(self):
        return self._file.read(ChunkField.CRC.length())


def print_error_and_exit(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    exit(1)


parser = argparse.ArgumentParser(description='Prints PNG text sections')
parser.add_argument('file', help='an PNG image')

filename = parser.parse_args().file

if not os.path.isfile(filename):
    print_error_and_exit('"{}" file not found!'.format(filename))

with open(filename, 'br') as f:
    # check file header
    if f.read(PNG_MAGIC_NUMBER_LENGTH) != PNG_MAGIC_NUMBER:
        print_error_and_exit('"{}" file is not an PNG image!'.format(filename))

    # load the picture to memory
    mm = mmap(f.fileno(), 0, access=ACCESS_READ)

    # skip file header
    mm.seek(PNG_MAGIC_NUMBER_LENGTH, os.SEEK_SET)

    for chunk in ChunkIterator(mm):
        if ChunkTypes.is_text_chunk(chunk.type):
            print('[{:08d}-{:08d}] {}:\n{}\n'.format(chunk.start_position,
                                                     chunk.end_position,
                                                     chunk.type,
                                                     chunk.data))
