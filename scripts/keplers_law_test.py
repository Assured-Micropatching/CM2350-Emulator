#!/usr/bin/env python3

import time
import queue
import struct
import argparse
import threading

from cm2350.ppc_peripherals import ExternalIOClient
from cm2350.peripherals.flexcan import CanMsg


TEST_ARBID = 0x15FF14F1
RESP_MASK  = 0x01FFFF00
RESP_ARBID = 0x01FF1500


def print_msg(msg, client_name=None):
    if client_name is None:
        client_name = ''

    # Print the message in socketcan-type format
    #   can0  0CF00400   [8]  0E 7D 7D 00 00 00 00 7D
    #   can0  18F00F00   [8]  FF FF FF FF C0 9F FF FF
    #   can0  18FEDF00   [8]  7D A0 28 7D 7D FF FF F0
    #   can0  0CF00A00   [8]  00 00 00 00 FF FF FF FF
    #   can0  0CF00300   [8]  CA FE 00 FF FF 0F 63 7D
    ts = time.strftime('%H:%M:%S')
    print('%s %-12s %08x  [%d]  %s' % (ts, client_name, msg.arbid, msg.length, msg.data.hex(' ', 1)))



#def run_test(client, client_name, msgq, arbid, data, resp_mask, resp_arbid, resp_len):
def run_test(client, client_name, msgq, arbid, data):
    msg = CanMsg(rtr=0, ide=1, arbid=arbid, length=len(data), data=data)

    # Before sending clear out the list received msgs
    try:
        while True:
            msgq.get_nowait()
    except queue.Empty:
        pass

    print_msg(msg, '%s ->' % client_name)
    client.send(msg)

    #time.sleep(240)

    #try:
    #    while True:
    #        name, resp = msgq.get_nowait()
    #        if name == client_name and resp.arbid & mask == resp_arbid and \
    #                resp.length == resp_len:
    #            return resp
    #except queue.Empty:
    #    pass
    #return None


def test_lower_input_boundary(client, client_name, msgq):
    msg = CanMsg(rtr=0, ide=1, arbid=TEST_ARBID, length=8, data=b'\x00'*8)
    print_msg(msg, '%s ->' % client_name)
    client.send(msg)


def test_upper_input_boundary(client, client_name, msgq):
    msg = CanMsg(rtr=0, ide=1, arbid=TEST_ARBID, length=8, data=b'\xFF'*8)
    print_msg(msg, '%s ->' % client_name)
    client.send(msg)


def test(client, client_name, msgq):
    msg = CanMsg(rtr=0, ide=1, arbid=TEST_ARBID, length=8, data=b'\x80\x31\xD4\x1F\xD8\x00\x00\x00')
    print_msg(msg, '%s ->' % client_name)
    client.send(msg)


def test_converged_inputs(client, client_name, msgq):
    convergence_failure = 0
    N = 2
    for i in range(1, N + 1):
        angle = 360 * i / N
        ecc = .338

        encoded_angle = int((angle + 210) * 1000000)
        encoded_ecc = int(ecc / 0.0015625)
        msg_data = struct.pack('<LHH', encoded_angle, encoded_ecc, 0xFFFF)

        resp = run_test(client, client_name, msgq, TEST_ARBID, msg_data,
                RESP_MASK, RESP_ARBID, 8)

        if resp is None:
            convergence_failure += 1
        else:
            # If a message was received check the results
            encoded_ecc_anom_degrees = struct.unpack_from('<L', resp, 0)[0]
            ecc_anom_degrees = encoded_ecc_anom_degrees * 0.000001 - 210
            if ecc_anom_degrees >= -210 and ecc_anom_degrees <= 210:
                print('Response within range: -210 <= %f <= 210' % ecc_anom_degrees)
            else:
                print('Response out of range: %f' % ecc_anom_degrees)
                convergence_failure += 1

    return convergence_failure


def test_for_vulnerable_inputs_unpatched(client, client_name, msgq):
    convergence_failure = test_converged_inputs(client, client_name, msgq)
    # For the vulnerable version we expect there to be convergence failures
    assert convergence_failure > 0


def test_for_vulnerable_inputs_patched(client, client_name, msgq):
    convergence_failure = test_converged_inputs(client, client_name, msgq)
    assert convergence_failure == 0


def recv_thread(client, name, msgq):
    while True:
        msg = client.recv()
        if msg is None:
            break
        print_msg(msg, name)
        msgq.put((client._addr, msg))


def run(*ports):
    msgq = queue.Queue()

    clients = [ExternalIOClient(None, p) for p in ports]
    for client in clients:
        client.open()

    thread_names = ['FlexCAN_A', 'FlexCAN_B', 'FlexCAN_C', 'FlexCAN_D']

    threads = [threading.Thread(target=recv_thread, daemon=True, args=(c, n, msgq))
            for c, n in zip(clients, thread_names)]
    for thread in threads:
        thread.start()

    # First send an address claim message?
    #input()
    #msg = CanMsg(rtr=0, ide=1, arbid=0x18eafffe, length=3, data=b'\x00\x33\xb6')
    #print_msg(msg, '%s ->' % thread_names[0])
    #clients[0].send(msg)
    #time.sleep(1)

    #msg = CanMsg(rtr=0, ide=1, arbid=0x18eaffb6, length=3, data=b'\xeb\xfe\xb6')
    #print_msg(msg, '%s ->' % thread_names[0])
    #clients[0].send(msg)

    #input()
    #test_lower_input_boundary(clients[0], thread_names[0], msgq)

    #input()
    #test_upper_input_boundary(clients[0], thread_names[0], msgq)

    while True:
        input()
        test_upper_input_boundary(clients[0], thread_names[0], msgq)
        #test_for_vulnerable_inputs_unpatched(clients[0], thread_names[0], msgq)
        #test_for_vulnerable_inputs_patched(clients[0], thread_names[0], msgq)
        #test(clients[0], thread_names[0], msgq)


def main():
    parser = argparse.ArgumentParser(description='Unpatched keplers law tests for cm2350 emulator')
    parser.add_argument('-a', '--port-a', default=11000, type=int)
    parser.add_argument('-b', '--port-b', default=11001, type=int)
    parser.add_argument('-c', '--port-c', default=11002, type=int)
    parser.add_argument('-d', '--port-d', default=11003, type=int)
    args = parser.parse_args()
    run(args.port_a, args.port_b, args.port_c, args.port_d)


if __name__ == '__main__':
    main()
