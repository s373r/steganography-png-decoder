# steganography-png-decoder
Python script for getting encoded text from PNG pictures

# Prepare

```
$ git clone https://github.com/s373r/steganography-png-decoder.git
$ cd steganography-png-decoder
$ chmod +x steganography-png-decoder.py
```

# Bacis usage

```
$ ./steganography-png-decoder.py -h
```

```
usage: steganography-png-decoder.py [-h] file

Prints PNG text sections

positional arguments:
  file        an PNG image

optional arguments:
  -h, --help  show this help message and exit
```
---
```
$ ./steganography-png-decoder.py samples/tEXT-chunks.png
```
```
[00000049-00000074] tEXt:
Title PngSuite

[00000075-00000135] tEXt:
Author Willem A.J. van Schaik
(willem@schaik.com)

[00000136-00000203] tEXt:
Copyright Copyright Willem van Schaik, Singapore 1995-96

[00000204-00000466] tEXt:
Description A compilation of a set of images created to test the
various color-types of the PNG format. Included are
black&white, color, paletted, with alpha channel, with
transparency formats. All bit-depths allowed according
to the spec are present.

[00000467-00000535] tEXt:
Software Created on a NeXTstation color using "pnmtopng".

[00000536-00000567] tEXt:
Disclaimer Freeware.
```
