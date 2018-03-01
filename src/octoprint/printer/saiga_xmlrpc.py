# -*- coding: utf-8 -*-
# @Author: Matt Pedler
# @Date:   2018-02-28 11:06:59
# @Last Modified by:   Matt Pedler
# @Last Modified time: 2018-02-28 17:23:09
'''
This is an XMLRPC server for the sole purpose of relaying all messages in comm to 
any local program that is subscribed to it. This allows other programs on the host
machine to read the printer terminal without being a part of Octoprint Plugin or otherwise
'''
from __future__ import absolute_import
from xmlrpclib import ServerProxy
from SimpleXMLRPCServer import SimpleXMLRPCServer
import multiprocessing
import threading
import logging
import traceback
import os

def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("",0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return int(port)

rpc_server_port = 5070
# XMLRPC server process
def start_saiga_dispatch_server():
    xmlrpc_process = threading.Thread(target=_saiga_dispatcher, name="printer.xmlrpc")
    xmlrpc_process.start()

#~~ XMLRPC serve forever thread
def _saiga_dispatcher():
    #xmlrpc
    Saiga_Dispatcher()

def check_pid(pid):        
    """ Check For the existence of a pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

class Saiga_Dispatcher(SimpleXMLRPCServer, object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.topic_subscribers = dict()
        super(Saiga_Dispatcher, self).__init__(("0.0.0.0", rpc_server_port), logRequests=False)
        self._logger.info("**********************************************************")
        self._logger.info("XMLRPC Listening on port {}...".format(rpc_server_port))
        self._logger.info("**********************************************************")
        self.register_function(self.subscribe, "subscribe")
        self.register_function(self.unsubscribe, "unsubscribe")
        self.register_function(self.unsubscribe_all, "unsubscribe_all")
        self.register_function(self.send, "send")
        self.register_function(self.kill, "kill")

        self.parent_PID = parent_PID
        self.serve_forever()

    def serve_forever(self):
        #serve xmlrpc forever until dead
        self.server_alive = True
        while self.server_alive:
            self.handle_request()

        self._logger.info("Exiting XMLRPC Server")

    def kill(self):
        self.server_alive = False
        return "OK"

    def subscribe(self, subscriber, topic):
        self._logger.info('Subscribing {} to {}'.format(subscriber, topic))
        self.topic_subscribers.setdefault(topic, set()).add(subscriber)
        return "OK"

    def unsubscribe(self, subscriber, topic):
        self._logger.info('Unsubscribing {} from {}'.format(subscriber, topic))
        self.topic_subscribers.setdefault(topic, set()).discard(subscriber)
        return "OK"

    def unsubscribe_all(self, topic):
        self._logger.info('unsubscribing all from {}'.format(topic))
        self.subscribers = self.topic_subscribers[topic] = set()
        return "OK"

    def send(self, message):
        #self._logger.info("\n\nSending Message:\nTopic: {}\nPayload: {}\n\n".format(message["topic"], message["payload"]))
        try:
            for subscriber in self.topic_subscribers[message.get("topic", "all")]:
                srv_proxy = ServerProxy("http://0.0.0.0:{}".format(subscriber))
                srv_proxy.process(message)
        except KeyError as e:
            #self._logger.info(message.get("topic", "No Topic") + " has no subscribers yet. Discarding message")
            pass
            #This error is most likely that there are no subscribers
        
        return "OK"

class Saiga_Node(object):
    """
    This node will allow the interaction between the Saiga_Server and any other process
    """
    def __init__(self):
        super(Saiga_Node, self).__init__()
        self._logger = logging.getLogger(__name__)

    def subscribe(self, topic, callback):
        subscriber_server = Subscriber("http://0.0.0.0:{}".format(rpc_server_port), topic, callback)
        return subscriber_server

    def publish_to(self, topic, payload = "Default Message, Please Change. It's you not me"):
        '''
           Provide a topic and some sort of payload
        '''
        message = {
            'topic': topic,
            'payload': payload,
        }
        try:
            publisher = ServerProxy("http://0.0.0.0:{}".format(rpc_server_port))
            publisher.send(message)
        except Exception as e:
            self._logger.info(str(e))
            traceback.print_exc()

            self._logger.info("Failed to connect on port {}".format(rpc_server_port))

class Subscriber(SimpleXMLRPCServer, object):
    def __init__(self, dispatcher, topic, callback):
        self._logger = logging.getLogger(__name__)
        self.port = self.get_open_port()
        self._logger.info("Listening on port " + str(self.port) + "...")
        super(Subscriber, self).__init__(("0.0.0.0", self.port),
                                         allow_none=True,
                                         logRequests=False)
        #handle the callback
        self.register_function(callback, "process")
        self.subscribe(dispatcher, topic)

    def subscribe(self, dispatcher, topic):
        sub_proxy = ServerProxy(dispatcher)
        sub_proxy.subscribe(self.port, topic)

    def get_open_port(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("",0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return int(port)

