# from target import *
from target import *
from image import *
from ssh import *
import pytest
import logging
import os

__author__ = 'Andy Nguyen'


def pytest_addoption(parser):
    parser.addoption("--server", action="store", default="10.241.54.221", help="server")
    parser.addoption("--server_pass", action="store", default="Microsemi**2")
    parser.addoption("--client", action="store", default="10.241.54.222")
    parser.addoption("--client_pass", action="store", default="Microsemi")


@pytest.fixture
def client_target(request):
    new_target = Target(request.config.getoption('--client'),
                        'v2', 'admin', request.config.getoption('--client_pass'))
    return new_target


@pytest.fixture
def server_target(request):
    new_target = Target(request.config.getoption('--server'),
                        'v2', 'admin', request.config.getoption('--server_pass'))
    return new_target


@pytest.fixture
def ssh_target(request):
    ssh = SSH(request.config.getoption('--client'), 'admin', request.config.getoption('--client_pass'),
              'K22Sxxx!.', 'SyncServer>')
    return ssh


@pytest.fixture
def image_target(request):
    new_image = Image('10.241.54.234', '/ws/releases/releases/K2/Nightly/',
                      '10.241.68.44', 'builder', 'myk2build!!.', 'builder@vm', 'K2')
    return new_image


@pytest.fixture
def logger_target(request):
    logger = logging.getLogger(__name__)
    return logger


def pytest_html_report_title(report):
    report.title = 'Sanity Test Report'
