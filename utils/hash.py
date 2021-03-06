"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import os
import hashlib
from core import db

q = db.query
logg = logging.getLogger(__name__)


def calcChecksum(filename, method):
    if os.path.exists(filename):
        f = open(filename)
        if method == "SHA-1":
            h = hashlib.sha1()
        else:
            h = hashlib.new('ripemd160')
        h.update(f.read())
        f.close()
        return h.hexdigest()
    else:
        return ""


def calcChecksumFromMetadata(node):
    h = hashlib.sha1()
    h.update(str(node.id))  # h.update requires string or buffer as argument
    h.update(node.getName())

    def attributesToString(node):
        string = ""
        for item in node.attrs.items():
            string += item[0] + item[1]
        return string

    h.update(attributesToString(node))

    return h.hexdigest()
