###############################################################################
##
##  Copyright (C) 2011-2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
## Modified by Greg Alice to develop this S3VT prototype
###############################################################################

import sys

from twisted.internet import reactor
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerFactory, \
                                        WebSocketServerProtocol, \
                                        listenWS

SERVER = "ws://ec2-52-11-177-72.us-west-2.compute.amazonaws.com:8575"
viewers = {}

class BroadcastServerProtocol(WebSocketServerProtocol):

    def onOpen(self):
      self.factory.register(self)

    def onMessage(self, payload, isBinary):
      if not isBinary:
         #msg = "{} from {}".format(payload.decode('utf8'), self.peer)
         msg = "{}".format(payload.decode('utf8'))
         self.factory.broadcast(msg)     

    def connectionLost(self, reason):
      WebSocketServerProtocol.connectionLost(self, reason)
      self.factory.unregister(self)


class BroadcastServerFactory(WebSocketServerFactory):
    """
    Simple broadcast server broadcasting any message it receives to all
    currently connected clients.
    """

    def __init__(self, url, debug = False, debugCodePaths = False):
      WebSocketServerFactory.__init__(self, url, debug = debug, debugCodePaths = debugCodePaths)
      self.clients = []
      self.tickcount = 0
      self.tick()
      self.time = "0"
      self.status = "-1"

    def tick(self):
      self.tickcount += 1
      # self.broadcast("tick %d from server" % self.tickcount)
      reactor.callLater(1, self.tick)

    def register(self, client):
      if not client in self.clients:
         print("registered client {}".format(client.peer))
         self.clients.append(client)

    def unregister(self, client):
      if client in self.clients:
         print("unregistered client {}".format(client.peer))
         self.clients.remove(client)
         if client.peer in viewers:
            del viewers[client.peer]
            new_msg = "authenticated="
            for x in viewers:
                viewer = viewers[x]
                new_msg += (viewer + "<br>")
            for c in self.clients:
                c.sendMessage(new_msg.encode('utf8'))
                print("message sent to {}".format(c.peer))
            print("message was " + new_msg.encode('utf8'))

    def broadcast(self, msg):
      print("message '{}' ".format(msg))
      
      if "logon=" in msg:
        print "logon received, msg=" + msg;
        name = msg[6:]
        new_msg = "authenticated="
        for c in self.clients:
            if not c.peer in viewers:
                viewers[c.peer] = name
        for x in viewers:
            viewer = viewers[x]
            new_msg += (viewer + "<br>")
        msg = new_msg;
        print "msg is " + msg + "\n";
      
      for c in self.clients:
         c.sendMessage(msg.encode('utf8'))
         print("message sent to {}".format(c.peer))
         
    def playbackCmd(msg):
        # msg in the format of status=<status>&time=<time>
        # Break into status and time
        params = msg.partition("&")
        # Separate parameters from values
        st_param = params[0].partition("=")
        new_st = st_param[2]
        time_param = params[2].partition("=")
        new_t = time_param[2]
        changed = False
        
        if not status == new_st:
            print("status changed: old=",self.status," new=",st_param[2])  
            self.status = new_st
            changed = True
            
        if not time == new_t:
            print("time changed: old=",self.time," new=",time_param[2]) 
            self.time = new_t
            changed = True
        
        if changed:
            return 'status=' + self.status + '&time=' + self.time
        
        else:
            return None

class BroadcastPreparedServerFactory(BroadcastServerFactory):
    """
    Functionally same as above, but optimized broadcast using
    prepareMessage and sendPreparedMessage.
    """

    def broadcast(self, msg):
      print("broadcasting prepared message '{}' ..".format(msg))
      preparedMsg = self.prepareMessage(msg)
      for c in self.clients:
         c.sendPreparedMessage(preparedMsg)
         print("prepared message sent to {}".format(c.peer))


if __name__ == '__main__':

    if len(sys.argv) > 1 and sys.argv[1] == 'debug':
      log.startLogging(sys.stdout)
      debug = True
    else:
      debug = False

    ServerFactory = BroadcastServerFactory
    #ServerFactory = BroadcastPreparedServerFactory
   # contextFactory = ssl.DefaultOpenSSLContextFactory('/etc/ssl/certs/s3vt.key', '/etc/ssl/certs/s3vt.pem')
    #'/var/keys/server.key',
    #                                                  '/var/keys/server.crt')
    factory = ServerFactory(SERVER, 
                           debug = debug,
                           debugCodePaths = debug)
    
    factory.protocol = BroadcastServerProtocol
    factory.setProtocolOptions(allowHixie76 = True)
    listenWS(factory)
    #listenWS(factory, contextFactory)

    webdir = File(".")
    web = Site(webdir)
    reactor.listenTCP(8080, web)

    reactor.run()
