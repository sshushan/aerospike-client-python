# -*- coding: utf-8 -*-

import pytest
import sys
import cPickle as pickle
import time
from test_base_class import TestBaseClass

try:
    import aerospike
    from aerospike.exception import *
except:
    print "Please install aerospike python client."
    sys.exit(1)

class TestInfo(object):

    def setup_class(cls):

        """
        Setup class.
        """
        TestInfo.hostlist, user, password = TestBaseClass.get_hosts()
        config = {
                'hosts': TestInfo.hostlist
                }
        if user == None and password == None:
            TestInfo.client = aerospike.client(config).connect()
        else:
            TestInfo.client = aerospike.client(config).connect(user, password)

    def teardown_class(cls):

        """
        Teardoen class.
        """

        TestInfo.client.close()

    def test_info_for_statistics(self):

        request = "statistics"

        nodes_info = TestInfo.client.info(request, TestInfo.hostlist)

        assert nodes_info != None

        assert type(nodes_info) == dict

    def test_info_positive_for_namespace(self):
        """
        Test info positive for namespace
        """
        key = ('test', 'demo', 'list_key')

        rec = {
                'names': ['John', 'Marlen', 'Steve']
            }

        TestInfo.client.put(key, rec)
        response = TestInfo.client.info('namespaces', TestInfo.hostlist)
        TestInfo.client.remove(key)
        flag = 0
        for keys in response.keys():
            for value in response[keys]:
                if value != None:
                    if 'test' in value:
                        flag = 1
        if flag:
            assert True == True
        else:
            assert True == False

    def test_info_positive_for_sets(self):
        """
        Test info positive for sets
        """
        key = ('test', 'demo', 'list_key')

        rec = {
                'names': ['John', 'Marlen', 'Steve']
            }

        TestInfo.client.put(key, rec)
        response = TestInfo.client.info('sets', TestInfo.hostlist)
        TestInfo.client.remove(key)
        flag = 0
        for keys in response.keys():
            for value in response[keys]:
                if value != None:
                    if 'demo' in value:
                        flag = 1
        if flag:
            assert True == True
        else:
            assert True == False

    def test_info_positive_for_bins(self):
        """
        Test info positive for bins
        """
        key = ('test', 'demo', 'list_key')

        rec = {
                'names': ['John', 'Marlen', 'Steve']
            }

        TestInfo.client.put(key, rec)
        response = TestInfo.client.info('bins', TestInfo.hostlist)
        TestInfo.client.remove(key)
        flag = 0
        for keys in response.keys():
            for value in response[keys]:
                if value != None:
                    if 'names' in value:
                        flag = 1
        if flag:
            assert True == True
        else:
            assert True == False

    def test_info_positive_for_sindex_creation(self):
        """
        Test info for secondary index creation
        """
        key = ('test', 'demo', 'list_key')

        rec = {
                'names': ['John', 'Marlen', 'Steve']
            }
        policy = {}
        TestInfo.client.put(key, rec)
        response = TestInfo.client.info('sindex-create:ns=test;set=demo;indexname=names_test_index;indexdata=names,string', TestInfo.hostlist)
        time.sleep(2)
        TestInfo.client.remove(key)
        response = TestInfo.client.info('sindex', TestInfo.hostlist)
        TestInfo.client.info('sindex-delete:ns=test;indexname=names_test_index', TestInfo.hostlist)

        flag = 0
        for keys in response.keys():
            for value in response[keys]:
                if value != None:
                    if 'demo' in value:
                        flag = 1
        if flag:
            assert True == True
        else:
            assert True == False

    def test_info_with_config_for_statistics(self):

        request = u"statistics"

        config = [(127, 3000)]

        try:
            TestInfo.client.info(request, config)

        except ParamError as exception:
            assert exception.code == -2
            assert exception.msg == "Host address is of type incorrect"

    def test_info_with_config_for_statistics_and_policy(self):

        request = "statistics"

        config = [('172.20.25.193', 3000)]

        policy = {
                'timeout': 1000
        }
        nodes_info = TestInfo.client.info(request, config, policy)

        assert nodes_info != None

        assert type(nodes_info) == dict

    def test_info_for_invalid_request(self):

        request = "no_info"

        nodes_info = TestInfo.client.info(request, TestInfo.hostlist)

        assert type(nodes_info) == dict

        assert nodes_info.values() != None

    def test_info_with_none_request(self):

        request = None

        try:
            TestInfo.client.info(request, TestInfo.hostlist)

        except ParamError as exception:
            assert exception.code == -2L
            assert exception.msg == "Request must be a string"

    def test_info_without_parameters(self):

        with pytest.raises(TypeError) as typeError:
            nodes_info = TestInfo.client.info()

        assert "Required argument 'command' (pos 1) not found" in typeError.value

    def test_info_positive_for_sets_without_connection(self):
        """
        Test info positive for sets without connection
        """
        config = {
                'hosts': [('172.20.25.193', 3000)]
                }
        
        client1 = aerospike.client(config)
        try:
            response = client1.info('sets', TestInfo.hostlist)

        except ClusterError as exception:
            assert exception.code == 11L
            assert exception.msg == 'No connection to aerospike cluster'
