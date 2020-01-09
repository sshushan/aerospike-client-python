# -*- coding: utf-8 -*-
import pytest
import time

import aerospike
from aerospike import exception, predicates
from aerospike_helpers.operations import operations
from aerospike import predexp as as_predexp

TEST_NS = 'test'
TEST_SET = 'background_scan1'
TEST_SET2 = 'background_scan2'
TEST_UDF_MODULE = 'bin_lua'
TEST_UDF_FUNCTION = 'mytransformscan'
# Hack to get long to exist in Python 3
try:
    long
except NameError:
    long = int

def wait_for_job_completion(as_connection, job_id):
    '''
    Blocks until the job has completed
    '''
    time.sleep(0.1)
    while True:
        response = as_connection.job_info(job_id, aerospike.JOB_SCAN)
        if response['status'] != aerospike.JOB_STATUS_INPROGRESS:
            break
        time.sleep(0.1)


def add_test_udf(client):
    policy = {}
    client.udf_put(u"bin_lua.lua", 0, policy)


def drop_test_udf(client):
    client.udf_remove("bin_lua.lua")


def validate_records(client, keys, validator):
    for key in keys:
        _, _, rec = client.get(key)
        assert validator(rec)


class TestScanApply(object):

    @pytest.fixture(autouse=True)
    def setup(self, request, connection_with_config_funcs):
        add_test_udf(self.as_connection)
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]
        for i, key in enumerate(keys):
            self.as_connection.put(key, {'number': i})
        keys = [(TEST_NS, TEST_SET2, i) for i in range(10)]
        for i, key in enumerate(keys):
            self.as_connection.put(key, {'number': i})
        
        def teardown():
            drop_test_udf(self.as_connection)
            keys = [(TEST_NS, TEST_SET, i) for i in range(50)]
            for i, key in enumerate(keys):
                self.as_connection.remove(key, {'number': i})
            keys = [(TEST_NS, TEST_SET2, i) for i in range(10)]
            for i, key in enumerate(keys):
                self.as_connection.remove(key, {'number': i})
    
        request.addfinalizer(teardown)

    def test_background_execute_return_val(self):
        """
        Ensure that Scan.execute_background() returns an int like object
        """
        test_bin = 'St1'
        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])
        res = scan.execute_background()
        assert isinstance(res, (int, long))

    def test_background_execute_no_predicate(self):
        """
        Ensure that Scan.execute_background() gets applied to all records
        """
        test_bin = 'number'
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]

        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin, 1])
        job_id = scan.execute_background()
        # Give time for the scan to finish
        wait_for_job_completion(self.as_connection, job_id)

        for i, key in enumerate(keys):
            _, _, bins = self.as_connection.get(key)
            assert bins['number'] == i + 1

    def test_background_execute_predexp_everywhere(self):
        """
        Ensure that Scan.execute_background() gets applied to records that match the predexp
        """
        test_bin = 'number'
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]

        predexp = [
            as_predexp.integer_bin('number'),
            as_predexp.integer_value(2),
            as_predexp.integer_equal(),
            as_predexp.integer_bin('number'),
            as_predexp.integer_value(3),
            as_predexp.integer_equal(),
            as_predexp.predexp_or(2)
        ]

        #number_predicate = predicates.equals('number', 3)

        policy = {
            'predexp': predexp
        }

        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        #scan.where(number_predicate)
        scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin, 1])
        job_id = scan.execute_background(policy)
        # Give time for the scan to finish
        wait_for_job_completion(self.as_connection, job_id)

        for i, key in enumerate(keys):
            _, _, bins = self.as_connection.get(key)
            if i == 2 or i == 3:
                assert(bins[test_bin] == i + 1)
            else:
                assert(bins.get(test_bin) == i)

    @pytest.mark.xfail(reason="scan does not implement .where()")
    def test_background_execute_predexp_and_predicate(self):
        """
        Ensure that Scan.execute_background() gets applied to records that match the predicate
        NOTE: the predicate overrides the predexp
        """
        test_bin = 'Stpredold'
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]

        predexp = [
            as_predexp.integer_bin('number'),
            as_predexp.integer_value(2),
            as_predexp.integer_equal(),
            as_predexp.integer_bin('number'),
            as_predexp.integer_value(3),
            as_predexp.integer_equal(),
            as_predexp.predexp_or(2)
        ]

        number_predicate = predicates.equals('number', 4)

        policy = {
            'predexp': predexp
        }

        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        scan.where(number_predicate)
        scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])
        job_id = scan.execute_background(policy)
        # Give time for the scan to finish
        wait_for_job_completion(self.as_connection, job_id)

        for key in keys:
            _, _, bins = self.as_connection.get(key)
            if bins['number'] == 4:
                assert(bins[test_bin] == 'aerospike')
            else:
                assert(bins.get(test_bin) is None)

    def test_background_execute_with_ops_and_predexp(self):
        """
        Ensure that Scan.execute_background() applies ops to records that match the predexp
        """
        test_bin = 'Stops_preds'
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]

        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        # scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])

        ops = [
            operations.write(test_bin, 'new_val')
        ]

        predexp = [
            as_predexp.integer_bin('number'),
            as_predexp.integer_value(2),
            as_predexp.integer_equal(),
            as_predexp.integer_bin('number'),
            as_predexp.integer_value(3),
            as_predexp.integer_equal(),
            as_predexp.predexp_or(2)
        ]

        policy = {
            'predexp': predexp
        }

        scan.add_ops(ops)
        job_id = scan.execute_background(policy)
        # Give time for the scan to finish
        wait_for_job_completion(self.as_connection, job_id)

        for key in keys:
            _, _, bins = self.as_connection.get(key)
            if bins['number'] == 2 or bins['number'] == 3:
                assert(bins[test_bin] == 'new_val')
            else:
                assert(bins.get(test_bin) is None)

    def test_background_execute_with_ops_and_predexp_None_set(self):
        """
        Ensure that Scan.execute_background() applies ops to all records in the NS that match the predexp
        """
        test_bin = 'Stops_noset'
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]
        keys2 = [(TEST_NS, TEST_SET2, i) for i in range(10)]
        scan = self.as_connection.scan(TEST_NS, None)
        # scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])

        ops = [
            operations.write(test_bin, 'new_val')
        ]

        predexp = [
            as_predexp.integer_bin('number'),
            as_predexp.integer_value(2),
            as_predexp.integer_equal(),
            as_predexp.integer_bin('number'),
            as_predexp.integer_value(3),
            as_predexp.integer_equal(),
            as_predexp.predexp_or(2)
        ]

        policy = {
            'predexp': predexp
        }

        scan.add_ops(ops)
        job_id = scan.execute_background(policy)
        # Give time for the scan to finish
        wait_for_job_completion(self.as_connection, job_id)

        for key in keys:
            _, _, bins = self.as_connection.get(key)
            if bins['number'] == 2 or bins['number'] == 3:
                assert(bins[test_bin] == 'new_val')
            else:
                assert(bins.get(test_bin) is None)
        
        for key in keys2:
            _, _, bins = self.as_connection.get(key)
            if bins['number'] == 2 or bins['number'] == 3:
                assert(bins[test_bin] == 'new_val')
            else:
                assert(bins.get(test_bin) is None)

    def test_background_execute_with_ops(self):
        """
        Ensure that Scan.execute_background() applies ops to all records
        """
        test_bin = 'Stops'
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]

        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        # scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])

        ops = [
            operations.write(test_bin, 'new_val')
        ]

        scan.add_ops(ops)
        job_id = scan.execute_background()
        # Give time for the scan to finish
        wait_for_job_completion(self.as_connection, job_id)

        validate_records(
            self.as_connection, keys,
            lambda rec: rec[test_bin] == 'new_val'
        )

    @pytest.mark.xfail(reason="Scan does not implement .where()")
    def test_background_execute_with_ops_and_preds(self):
        """
        Ensure that Scan.execute_background() applies ops to records that match the predicate
        """
        test_bin = 'St1'
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]

        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        number_predicate = predicates.equals('number', 3)
        # scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])

        ops = [
            operations.append(test_bin, 'new_val')
        ]

        scan.add_ops(ops)
        scan.where(number_predicate)
        job_id = scan.execute_background()
        # Give time for the scan to finish
        wait_for_job_completion(self.as_connection, job_id)

        _, _, num_5_record = self.as_connection.get((TEST_NS, TEST_SET, 5))
        assert num_5_record[test_bin] == 'aerospike'

        _, _, num_3_record = self.as_connection.get((TEST_NS, TEST_SET, 3))
        assert num_3_record[test_bin] == 'aerospikenew_val'

        # cleanup
        ops = [
            operations.write(test_bin, 'aerospike')
        ]

        scan.add_ops(ops)
        job_id = scan.execute_background()
        wait_for_job_completion(self.as_connection, job_id)

        validate_records(
            self.as_connection, keys,
            lambda rec: rec[test_bin] == 'aerospike'
        )

    @pytest.mark.xfail(reason="Scan does not implement .where()")
    def test_background_execute_sindex_predicate(self):
        """
        Ensure that Scan.execute_background() only applies to records matched by
        the specified predicate
        """
        test_bin = 'St3'
        keys = [(TEST_NS, TEST_SET, i) for i in range(50)]
        number_predicate = predicates.equals('number', 5)

        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        scan.where(number_predicate)
        scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])
        job_id = scan.execute_background()
        # Give time for the scan to finish
        wait_for_job_completion(self.as_connection, job_id)

        keys = [(TEST_NS, TEST_SET, i) for i in range(50) if i != 5]
        validate_records(
            self.as_connection, keys,
            lambda rec: test_bin not in rec
        )
        _, _, num_5_record = self.as_connection.get((TEST_NS, TEST_SET, 5))
        assert num_5_record[test_bin] == 'aerospike'

    def test_background_execute_with_policy(self):
        """
        Ensure that Scan.execute_background() returns an int like object
        """
        test_bin = 'St5'
        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])
        res = scan.execute_background({'socket_timeout': 10000})
        assert isinstance(res, (int, long))

    def test_background_execute_with_policy_kwarg(self):
        """
        Ensure that Scan.execute_background() returns an int like object
        """
        test_bin = 'St6'
        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])
        res = scan.execute_background(policy={})
        assert isinstance(res, (int, long))

    def test_background_execute_with_invalid_policy_type(self):
        """
        Ensure that Scan.execute_background() returns an int like object
        """
        test_bin = 'St6'
        scan = self.as_connection.scan(TEST_NS, TEST_SET)
        scan.apply(TEST_UDF_MODULE, TEST_UDF_FUNCTION, [test_bin])
        # Policy needs to be a dict. Not a string
        with pytest.raises(exception.ParamError):
            res = scan.execute_background("Honesty is the best Policy")
