import pytest
from classes.target import *

def test_ip():
    server_target = Target('10.241.57.198', 'v2', 'admin', 'Microsemi**2')
    url = "/system/state"
    data = server_target.get(url)
    currRef = server_target.reference_IDs.get(int(data.get('powerSupply1')))
    assert currRef == 2
